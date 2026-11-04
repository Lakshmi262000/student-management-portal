from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, connection
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.models import User
from academics.models import Batch, Course
from attendance.models import AttendanceStatus, StaffAttendance, StudentAttendance
from staff.models import StaffProfile
from students.models import Student


def _attendance_percentage(records):
    eligible = [record for record in records if record.status != AttendanceStatus.LEAVE]
    if not eligible:
        return 0
    score = sum(
        1 if record.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE)
        else 0.5 if record.status == AttendanceStatus.HALF_DAY
        else 0
        for record in eligible
    )
    return round(score * 100 / len(eligible))


def health(request):
    try:
        connection.ensure_connection()
    except DatabaseError:
        return HttpResponse("Database unavailable", status=503)
    return HttpResponse("ok")


@login_required
def home(request):
    user = request.user
    today = timezone.localdate()
    context = {"today": today}

    if user.role == User.Role.ADMIN:
        todays_students = StudentAttendance.objects.filter(date=today)
        todays_staff = StaffAttendance.objects.filter(date=today)
        student_total = todays_students.count()
        context.update(
            {
                "total_students": Student.objects.filter(user__is_active=True).count(),
                "total_staff": StaffProfile.objects.filter(user__is_active=True).count(),
                "total_courses": Course.objects.count(),
                "total_batches": Batch.objects.count(),
                "present_students": todays_students.filter(
                    status=AttendanceStatus.PRESENT
                ).count(),
                "absent_students": todays_students.filter(
                    status=AttendanceStatus.ABSENT
                ).count(),
                "student_attendance_today": todays_students.count(),
                "staff_attendance_today": todays_staff.count(),
                "present_percentage": round(
                    todays_students.filter(status=AttendanceStatus.PRESENT).count()
                    * 100
                    / student_total
                )
                if student_total
                else 0,
                "recent_students": Student.objects.select_related(
                    "user", "batch", "batch__course"
                ).filter(user__is_active=True).order_by("-user__date_joined")[:6],
            }
        )
    elif user.role == User.Role.STAFF:
        batches = Batch.objects.filter(staff_members__user=user).distinct()
        students = Student.objects.filter(
            batch__in=batches, user__is_active=True
        ).select_related(
            "user", "batch", "batch__course"
        ).order_by("-user__date_joined")
        todays_students = StudentAttendance.objects.filter(
            date=today, student__batch__in=batches
        )
        total_today = todays_students.count()
        context.update(
            {
                "assigned_batches": batches,
                "total_assigned_students": students.count(),
                "present_students": todays_students.filter(
                    status=AttendanceStatus.PRESENT
                ).count(),
                "absent_students": todays_students.filter(
                    status=AttendanceStatus.ABSENT
                ).count(),
                "present_percentage": round(
                    todays_students.filter(status=AttendanceStatus.PRESENT).count()
                    * 100
                    / total_today
                )
                if total_today
                else 0,
                "recent_students": students[:6],
            }
        )
        try:
            context["staff_profile"] = user.staff_profile
        except StaffProfile.DoesNotExist:
            context["staff_profile"] = None
    else:
        try:
            student = Student.objects.select_related(
                "batch", "batch__course"
            ).get(user=user)
        except Student.DoesNotExist:
            student = None
        context["student"] = student
        if student:
            records = list(student.attendance_records.all())
            context.update(
                {
                    "attendance_percentage": _attendance_percentage(records),
                    "present_days": sum(
                        1
                        if record.status
                        in (AttendanceStatus.PRESENT, AttendanceStatus.LATE)
                        else 0.5
                        if record.status == AttendanceStatus.HALF_DAY
                        else 0
                        for record in records
                    ),
                    "absent_days": sum(
                        record.status == AttendanceStatus.ABSENT
                        for record in records
                    ),
                    "recent_attendance": records[:8],
                }
            )
        else:
            context["attendance_percentage"] = 0
            context["present_days"] = 0
            context["absent_days"] = 0
            context["recent_attendance"] = []

    return render(request, "dashboard/home.html", context)
