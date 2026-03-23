import re
from datetime import date
from django import forms
from django.contrib.auth.models import User
from . import models

class StudentUserForm(forms.ModelForm):
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
            "registration_status",
            "bio",
            "mobile",
            "address",
            "profile_pic",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field not in ["profile_pic", "bio"]:
                self.fields[field].required = True

    def clean_institutional_email(self):
        email = self.cleaned_data.get("institutional_email", "").lower()
        if not email.endswith(".edu.ng"):
            raise forms.ValidationError("Please use an institutional email ending in .edu.ng")
        return email
