from django import forms

from .models import AttendanceStatus


class AttendanceDateForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))


class AttendanceReportFilterForm(forms.Form):
    month = forms.IntegerField(min_value=1, max_value=12)
    year = forms.IntegerField(min_value=2000, max_value=2200)

    def __init__(self, *args, **kwargs):
        from django.utils import timezone

        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        self.fields["month"].initial = today.month
        self.fields["year"].initial = today.year


def attendance_choice_field():
    return forms.ChoiceField(choices=AttendanceStatus.choices)
