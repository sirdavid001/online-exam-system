from django import forms
from django.contrib.auth.models import User

from exam import models as QMODEL

from . import models


class TeacherUserForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "password"]
        widgets = {
            "password": forms.PasswordInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class TeacherForm(forms.ModelForm):
    class Meta:
        model = models.Teacher
        fields = [
            "staff_id",
            "official_email",
            "faculty",
            "department",
            "designation",
            "mobile",
            "address",
            "profile_pic",
        ]
        labels = {
            "staff_id": "Staff ID / Employee Number",
            "official_email": "Official University Email",
            "mobile": "Official Phone Number",
            "address": "Office Address",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["staff_id"].required = True
        self.fields["official_email"].required = True
        self.fields["faculty"].required = True
        self.fields["department"].required = True
        self.fields["designation"].required = True

    def clean_staff_id(self):
        staff_id = (self.cleaned_data.get("staff_id") or "").strip().upper()
        if len(staff_id) < 5:
            raise forms.ValidationError("Staff ID must be at least 5 characters long.")
        return staff_id

    def clean_official_email(self):
        official_email = (self.cleaned_data.get("official_email") or "").strip().lower()
        if not official_email.endswith(".edu.ng"):
            raise forms.ValidationError(
                "Use an official university email ending with .edu.ng."
            )
        return official_email


class QuestionUploadForm(forms.Form):
    courseID = forms.ModelChoiceField(
        queryset=QMODEL.Course.objects.all().order_by("course_name"),
        empty_label="Select Course",
        to_field_name="id",
        label="Course",
    )
    questions_file = forms.FileField(label="Question File")
    has_header = forms.BooleanField(
        required=False,
        initial=True,
        label="File contains a header row",
    )
