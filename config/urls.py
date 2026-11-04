from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("students/", include("students.urls")),
    path("staff/", include("staff.urls")),
    path("attendance/", include("attendance.urls")),
    path("", include("dashboard.urls")),
]
