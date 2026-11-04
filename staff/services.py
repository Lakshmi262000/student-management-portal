from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from accounts.models import User
from .models import StaffProfile, StaffProfileAudit


@transaction.atomic
def create_staff(*, data, created_by):
    validate_password(data["password"])
    user = User.objects.create_user(
        username=data["username"],
        email=data["email"],
        password=data["password"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        role=User.Role.STAFF,
    )
    profile = StaffProfile.objects.create(
        user=user,
        phone=data["phone"],
        address=data["address"],
        designation=data["designation"],
        joining_date=data["joining_date"],
        created_by=created_by,
        modified_by=created_by,
    )
    profile.batches.set(data["batches"])
    StaffProfileAudit.objects.create(
        staff_profile=profile,
        changed_by=created_by,
        action="created",
        changed_fields=[
            "user",
            "phone",
            "address",
            "designation",
            "joining_date",
            "batches",
        ],
    )
    return profile
