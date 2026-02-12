import json
import re
from datetime import date

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from exam.dou_catalog import DOU_FACULTY_DEPARTMENTS, department_choices_for, faculty_choices

from . import models


class StudentUserForm(forms.ModelForm):
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


class StudentAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Username / Matric Number / Institutional Email",
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "placeholder": "e.g. UNN/2026/12345 or student@university.edu.ng",
            }
        ),
    )


class StudentForm(forms.ModelForm):
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
        model = models.Student
        fields = [
            "matric_number",
            "institutional_email",
            "faculty",
            "department",
            "programme",
            "current_level",
            "entry_year",
            "mobile",
            "address",
            "profile_pic",
        ]
        labels = {
            "matric_number": "Matriculation / Registration Number",
            "institutional_email": "Institutional Student Email",
            "mobile": "Official Phone Number",
            "address": "Contact Address",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["matric_number"].required = True
        self.fields["institutional_email"].required = True
        self.fields["faculty"].required = True
        self.fields["department"].required = True
        self.fields["programme"].required = True
        self.fields["current_level"].required = True
        self.fields["entry_year"].required = True

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

    def clean_matric_number(self):
        matric_number = (self.cleaned_data.get("matric_number") or "").strip().upper()

        if not re.match(r"^[A-Z0-9][A-Z0-9/-]{5,29}$", matric_number):
            raise forms.ValidationError(
                "Enter a valid matric/reg number (letters, numbers, slash or dash only)."
            )

        if not re.search(r"\d", matric_number):
            raise forms.ValidationError("Matric/reg number must include digits.")

        return matric_number

    def clean_institutional_email(self):
        institutional_email = (self.cleaned_data.get("institutional_email") or "").strip().lower()
        if not institutional_email.endswith(".edu.ng"):
            raise forms.ValidationError("Use an institutional email ending with .edu.ng.")
        return institutional_email

    def clean_entry_year(self):
        entry_year = self.cleaned_data["entry_year"]
        current_year = date.today().year
        if entry_year > current_year + 1:
            raise forms.ValidationError("Entry year cannot be in the far future.")
        return entry_year

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
