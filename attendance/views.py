from calendar import monthrange
from datetime import date

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from accounts.permissions import roles_required
from academics.models import Batch
from staff.models import StaffProfile
from students.models import Student
from .forms import AttendanceDateForm, AttendanceReportFilterForm
from .models import (
    AttendanceStatus,
    AttendanceAuditLog,
    StaffAttendance,
    StudentAttendance,
)


class BulkStatusForm(forms.Form):
    def __init__(self, *args, people, prefix, **kwargs):
        super().__init__(*args, **kwargs)
        self.people = list(people)
        for person in self.people:
            self.fields[f"{prefix}_{person.pk}"] = forms.ChoiceField(
                choices=AttendanceStatus.choices,
                initial=AttendanceStatus.PRESENT,
                label=str(person),
            )


def _can_access_batch(user, batch):
    return user.role == User.Role.ADMIN or (
        user.role == User.Role.STAFF
        and batch.staff_members.filter(user=user).exists()
    )


@login_required
@roles_required(User.Role.ADMIN, User.Role.STAFF)
def mark_students(request, batch_id):
    batch = get_object_or_404(
        Batch.objects.select_related("course").prefetch_related("students__user"),
        pk=batch_id,
        is_active=True,
    )
    if not _can_access_batch(request.user, batch):
        raise PermissionDenied
    students = list(
        Student.objects.filter(batch=batch, user__is_active=True)
        .select_related("user")
        .order_by("student_id")
    )
    initial_date = timezone.localdate()
    date_form = AttendanceDateForm(
        request.POST or None, initial={"date": initial_date}
    )
    bulk_form = BulkStatusForm(
        request.POST or None, people=students, prefix="student"
    )
    if request.method == "POST" and date_form.is_valid() and bulk_form.is_valid():
        attendance_date = date_form.cleaned_data["date"]
        if attendance_date > initial_date:
            date_form.add_error("date", "Attendance cannot be marked for a future date.")
        else:
            try:
                with transaction.atomic():
                    for student in students:
                        status = bulk_form.cleaned_data[f"student_{student.pk}"]
                        record, created = StudentAttendance.objects.get_or_create(
                            student=student,
                            date=attendance_date,
                            defaults={
                                "status": status,
                                "marked_by": request.user,
                                "modified_by": request.user,
                            },
                        )
                        if not created:
                            old_status = record.status
                            if old_status == status:
                                continue
                            record.status = status
                            record.modified_by = request.user
                            record.save(update_fields=["status", "modified_by", "updated_at"])
                        else:
                            old_status = ""
                        AttendanceAuditLog.objects.create(
                            student_attendance=record,
                            changed_by=request.user,
                            old_status=old_status,
                            new_status=status,
                        )
            except IntegrityError:
                messages.error(
                    request,
                    "Attendance changed concurrently. Reload the page and try again.",
                )
            else:
                messages.success(
                    request,
                    f"Attendance saved for {len(students)} students on {attendance_date}.",
                )
                return redirect("attendance:mark_students", batch_id=batch.pk)
    if request.method == "GET":
        chosen = request.GET.get("date")
        if chosen:
            try:
                selected_date = date.fromisoformat(chosen)
            except ValueError:
                selected_date = initial_date
            date_form = AttendanceDateForm(initial={"date": selected_date})
        else:
            selected_date = initial_date
        existing = {
            record.student_id: record.status
            for record in StudentAttendance.objects.filter(
                student__in=students, date=selected_date
            )
        }
        for student in students:
            field = f"student_{student.pk}"
            if student.pk in existing:
                bulk_form.fields[field].initial = existing[student.pk]

    return render(
        request,
        "attendance/mark_students.html",
        {
            "batch": batch,
            "students": students,
            "date_form": date_form,
            "bulk_form": bulk_form,
            "selected_date": (
                date_form["date"].value() or initial_date.isoformat()
            ),
        },
    )


@login_required
@roles_required(User.Role.ADMIN)
def mark_staff(request):
    profiles = list(
        StaffProfile.objects.filter(user__is_active=True)
        .select_related("user")
        .order_by("staff_id")
    )
    today = timezone.localdate()
    date_form = AttendanceDateForm(request.POST or None, initial={"date": today})
    bulk_form = BulkStatusForm(request.POST or None, people=profiles, prefix="staff")
    if request.method == "POST" and date_form.is_valid() and bulk_form.is_valid():
        attendance_date = date_form.cleaned_data["date"]
        if attendance_date > today:
            date_form.add_error("date", "Attendance cannot be marked for a future date.")
        else:
            with transaction.atomic():
                for profile in profiles:
                    status = bulk_form.cleaned_data[f"staff_{profile.pk}"]
                    record, created = StaffAttendance.objects.get_or_create(
                        staff=profile,
                        date=attendance_date,
                        defaults={
                            "status": status,
                            "marked_by": request.user,
                            "modified_by": request.user,
                        },
                    )
                    if not created:
                        old_status = record.status
                        if old_status == status:
                            continue
                        record.status = status
                        record.modified_by = request.user
                        record.save(update_fields=["status", "modified_by", "updated_at"])
                    else:
                        old_status = ""
                    AttendanceAuditLog.objects.create(
                        staff_attendance=record,
                        changed_by=request.user,
                        old_status=old_status,
                        new_status=status,
                    )
            messages.success(request, f"Staff attendance saved for {attendance_date}.")
            return redirect("attendance:mark_staff")

    if request.method == "GET":
        chosen = request.GET.get("date")
        try:
            selected_date = date.fromisoformat(chosen) if chosen else today
        except ValueError:
            selected_date = today
        date_form = AttendanceDateForm(initial={"date": selected_date})
        existing = {
            record.staff_id: record.status
            for record in StaffAttendance.objects.filter(
                staff__in=profiles, date=selected_date
            )
        }
        for profile in profiles:
            if profile.pk in existing:
                bulk_form.fields[f"staff_{profile.pk}"].initial = existing[profile.pk]

    return render(
        request,
        "attendance/mark_staff.html",
        {
            "profiles": profiles,
            "date_form": date_form,
            "bulk_form": bulk_form,
            "selected_date": date_form["date"].value() or today.isoformat(),
        },
    )


