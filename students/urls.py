from django.urls import path

from . import views


app_name = "students"

urlpatterns = [
    path("", views.student_list, name="list"),
    path("register/", views.student_register, name="register"),
    path("me/", views.my_profile, name="my_profile"),
    path("<int:pk>/", views.student_detail, name="detail"),
    path("<int:pk>/edit/", views.student_update, name="edit"),
    path("<int:pk>/deactivate/", views.student_deactivate, name="deactivate"),
]
