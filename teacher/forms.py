from django import forms
from django.contrib.auth.models import User
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

    def clean_official_email(self):
        email = self.cleaned_data.get("official_email", "").lower()
        if not email.endswith(".edu.ng"):
            raise forms.ValidationError("Please use an official email ending in .edu.ng")
        return email