@login_required
def reports(request):
    form = AttendanceReportFilterForm(request.GET or None)
    if request.GET and not form.is_valid():
        records = StudentAttendance.objects.none()
    else:
        selected_month = (
            form.cleaned_data["month"]
            if form.is_bound and form.is_valid()
            else timezone.localdate().month
        )
        selected_year = (
            form.cleaned_data["year"]
            if form.is_bound and form.is_valid()
            else timezone.localdate().year
        )
        start = date(selected_year, selected_month, 1)
        end = date(selected_year, selected_month, monthrange(selected_year, selected_month)[1])
        records = StudentAttendance.objects.filter(date__range=(start, end))
        if request.user.role == User.Role.STAFF:
            records = records.filter(student__batch__staff_members__user=request.user)
        elif request.user.role == User.Role.STUDENT:
            records = records.filter(student__user=request.user)
        records = records.select_related(
            "student__user", "student__batch", "student__batch__course"
        ).order_by("-date", "student__student_id")
    record_list = list(records)
    monthly_stats = {}
    for record in record_list:
        stats = monthly_stats.setdefault(
            record.student_id,
            {
                "student": record.student,
                "present": 0,
                "absent": 0,
                "eligible": 0,
                "score": 0,
            },
        )
        if record.status == AttendanceStatus.LEAVE:
            continue
        stats["eligible"] += 1
        if record.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE):
            stats["score"] += 1
            stats["present"] += 1
        elif record.status == AttendanceStatus.HALF_DAY:
            stats["score"] += 0.5
        elif record.status == AttendanceStatus.ABSENT:
            stats["absent"] += 1
    monthly_summaries = [
        {
            **stats,
            "percentage": round(stats["score"] * 100 / stats["eligible"])
            if stats["eligible"]
            else 0,
        }
        for stats in monthly_stats.values()
    ]
    return render(
        request,
        "attendance/reports.html",
        {
            "form": form,
            "records": record_list,
            "monthly_summaries": monthly_summaries,
        },
    )


@login_required
def daily_report(request):
    form = AttendanceDateForm(request.GET or None, initial={"date": timezone.localdate()})
    selected_date = timezone.localdate()
    if form.is_bound and form.is_valid():
        selected_date = form.cleaned_data["date"]
    student_records = StudentAttendance.objects.filter(date=selected_date)
    if request.user.role == User.Role.STAFF:
        student_records = student_records.filter(
            student__batch__staff_members__user=request.user
        )
    elif request.user.role == User.Role.STUDENT:
        student_records = student_records.filter(student__user=request.user)
    student_records = student_records.select_related(
        "student__user", "student__batch", "student__batch__course"
    ).order_by("student__student_id")

    staff_records = StaffAttendance.objects.none()
    if request.user.role == User.Role.ADMIN:
        staff_records = StaffAttendance.objects.filter(
            date=selected_date
        ).select_related("staff__user")
    elif request.user.role == User.Role.STAFF:
        staff_records = StaffAttendance.objects.filter(
            date=selected_date, staff__user=request.user
        ).select_related("staff__user")
    return render(
        request,
        "attendance/daily_report.html",
        {
            "form": form,
            "selected_date": selected_date,
            "student_records": student_records,
            "staff_records": staff_records,
        },
    )


@login_required
def staff_attendance_history(request):
    form = AttendanceReportFilterForm(request.GET or None)
    if request.GET and not form.is_valid():
        records = StaffAttendance.objects.none()
    else:
        month = (
            form.cleaned_data["month"]
            if form.is_bound and form.is_valid()
            else timezone.localdate().month
        )
        year = (
            form.cleaned_data["year"]
            if form.is_bound and form.is_valid()
            else timezone.localdate().year
        )
        first = date(year, month, 1)
        last = date(year, month, monthrange(year, month)[1])
        records = StaffAttendance.objects.filter(date__range=(first, last))
    if request.user.role == User.Role.ADMIN:
        records = records.select_related("staff__user")
    elif request.user.role == User.Role.STAFF:
        records = records.filter(staff__user=request.user).select_related("staff__user")
    else:
        raise PermissionDenied
    record_list = list(records)
    eligible = [record for record in record_list if record.status != AttendanceStatus.LEAVE]
    score = sum(
        1 if record.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE)
        else 0.5 if record.status == AttendanceStatus.HALF_DAY
        else 0
        for record in eligible
    )
    percentage = round(score * 100 / len(eligible)) if eligible else 0
    return render(
        request,
        "attendance/staff_history.html",
        {
            "form": form,
            "records": record_list[:100],
            "attendance_percentage": percentage,
        },
    )
