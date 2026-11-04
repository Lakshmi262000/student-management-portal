from django.core.exceptions import PermissionDenied

from .models import User


class AdminRoleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.path_info.startswith("/admin/")
            and request.user.is_authenticated
            and request.user.role != User.Role.ADMIN
        ):
            raise PermissionDenied
        return self.get_response(request)
