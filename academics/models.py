from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower


class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), name="unique_course_name_case_insensitive"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Batch(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.PROTECT, related_name="batches"
    )
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["course__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "name"], name="unique_batch_name_per_course"
            ),
        ]

    def clean(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot be before start date."})

    def __str__(self):
        return f"{self.course.name} - {self.name}"
