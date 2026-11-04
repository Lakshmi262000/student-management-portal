from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("A username is required.")
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields["role"] = User.Role.ADMIN
        if extra_fields["is_staff"] is not True:
            raise ValueError("A superuser must have is_staff=True.")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("A superuser must have is_superuser=True.")
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        STAFF = "STAFF", "Staff"
        STUDENT = "STUDENT", "Student"

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )

    objects = UserManager()

    REQUIRED_FIELDS = ["email"]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("username"), name="unique_username_case_insensitive"
            ),
            models.UniqueConstraint(
                Lower("email"), name="unique_email_case_insensitive"
            ),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
