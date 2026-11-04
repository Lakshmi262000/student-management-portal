from django.conf import settings
from django.db import models


class AttendanceStatus(models.TextChoices):
    PRESENT = "PRESENT", "Present"
    ABSENT = "ABSENT", "Absent"
    LATE = "LATE", "Late"
    HALF_DAY = "HALF_DAY", "Half day"
    LEAVE = "LEAVE", "Leave"


class AttendanceRecord(models.Model):
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=AttendanceStatus.choices)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(class)s_marked",
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(class)s_modified",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class StudentAttendance(AttendanceRecord):
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="attendance_records",
    )

    class Meta:
        ordering = ["-date", "student__student_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "date"], name="unique_student_attendance_per_day"
            )
        ]

    def __str__(self):
        return f"{self.student} - {self.date}: {self.get_status_display()}"


class StaffAttendance(AttendanceRecord):
    staff = models.ForeignKey(
        "staff.StaffProfile",
        on_delete=models.PROTECT,
        related_name="attendance_records",
    )

    class Meta:
        ordering = ["-date", "staff__staff_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["staff", "date"], name="unique_staff_attendance_per_day"
            )
        ]

    def __str__(self):
        return f"{self.staff} - {self.date}: {self.get_status_display()}"


class AttendanceAuditLog(models.Model):
    student_attendance = models.ForeignKey(
        StudentAttendance,
        on_delete=models.PROTECT,
        related_name="audit_history",
        null=True,
        blank=True,
    )
    staff_attendance = models.ForeignKey(
        StaffAttendance,
        on_delete=models.PROTECT,
        related_name="audit_history",
        null=True,
        blank=True,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="attendance_audits",
    )
    old_status = models.CharField(max_length=10, blank=True)
    new_status = models.CharField(max_length=10, choices=AttendanceStatus.choices)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        student_attendance__isnull=False,
                        staff_attendance__isnull=True,
                    )
                    | models.Q(
                        student_attendance__isnull=True,
                        staff_attendance__isnull=False,
                    )
                ),
                name="attendance_audit_has_one_record",
            )
        ]

    def __str__(self):
        return f"{self.old_status or 'NEW'} -> {self.new_status} by {self.changed_by}"
