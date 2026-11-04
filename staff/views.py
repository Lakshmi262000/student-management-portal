from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from accounts.permissions import roles_required
from attendance.models import StaffAttendance
from .forms import StaffCreationForm, StaffProfileForm
from .models import StaffProfile, StaffProfileAudit
from .services import create_staff


@login_required
@roles_required(User.Role.ADMIN)
def staff_list(request):
    profiles = StaffProfile.objects.select_related("user").prefetch_related("batches")
    query = request.GET.get("q", "").strip()
    if query:
        profiles = profiles.filter(
            Q(staff_id__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(user__email__icontains=query)
            | Q(designation__icontains=query)
        )
    return render(
        request,
        "staff/list.html",
        {"staff_profiles": profiles, "query": query},
    )


@login_required
@roles_required(User.Role.ADMIN)
def staff_create(request):
    if request.method == "POST":
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            profile = create_staff(data=form.cleaned_data, created_by=request.user)
            messages.success(request, f"Staff member {profile.staff_id} created.")
            return redirect("staff:list")
    else:
        form = StaffCreationForm()
    return render(
        request,
        "shared/form.html",
        {
            "form": form,
            "title": "Add staff member",
            "submit_label": "Create staff account",
        },
    )


@login_required
def staff_profile(request):
    profile = get_object_or_404(
        StaffProfile.objects.select_related("user").prefetch_related("batches"),
        user=request.user,
    )
    if request.method == "POST":
        if request.user.role not in (User.Role.ADMIN, User.Role.STAFF):
            raise PermissionDenied
        form = StaffProfileForm(request.POST, instance=profile, actor=request.user)
        if request.user.role != User.Role.ADMIN:
            form.fields.pop("batches")
        if form.is_valid():
            with transaction.atomic():
                changed_fields = form.changed_data
                form.save()
                if changed_fields:
                    StaffProfileAudit.objects.create(
                        staff_profile=profile,
                        changed_by=request.user,
                        action="updated",
                        changed_fields=changed_fields,
                    )
            messages.success(request, "Profile updated.")
            return redirect("staff:profile")
    else:
        form = StaffProfileForm(instance=profile, actor=request.user)
        if request.user.role != User.Role.ADMIN:
            form.fields.pop("batches")
    return render(
        request,
        "staff/profile.html",
        {
            "profile": profile,
            "form": form,
            "attendance": StaffAttendance.objects.filter(staff=profile)[:20],
            "audit_history": profile.audit_history.select_related("changed_by")[:20],
        },
    )


@login_required
@roles_required(User.Role.ADMIN)
def staff_edit(request, pk):
    profile = get_object_or_404(StaffProfile.objects.select_related("user"), pk=pk)
    if request.method == "POST":
        form = StaffProfileForm(request.POST, instance=profile, actor=request.user)
        if form.is_valid():
            with transaction.atomic():
                changed_fields = form.changed_data
                form.save()
                if changed_fields:
                    StaffProfileAudit.objects.create(
                        staff_profile=profile,
                        changed_by=request.user,
                        action="updated",
                        changed_fields=changed_fields,
                    )
            messages.success(request, "Staff profile updated.")
            return redirect("staff:list")
    else:
        form = StaffProfileForm(instance=profile, actor=request.user)
    return render(
        request,
        "shared/form.html",
        {
            "form": form,
            "title": f"Update {profile.staff_id}",
            "submit_label": "Save changes",
        },
    )


@login_required
@roles_required(User.Role.ADMIN)
def staff_deactivate(request, pk):
    if request.method != "POST":
        raise PermissionDenied
    profile = get_object_or_404(StaffProfile.objects.select_related("user"), pk=pk)
    with transaction.atomic():
        profile.user.is_active = False
        profile.user.save(update_fields=["is_active"])
        profile.modified_by = request.user
        profile.save(update_fields=["modified_by"])
        StaffProfileAudit.objects.create(
            staff_profile=profile,
            changed_by=request.user,
            action="deactivated",
            changed_fields=["is_active"],
        )
    messages.success(request, f"Account for {profile.staff_id} deactivated.")
    return redirect("staff:list")
