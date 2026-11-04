from django.conf import settings
from django.db import models


class Student(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "F", "Female"
        MALE = "M", "Male"
        OTHER = "O", "Other"
        UNSPECIFIED = "U", "Prefer not to say"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="student_profile",
    )
    student_id = models.CharField(max_length=20, unique=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=1, choices=Gender.choices, default=Gender.UNSPECIFIED
    )
    address = models.TextField(blank=True)
    batch = models.ForeignKey(
        "academics.Batch",
        on_delete=models.PROTECT,
        related_name="students",
    )
    joining_date = models.DateField()
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="registered_students",
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="modified_students",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["user__last_name", "user__first_name", "student_id"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.student_id:
            self.student_id = f"STU{self.pk:06d}"
            super().save(update_fields=["student_id"])

    def __str__(self):
        return f"{self.student_id or 'New student'} - {self.user.get_full_name() or self.user.username}"

    @property
    def course(self):
        return self.batch.course


class StudentProfileAudit(models.Model):
    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name="audit_history"
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="student_profile_audits",
    )
    action = models.CharField(max_length=20)
    changed_fields = models.JSONField(default=list)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.student.student_id}: {self.action} by {self.changed_by}"
