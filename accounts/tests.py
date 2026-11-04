from django.test import TestCase
from django.urls import reverse

from .models import User


class UserManagerTests(TestCase):
    def test_create_user_hashes_password_and_sets_default_role(self):
        user = User.objects.create_user(
            username="student1",
            email="student@example.com",
            password="safe-test-password",
        )

        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(user.check_password("safe-test-password"))
        self.assertNotEqual(user.password, "safe-test-password")

    def test_create_superuser_has_admin_role(self):
        user = User.objects.create_superuser(
            username="portal-admin",
            email="admin@example.com",
            password="safe-test-password",
        )

        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class LoginFlowTests(TestCase):
    def test_user_can_sign_in_and_reach_dashboard(self):
        User.objects.create_user(
            username="student1",
            email="student@example.com",
            password="safe-test-password",
        )

        response = self.client.post(
            reverse("login"),
            {"username": "student1", "password": "safe-test-password"},
        )

        self.assertRedirects(response, reverse("dashboard:home"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_page_is_rendered(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back")

    def test_password_reset_page_is_available(self):
        response = self.client.get(reverse("password_reset"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reset your password")

    def test_staff_role_cannot_enter_django_admin_even_if_is_staff_is_set(self):
        user = User.objects.create_user(
            username="staff-admin-check",
            email="staff-admin-check@example.com",
            password="safe-test-password",
            role=User.Role.STAFF,
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 403)
