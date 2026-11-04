from django.conf import settings
from django.db import models


class StaffProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="staff_profile",
    )
    staff_id = models.CharField(max_length=20, unique=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    designation = models.CharField(max_length=100)
    joining_date = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_staff_profiles",
        null=True,
        blank=True,
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="modified_staff_profiles",
        null=True,
        blank=True,
    )
    batches = models.ManyToManyField(
        "academics.Batch", related_name="staff_members", blank=True
    )

    class Meta:
        ordering = ["user__last_name", "user__first_name", "staff_id"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.staff_id:
            self.staff_id = f"STF{self.pk:06d}"
            super().save(update_fields=["staff_id"])

    def __str__(self):
        return f"{self.staff_id or 'New staff'} - {self.user.get_full_name() or self.user.username}"


class StaffProfileAudit(models.Model):
    staff_profile = models.ForeignKey(
        StaffProfile, on_delete=models.PROTECT, related_name="audit_history"
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="staff_profile_audits",
    )
    action = models.CharField(max_length=20)
    changed_fields = models.JSONField(default=list)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.staff_profile.staff_id}: {self.action} by {self.changed_by}"
