from django.contrib import admin

from .models import Student, StudentProfileAudit


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id", "full_name", "user", "batch", "joining_date")
    list_filter = ("batch__course", "batch", "gender")
    search_fields = ("student_id", "user__first_name", "user__last_name", "user__email")
    autocomplete_fields = ("user", "batch", "registered_by")
    readonly_fields = ("student_id",)

    def save_model(self, request, obj, form, change):
        changed_fields = list(form.changed_data)
        if change:
            previous = Student.objects.select_related("user").get(pk=obj.pk)
            for field in ("first_name", "last_name", "email"):
                old_value = getattr(previous.user, field)
                new_value = getattr(obj.user, field)
                if old_value != new_value:
                    changed_fields.append(field)
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)
        if not change or changed_fields:
            StudentProfileAudit.objects.create(
                student=obj,
                changed_by=request.user,
                action="updated" if change else "created",
                changed_fields=changed_fields or ["profile"],
            )

    @admin.display(description="Name")
    def full_name(self, obj):
        return obj.user.get_full_name()


@admin.register(StudentProfileAudit)
class StudentProfileAuditAdmin(admin.ModelAdmin):
    list_display = ("student", "action", "changed_by", "changed_at")
    list_filter = ("action", "changed_at")
    readonly_fields = ("student", "changed_by", "action", "changed_fields", "changed_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff
