from django.urls import path

from . import views


app_name = "staff"

urlpatterns = [
    path("", views.staff_list, name="list"),
    path("add/", views.staff_create, name="create"),
    path("profile/", views.staff_profile, name="profile"),
    path("<int:pk>/edit/", views.staff_edit, name="edit"),
    path("<int:pk>/deactivate/", views.staff_deactivate, name="deactivate"),
]
