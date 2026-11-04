from django import forms
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q

from accounts.models import User
from academics.models import Batch
from .models import StaffProfile


class StaffCreationForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    password = forms.CharField(widget=forms.PasswordInput, validators=[validate_password])
    phone = forms.CharField(max_length=30, required=False)
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    designation = forms.CharField(max_length=100)
    joining_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    batches = forms.ModelMultipleChoiceField(
        queryset=Batch.objects.filter(is_active=True),
        required=False,
        label="Assigned batches",
        help_text=(
            "Staff can view and mark attendance for students in these batches. "
            "Register students into the same batches to assign them to this staff member."
        ),
    )

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


class StaffProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()

    class Meta:
        model = StaffProfile
        fields = [
            "first_name", "last_name", "email", "phone",
            "address", "designation", "joining_date", "batches",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "joining_date": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts = {
            "batches": (
                "The staff member can access students in these batches. "
                "Assign students by registering them into one of these batches."
            ),
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.fields["first_name"].initial = self.instance.user.first_name
        self.fields["last_name"].initial = self.instance.user.last_name
        self.fields["email"].initial = self.instance.user.email
        if self.instance.pk:
            assigned_ids = self.instance.batches.values_list("pk", flat=True)
            self.fields["batches"].queryset = Batch.objects.filter(
                Q(is_active=True) | Q(pk__in=assigned_ids)
            )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exclude(
            pk=self.instance.user_id
        ).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.user.first_name = self.cleaned_data["first_name"]
        profile.user.last_name = self.cleaned_data["last_name"]
        profile.user.email = self.cleaned_data["email"]
        if self.actor:
            profile.modified_by = self.actor
        if commit:
            profile.user.save()
            profile.save()
            self.save_m2m()
        return profile
