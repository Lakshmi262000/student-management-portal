from django.contrib import admin

from .models import AttendanceAuditLog, StaffAttendance, StudentAttendance


class AttendanceAdmin(admin.ModelAdmin):
    list_filter = ("date", "status")
    date_hierarchy = "date"
    readonly_fields = ("marked_by", "modified_by", "updated_at")

    def save_model(self, request, obj, form, change):
        old_status = obj.status if change else ""
        if not change:
            obj.marked_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)
        if old_status != obj.status:
            AttendanceAuditLog.objects.create(
                **(
                    {"student_attendance": obj}
                    if isinstance(obj, StudentAttendance)
                    else {"staff_attendance": obj}
                ),
                changed_by=request.user,
                old_status=old_status,
                new_status=obj.status,
            )


@admin.register(StudentAttendance)
class StudentAttendanceAdmin(AttendanceAdmin):
    list_display = ("date", "student", "status", "marked_by", "modified_by")
    search_fields = (
        "student__student_id",
        "student__user__first_name",
        "student__user__last_name",
    )
    autocomplete_fields = ("student",)

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj:
            fields.extend(("student", "date"))
        return fields


@admin.register(StaffAttendance)
class StaffAttendanceAdmin(AttendanceAdmin):
    list_display = ("date", "staff", "status", "marked_by", "modified_by")
    search_fields = (
        "staff__staff_id",
        "staff__user__first_name",
        "staff__user__last_name",
    )
    autocomplete_fields = ("staff",)

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj:
            fields.extend(("staff", "date"))
        return fields


@admin.register(AttendanceAuditLog)
class AttendanceAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "changed_at",
        "student_attendance",
        "staff_attendance",
        "old_status",
        "new_status",
        "changed_by",
    )
    list_filter = ("changed_at", "new_status")
    readonly_fields = (
        "student_attendance",
        "staff_attendance",
        "changed_by",
        "old_status",
        "new_status",
        "changed_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff
