from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from academics.models import Batch, Course
from .models import StaffProfile


class StaffManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="Very-Strong-Test-Pass!1357",
        )
        self.course = Course.objects.create(code="MATH", name="Mathematics")
        self.batch = Batch.objects.create(
            course=self.course,
            name="Group A",
            start_date=date(2026, 1, 1),
        )

    def test_admin_can_create_staff_account_and_assign_batch(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("staff:create"),
            {
                "username": "instructor",
                "email": "instructor@example.com",
                "first_name": "Alex",
                "last_name": "Teacher",
                "password": "Very-Strong-Test-Pass!1357",
                "phone": "5550100",
                "address": "Example address",
                "designation": "Instructor",
                "joining_date": "2026-02-01",
                "batches": [str(self.batch.pk)],
            },
        )

        profile = StaffProfile.objects.get(user__username="instructor")
        self.assertRedirects(response, reverse("staff:list"))
        self.assertEqual(profile.staff_id, "STF000001")
        self.assertEqual(profile.created_by, self.admin)
        self.assertTrue(profile.batches.filter(pk=self.batch.pk).exists())
        self.assertTrue(profile.user.check_password("Very-Strong-Test-Pass!1357"))
        self.assertEqual(profile.audit_history.count(), 1)

    def test_staff_cannot_open_admin_staff_directory(self):
        staff_user = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="Very-Strong-Test-Pass!1357",
            role=User.Role.STAFF,
        )
        StaffProfile.objects.create(
            user=staff_user,
            designation="Instructor",
            joining_date=date(2026, 1, 1),
        )
        self.client.force_login(staff_user)

        response = self.client.get(reverse("staff:list"))

        self.assertEqual(response.status_code, 403)

    def test_admin_can_assign_batches_from_staff_edit_page(self):
        staff_user = User.objects.create_user(
            username="unassigned-teacher",
            email="unassigned-teacher@example.com",
            password="Very-Strong-Test-Pass!1357",
            role=User.Role.STAFF,
        )
        profile = StaffProfile.objects.create(
            user=staff_user,
            designation="Instructor",
            joining_date=date(2026, 1, 1),
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("staff:edit", args=[profile.pk]),
            {
                "first_name": "Staff",
                "last_name": "Member",
                "email": staff_user.email,
                "phone": "",
                "address": "",
                "designation": "Instructor",
                "joining_date": "2026-01-01",
                "batches": [str(self.batch.pk)],
            },
        )

        self.assertRedirects(response, reverse("staff:list"))
        self.assertQuerySetEqual(
            profile.batches.all(), [self.batch], transform=lambda batch: batch
        )
