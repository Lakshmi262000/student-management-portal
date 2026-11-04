from django.urls import path

from . import views


app_name = "attendance"

urlpatterns = [
    path("batch/<int:batch_id>/mark/", views.mark_students, name="mark_students"),
    path("staff/mark/", views.mark_staff, name="mark_staff"),
    path("daily/", views.daily_report, name="daily_report"),
    path("reports/", views.reports, name="reports"),
    path("staff/history/", views.staff_attendance_history, name="staff_history"),
]
