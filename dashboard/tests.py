from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class DashboardAccessTests(TestCase):
    def test_dashboard_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse("dashboard:home"))

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("dashboard:home")}',
        )

    def test_authenticated_user_can_open_dashboard(self):
        user = User.objects.create_user(
            username="learner",
            email="learner@example.com",
            password="safe-test-password",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student dashboard")

    def test_admin_dashboard_shows_management_counts_and_links(self):
        user = User.objects.create_superuser(
            username="administrator",
            email="admin@example.com",
            password="Very-Strong-Test-Pass!1357",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin dashboard")
        self.assertContains(response, "Register student")
        self.assertContains(response, "Students")

    def test_health_endpoint_returns_ok(self):
        response = self.client.get(reverse("dashboard:health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_authenticated_dashboard_has_responsive_back_navigation(self):
        user = User.objects.create_user(
            username="staff-member",
            email="staff-member@example.com",
            password="Very-Strong-Test-Pass!1357",
            role=User.Role.STAFF,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("dashboard:home"))

        self.assertContains(response, "Back")
        self.assertContains(response, "sidebar-scrim")
        self.assertContains(response, "portal-navigation.js")
        self.assertContains(response, "Assigned students")
        self.assertContains(response, "STUDENT MANAGEMENT")
        self.assertContains(response, "Change password")
        self.assertContains(response, "Sign out")
        self.assertContains(response, "<svg", html=False)
