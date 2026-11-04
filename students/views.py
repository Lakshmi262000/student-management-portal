from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from accounts.permissions import roles_required
from .forms import StudentRegistrationForm, StudentUpdateForm
from .models import Student, StudentProfileAudit
from .services import register_student


def _student_queryset_for(user):
    queryset = Student.objects.select_related("user", "batch", "batch__course")
    if user.role == User.Role.STAFF:
        queryset = queryset.filter(batch__staff_members__user=user).distinct()
    return queryset


@login_required
@roles_required(User.Role.ADMIN, User.Role.STAFF)
def student_list(request):
    students = _student_queryset_for(request.user)
    query = request.GET.get("q", "").strip()
    if query:
        students = students.filter(
            Q(student_id__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(user__email__icontains=query)
            | Q(batch__name__icontains=query)
        )
    return render(
        request, "students/list.html", {"students": students, "query": query}
    )


@login_required
@roles_required(User.Role.ADMIN, User.Role.STAFF)
def student_register(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST, actor=request.user)
        if form.is_valid():
            try:
                student = register_student(
                    data=form.cleaned_data, registered_by=request.user
                )
            except ValidationError as error:
                form.add_error(None, error)
            except IntegrityError:
                form.add_error(
                    None,
                    "Registration could not be completed because the username, "
                    "email, course, or batch was just created by another user. "
                    "Review the details and try again.",
                )
            else:
                messages.success(
                    request,
                    f"Student {student.student_id} was registered successfully.",
                )
                return redirect("students:detail", pk=student.pk)
    else:
        form = StudentRegistrationForm(actor=request.user)
    return render(
        request,
        "shared/form.html",
        {
            "form": form,
            "title": "Register student",
            "submit_label": "Create student account",
            "course_choices": form.course_choices,
            "course_list_id": form["course"].field.widget.attrs["list"],
        },
    )


@login_required
def my_profile(request):
    if request.user.role != User.Role.STUDENT:
        raise PermissionDenied
    student = get_object_or_404(
        Student.objects.only("pk"),
        user=request.user,
    )
    return redirect("students:detail", pk=student.pk)


@login_required
def student_detail(request, pk):
    student = get_object_or_404(
        Student.objects.select_related("user", "batch", "batch__course"), pk=pk
    )
    if request.user.role == User.Role.STUDENT and student.user_id != request.user.pk:
        raise PermissionDenied
    if request.user.role == User.Role.STAFF and not student.batch.staff_members.filter(
        user=request.user
    ).exists():
        raise PermissionDenied
    records = student.attendance_records.all()[:20]
    audit_history = student.audit_history.select_related("changed_by")[:20]
    return render(
        request,
        "students/detail.html",
        {
            "student": student,
            "attendance": records,
            "audit_history": audit_history,
        },
    )


@login_required
@roles_required(User.Role.ADMIN, User.Role.STAFF)
def student_update(request, pk):
    student = get_object_or_404(_student_queryset_for(request.user), pk=pk)
    if request.method == "POST":
        form = StudentUpdateForm(request.POST, instance=student, actor=request.user)
        if form.is_valid():
            with transaction.atomic():
                changed_fields = form.changed_data
                form.save()
                if changed_fields:
                    StudentProfileAudit.objects.create(
                        student=student,
                        changed_by=request.user,
                        action="updated",
                        changed_fields=changed_fields,
                    )
            messages.success(request, "Student profile updated.")
            return redirect("students:detail", pk=student.pk)
    else:
        form = StudentUpdateForm(instance=student, actor=request.user)
    return render(
        request,
        "shared/form.html",
        {
            "form": form,
            "title": f"Update {student.student_id}",
            "submit_label": "Save changes",
        },
    )


@login_required
@roles_required(User.Role.ADMIN)
def student_deactivate(request, pk):
    if request.method != "POST":
        raise PermissionDenied
    student = get_object_or_404(Student.objects.select_related("user"), pk=pk)
    with transaction.atomic():
        student.user.is_active = False
        student.user.save(update_fields=["is_active"])
        student.modified_by = request.user
        student.save(update_fields=["modified_by"])
        StudentProfileAudit.objects.create(
            student=student,
            changed_by=request.user,
            action="deactivated",
            changed_fields=["is_active"],
        )
    messages.success(request, f"Account for {student.student_id} deactivated.")
    return redirect("students:list")
