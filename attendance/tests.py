from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from academics.models import Batch, Course
from attendance.models import AttendanceStatus, StudentAttendance
from staff.models import StaffProfile
from students.models import Student


class AttendanceWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="Very-Strong-Test-Pass!1357",
        )
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="Very-Strong-Test-Pass!1357",
            role=User.Role.STAFF,
        )
        self.student_user = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="Very-Strong-Test-Pass!1357",
            role=User.Role.STUDENT,
        )
        course = Course.objects.create(code="SCI", name="Science")
        self.batch = Batch.objects.create(
            course=course, name="Group A", start_date=date(2026, 1, 1)
        )
        self.other_batch = Batch.objects.create(
            course=course, name="Group B", start_date=date(2026, 1, 1)
        )
        profile = StaffProfile.objects.create(
            user=self.staff_user,
            designation="Instructor",
            joining_date=date(2026, 1, 1),
        )
        profile.batches.add(self.batch)
        self.student = Student.objects.create(
            user=self.student_user,
            batch=self.batch,
            joining_date=date(2026, 1, 1),
            registered_by=self.admin,
        )

    def test_assigned_staff_can_mark_batch_attendance_and_edit_it(self):
        self.client.force_login(self.staff_user)
        url = reverse("attendance:mark_students", args=[self.batch.pk])
        data = {
            "date": timezone.localdate().isoformat(),
            f"student_{self.student.pk}": AttendanceStatus.PRESENT,
        }

        response = self.client.post(url, data)
        self.assertRedirects(response, url)
        record = StudentAttendance.objects.get(student=self.student)
        self.assertEqual(record.status, AttendanceStatus.PRESENT)
        self.assertEqual(record.marked_by, self.staff_user)

        data[f"student_{self.student.pk}"] = AttendanceStatus.LATE
        self.client.post(url, data)
        record.refresh_from_db()
        self.assertEqual(record.status, AttendanceStatus.LATE)
        self.assertEqual(record.marked_by, self.staff_user)
        self.assertEqual(record.modified_by, self.staff_user)
        self.assertEqual(StudentAttendance.objects.filter(student=self.student).count(), 1)

    def test_staff_cannot_mark_unassigned_batch(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse("attendance:mark_students", args=[self.other_batch.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_student_report_is_scoped_to_own_records(self):
        other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="Very-Strong-Test-Pass!1357",
            role=User.Role.STUDENT,
        )
        other_student = Student.objects.create(
            user=other_user,
            batch=self.batch,
            joining_date=date(2026, 1, 1),
            registered_by=self.admin,
        )
        StudentAttendance.objects.create(
            student=self.student,
            date=timezone.localdate(),
            status=AttendanceStatus.PRESENT,
            marked_by=self.admin,
            modified_by=self.admin,
        )
        StudentAttendance.objects.create(
            student=other_student,
            date=timezone.localdate(),
            status=AttendanceStatus.ABSENT,
            marked_by=self.admin,
            modified_by=self.admin,
        )
        self.client.force_login(self.student_user)

        response = self.client.get(reverse("attendance:reports"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.student_id)
        self.assertNotContains(response, other_student.student_id)

    def test_daily_report_is_available_to_staff_and_scoped_to_assigned_batch(self):
        StudentAttendance.objects.create(
            student=self.student,
            date=timezone.localdate(),
            status=AttendanceStatus.PRESENT,
            marked_by=self.admin,
            modified_by=self.admin,
        )
        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse("attendance:daily_report"),
            {"date": timezone.localdate().isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.student_id)
        self.assertNotContains(response, "other-student-id")

    def test_attendance_change_history_is_recorded(self):
        self.client.force_login(self.admin)
        url = reverse("attendance:mark_students", args=[self.batch.pk])
        post_data = {
            "date": timezone.localdate().isoformat(),
            f"student_{self.student.pk}": AttendanceStatus.PRESENT,
        }
        self.client.post(url, post_data)
        post_data[f"student_{self.student.pk}"] = AttendanceStatus.ABSENT
        self.client.post(url, post_data)

        record = StudentAttendance.objects.get(student=self.student)

        self.assertEqual(record.audit_history.count(), 2)
        self.assertEqual(
            record.audit_history.first().old_status, AttendanceStatus.PRESENT
        )

    def test_admin_can_mark_staff_attendance(self):
        profile = self.staff_user.staff_profile
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("attendance:mark_staff"),
            {
                "date": timezone.localdate().isoformat(),
                f"staff_{profile.pk}": AttendanceStatus.LATE,
            },
        )

        self.assertEqual(response.status_code, 302)
        from attendance.models import StaffAttendance

        record = StaffAttendance.objects.get(staff=profile)
        self.assertEqual(record.status, AttendanceStatus.LATE)
        self.assertEqual(record.marked_by, self.admin)
        self.assertEqual(record.audit_history.count(), 1)

    def test_staff_cannot_mark_staff_attendance(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse("attendance:mark_staff"))

        self.assertEqual(response.status_code, 403)
