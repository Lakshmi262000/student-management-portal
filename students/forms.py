from django import forms
from django.contrib.auth.password_validation import validate_password
from accounts.models import User
from academics.models import Batch, Course
from .models import Student


BATCH_CHOICES = tuple((f"Batch {year}", f"Batch {year}") for year in range(22, 28))


class StudentRegistrationForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    password = forms.CharField(
        widget=forms.PasswordInput,
        validators=[validate_password],
        help_text="Set a temporary password and share it with the student securely.",
    )
    phone = forms.CharField(max_length=30, required=False)
    date_of_birth = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    gender = forms.ChoiceField(choices=Student.Gender.choices)
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    course = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"placeholder": "Enter course name"}),
    )
    batch = forms.ChoiceField(choices=BATCH_CHOICES)
    joining_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.assigned_batches = Batch.objects.none()
        if actor.role == User.Role.STAFF:
            self.assigned_batches = Batch.objects.filter(
                is_active=True, staff_members__user=actor
            ).distinct()
            self.fields["course"].help_text = (
                "Enter the name of a course assigned to you."
            )
            self.fields["course"].widget.attrs["list"] = "assigned-courses"
            self.course_choices = list(
                self.assigned_batches.values_list("course__name", flat=True).distinct()
            )
        else:
            self.course_choices = list(
                Course.objects.filter(is_active=True)
                .order_by("name")
                .values_list("name", flat=True)
            )
            self.fields["course"].widget.attrs["list"] = "existing-courses"

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already in use.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def clean_course(self):
        course_name = self.cleaned_data["course"].strip()
        if not course_name:
            raise forms.ValidationError("Enter a course name.")
        course = Course.objects.filter(name__iexact=course_name).first()
        if course and not course.is_active:
            raise forms.ValidationError("This course is inactive.")
        if self.actor.role == User.Role.STAFF and not Course.objects.filter(
            name__iexact=course_name,
            batches__staff_members__user=self.actor,
            batches__is_active=True,
        ).exists():
            raise forms.ValidationError(
                "You can register students only for an assigned course."
            )
        return course_name

    def clean(self):
        cleaned = super().clean()
        course_name = cleaned.get("course")
        batch = cleaned.get("batch")
        if self.actor.role == User.Role.STAFF and course_name and batch:
            if not self.assigned_batches.filter(
                course__name__iexact=course_name, name=batch
            ).exists():
                self.add_error(
                    "batch",
                    "You can register students only in an assigned batch.",
                )
        elif course_name and batch:
            course = Course.objects.filter(name__iexact=course_name).first()
            if course and Batch.objects.filter(
                course=course, name=batch, is_active=False
            ).exists():
                self.add_error("batch", "This batch is inactive.")
        return cleaned


class StudentUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()

    class Meta:
        model = Student
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "date_of_birth",
            "gender",
            "address",
            "batch",
            "joining_date",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "joining_date": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.fields["first_name"].initial = self.instance.user.first_name
        self.fields["last_name"].initial = self.instance.user.last_name
        self.fields["email"].initial = self.instance.user.email
        batches = Batch.objects.filter(is_active=True)
        if actor.role == User.Role.STAFF:
            batches = batches.filter(staff_members__user=actor)
            if self.instance.pk:
                batches = batches | Batch.objects.filter(pk=self.instance.batch_id)
        elif self.instance.pk:
            batches = batches | Batch.objects.filter(pk=self.instance.batch_id)
        self.fields["batch"].queryset = batches.distinct()

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exclude(
            pk=self.instance.user_id
        ).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def save(self, commit=True):
        student = super().save(commit=False)
        student.modified_by = self.actor
        student.user.first_name = self.cleaned_data["first_name"]
        student.user.last_name = self.cleaned_data["last_name"]
        student.user.email = self.cleaned_data["email"]
        if commit:
            student.user.save()
            student.save()
        return student
