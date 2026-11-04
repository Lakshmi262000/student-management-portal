from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from academics.models import Batch, Course
from staff.models import StaffProfile
from .models import Student


class StudentWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="Very-Strong-Test-Pass!1357",
        )
        self.staff_user = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="Very-Strong-Test-Pass!1357",
            role=User.Role.STAFF,
        )
        self.course = Course.objects.create(code="ENG", name="English")
        self.batch = Batch.objects.create(
            course=self.course, name="Batch 22", start_date=date(2026, 1, 1)
        )
        self.other_batch = Batch.objects.create(
            course=self.course, name="Batch 23", start_date=date(2026, 1, 1)
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.staff_user,
            designation="Teacher",
            joining_date=date(2026, 1, 1),
        )
        self.staff_profile.batches.add(self.batch)

    def student_data(self, username="learner"):
        return {
            "username": username,
            "email": f"{username}@example.com",
            "first_name": "Taylor",
            "last_name": "Student",
            "password": "Very-Strong-Test-Pass!1357",
            "phone": "5550100",
            "date_of_birth": "",
            "gender": Student.Gender.UNSPECIFIED,
            "address": "Example address",
            "course": self.course.name,
            "batch": self.batch.name,
            "joining_date": "2026-02-01",
        }

    def test_admin_registration_creates_account_and_profile_together(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("students:register"), self.student_data()
        )

        student = Student.objects.get(user__username="learner")
        self.assertRedirects(
            response, reverse("students:detail", args=[student.pk])
        )
        self.assertEqual(student.student_id, "STU000001")
        self.assertEqual(student.registered_by, self.admin)
        self.assertTrue(student.user.check_password("Very-Strong-Test-Pass!1357"))
        self.assertNotEqual(student.user.password, "Very-Strong-Test-Pass!1357")
        self.assertEqual(student.batch, self.batch)

    def test_admin_can_type_a_new_course_and_select_a_fixed_batch(self):
        self.client.force_login(self.admin)
        data = self.student_data()
        data.update(
            username="newcourse",
            email="newcourse@example.com",
            course="Computer Science",
            batch="Batch 26",
        )

        response = self.client.post(reverse("students:register"), data)

        student = Student.objects.get(user__username="newcourse")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(student.batch.name, "Batch 26")
        self.assertEqual(student.batch.course.name, "Computer Science")
        self.assertTrue(student.batch.course.code)
        self.assertEqual(student.batch.start_date, date(2026, 2, 1))

    def test_course_name_is_reused_without_case_sensitive_duplicates(self):
        self.client.force_login(self.admin)
        data = self.student_data()
        data.update(
            username="different-case",
            email="different-case@example.com",
            course="eNgLiSh",
        )

        response = self.client.post(reverse("students:register"), data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Course.objects.filter(name__iexact="English").count(), 1)
        self.assertEqual(
            Student.objects.get(user__username="different-case").batch.course,
            self.course,
        )

    def test_batch_options_are_the_six_requested_batches(self):
        from .forms import StudentRegistrationForm

        form = StudentRegistrationForm(actor=self.admin)

        self.assertEqual(
            [value for value, _label in form.fields["batch"].choices],
            [
                "Batch 22",
                "Batch 23",
                "Batch 24",
                "Batch 25",
                "Batch 26",
                "Batch 27",
            ],
        )

    def test_staff_can_register_only_into_an_assigned_batch(self):
        self.client.force_login(self.staff_user)
        data = self.student_data()
        response = self.client.post(reverse("students:register"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Student.objects.count(), 1)

        data = self.student_data(username="learner2")
        data["batch"] = self.other_batch.name
        response = self.client.post(reverse("students:register"), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Student.objects.count(), 1)

    def test_student_cannot_view_another_students_profile(self):
        first = User.objects.create_user(
            username="first",
            email="first@example.com",
            password="Very-Strong-Test-Pass!1357",
            role=User.Role.STUDENT,
        )
        second = User.objects.create_user(
            username="second",
            email="second@example.com",
            password="Very-Strong-Test-Pass!1357",
            role=User.Role.STUDENT,
        )
        own_profile = Student.objects.create(
            user=first,
            batch=self.batch,
            joining_date=date(2026, 2, 1),
            registered_by=self.admin,
        )
        other_profile = Student.objects.create(
            user=second,
            batch=self.batch,
            joining_date=date(2026, 2, 1),
            registered_by=self.admin,
        )
        self.client.force_login(first)

        response = self.client.get(
            reverse("students:detail", args=[other_profile.pk])
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self.client.get(reverse("students:detail", args=[own_profile.pk])).status_code,
            200,
        )
        response = self.client.get(reverse("students:detail", args=[own_profile.pk]))
        self.assertContains(response, 'class="back-button"')
        self.assertContains(response, 'href="/" data-back-button')

    def test_student_sidebar_profile_link_opens_their_own_profile(self):
        learner = User.objects.create_user(
            username="my-profile",
            email="my-profile@example.com",
            password="Very-Strong-Test-Pass!1357",
            role=User.Role.STUDENT,
        )
        student = Student.objects.create(
            user=learner,
            batch=self.batch,
            joining_date=date(2026, 2, 1),
            registered_by=self.admin,
        )
        self.client.force_login(learner)

        response = self.client.get(reverse("students:my_profile"))

        self.assertRedirects(response, reverse("students:detail", args=[student.pk]))
        dashboard = self.client.get(reverse("dashboard:home"))
        self.assertContains(dashboard, reverse("students:my_profile"))
        self.assertContains(dashboard, "menu-toggle")

    def test_staff_cannot_update_student_outside_assigned_batches(self):
        learner = User.objects.create_user(
            username="unassigned",
            email="unassigned@example.com",
            password="Very-Strong-Test-Pass!1357",
            role=User.Role.STUDENT,
        )
        student = Student.objects.create(
            user=learner,
            batch=self.other_batch,
            joining_date=date(2026, 2, 1),
            registered_by=self.admin,
        )
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse("students:edit", args=[student.pk]))

        self.assertEqual(response.status_code, 404)
