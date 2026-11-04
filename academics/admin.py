from django.contrib import admin

from .models import Batch, Course


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("name",)


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "start_date", "end_date", "is_active")
    list_filter = ("course", "is_active")
    search_fields = ("name", "course__name", "course__code")
    ordering = ("course__name", "name")
