from django.contrib import admin

from .models import StaffProfile, StaffProfileAudit


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("staff_id", "full_name", "user", "designation", "joining_date")
    list_filter = ("designation", "batches")
    search_fields = ("staff_id", "user__first_name", "user__last_name", "user__email")
    autocomplete_fields = ("user",)
    filter_horizontal = ("batches",)
    readonly_fields = ("staff_id",)

    def save_model(self, request, obj, form, change):
        changed_fields = list(form.changed_data)
        if change:
            previous = StaffProfile.objects.select_related("user").get(pk=obj.pk)
            for field in ("first_name", "last_name", "email"):
                if getattr(previous.user, field) != getattr(obj.user, field):
                    changed_fields.append(field)
        obj.modified_by = request.user
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        if not change or changed_fields:
            StaffProfileAudit.objects.create(
                staff_profile=obj,
                changed_by=request.user,
                action="updated" if change else "created",
                changed_fields=changed_fields or ["profile"],
            )

    @admin.display(description="Name")
    def full_name(self, obj):
        return obj.user.get_full_name()


@admin.register(StaffProfileAudit)
class StaffProfileAuditAdmin(admin.ModelAdmin):
    list_display = ("staff_profile", "action", "changed_by", "changed_at")
    list_filter = ("action", "changed_at")
    readonly_fields = (
        "staff_profile", "changed_by", "action", "changed_fields", "changed_at"
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff
