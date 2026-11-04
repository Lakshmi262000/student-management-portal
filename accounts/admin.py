from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Portal access", {"fields": ("role",)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Portal access", {"fields": ("email", "role")}),
    )
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = DjangoUserAdmin.list_filter + ("role",)
