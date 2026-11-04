from functools import wraps

from django.core.exceptions import PermissionDenied

from .models import User


def roles_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login

                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


ADMIN_ROLES = (User.Role.ADMIN,)
STUDENT_REGISTRAR_ROLES = (User.Role.ADMIN, User.Role.STAFF)
