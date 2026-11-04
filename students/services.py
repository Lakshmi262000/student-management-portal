from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from accounts.models import User
from academics.models import Batch, Course
from .models import Student, StudentProfileAudit


def _course_code(course_name):
    base = slugify(course_name).replace("-", "").upper() or "COURSE"
    base = base[:20]
    code = base
    suffix = 1
    while Course.objects.filter(code=code).exists():
        suffix += 1
        suffix_text = str(suffix)
        code = f"{base[:20 - len(suffix_text)]}{suffix_text}"
    return code


@transaction.atomic
def register_student(*, data, registered_by):
    validate_password(data["password"])
    course_name = data["course"].strip()
    course = Course.objects.filter(name__iexact=course_name).first()
    if course is None:
        if registered_by.role != User.Role.ADMIN:
            raise ValidationError("Only admins can add a new course.")
        course = Course.objects.create(
            name=course_name,
            code=_course_code(course_name),
        )
    if not course.is_active:
        raise ValidationError("The selected course is inactive.")

    if registered_by.role == User.Role.STAFF:
        batch = Batch.objects.filter(
            course=course,
            name=data["batch"],
            is_active=True,
            staff_members__user=registered_by,
        ).first()
        if batch is None:
            raise ValidationError(
                "You can register students only in an assigned batch."
            )
    else:
        batch, _ = Batch.objects.get_or_create(
            course=course,
            name=data["batch"],
            defaults={"start_date": data["joining_date"]},
        )
        if not batch.is_active:
            raise ValidationError("The selected batch is inactive.")

    user = User.objects.create_user(
        username=data["username"],
        email=data["email"],
        password=data["password"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        role=User.Role.STUDENT,
    )
    student = Student.objects.create(
        user=user,
        phone=data["phone"],
        date_of_birth=data["date_of_birth"],
        gender=data["gender"],
        address=data["address"],
        batch=batch,
        joining_date=data["joining_date"],
        registered_by=registered_by,
    )
    StudentProfileAudit.objects.create(
        student=student,
        changed_by=registered_by,
        action="created",
        changed_fields=[
            "user",
            "phone",
            "date_of_birth",
            "gender",
            "address",
            "batch",
            "joining_date",
        ],
    )
    return student
