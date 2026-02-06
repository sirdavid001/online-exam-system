import re
from datetime import date

from django import forms
from django.contrib.auth.models import User

from . import models


class StudentUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "password"]
        widgets = {
            "password": forms.PasswordInput(),
        }


class StudentForm(forms.ModelForm):
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
