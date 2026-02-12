import json

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from exam.dou_catalog import DOU_FACULTY_DEPARTMENTS, department_choices_for, faculty_choices
from exam import models as QMODEL

from . import models


class TeacherUserForm(forms.ModelForm):
    accept_policies = forms.BooleanField(
        required=True,
        label="I agree to the Terms of Use and Privacy Policy.",
        error_messages={
            "required": "You must accept the Terms of Use and Privacy Policy to continue."
        },
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "password"]
        widgets = {
            "password": forms.PasswordInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Consent is mandatory for new registrations only.
        if self.instance and self.instance.pk:
            self.fields["accept_policies"].required = False


class TeacherAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Username / Staff ID / Official Email",
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "placeholder": "e.g. DOU/CSE/2026/014 or lecturer@university.edu.ng",
            }
        ),
    )


class TeacherForm(forms.ModelForm):
    faculty = forms.ChoiceField(
        choices=faculty_choices(),
        required=True,
        label="Faculty / College",
    )
    department = forms.ChoiceField(
        choices=department_choices_for(""),
        required=True,
        label="Department",
    )

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

        self.fields["faculty"].widget.attrs["data-department-map"] = json.dumps(
            DOU_FACULTY_DEPARTMENTS
        )

        selected_faculty = (self.data.get("faculty") or "").strip()
        if not selected_faculty and self.instance and self.instance.pk:
            selected_faculty = (getattr(self.instance, "faculty", "") or "").strip()

        selected_department = (self.data.get("department") or "").strip()
        if not selected_department and self.instance and self.instance.pk:
            selected_department = (getattr(self.instance, "department", "") or "").strip()

        faculty_options = faculty_choices()
        known_faculty = {choice[0] for choice in faculty_options if choice[0]}
        if selected_faculty and selected_faculty not in known_faculty:
            faculty_options.append((selected_faculty, f"{selected_faculty} (Legacy)"))
        self.fields["faculty"].choices = faculty_options

        department_options = department_choices_for(selected_faculty)
        known_department = {choice[0] for choice in department_options if choice[0]}
        if selected_department and selected_department not in known_department:
            department_options.append((selected_department, f"{selected_department} (Legacy)"))
        self.fields["department"].choices = department_options

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

    def clean(self):
        cleaned_data = super().clean()
        faculty = (cleaned_data.get("faculty") or "").strip()
        department = (cleaned_data.get("department") or "").strip()

        valid_departments = DOU_FACULTY_DEPARTMENTS.get(faculty)
        if valid_departments and department and department not in valid_departments:
            self.add_error(
                "department",
                "Select a department that matches the selected faculty.",
            )

        return cleaned_data


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
