import re

from django import forms

from . import models


DOU_COURSE_CATALOG = (
    "GST 111 - Communication in English",
    "GST 112 - Nigerian Peoples and Culture",
    "GST 113 - Logic, Philosophy and Human Existence",
    "GST 121 - Use of Library, Study Skills and ICT",
    "MTH 111 - Elementary Mathematics I",
    "MTH 112 - Elementary Mathematics II",
    "CSC 111 - Introduction to Computer Science",
    "CSC 121 - Programming Fundamentals",
    "CSC 122 - Structured Programming with C",
    "CSC 123 - Introduction to Python Programming",
    "CSC 211 - Data Structures",
    "CSC 221 - Object-Oriented Programming",
    "CSC 222 - Java Programming",
    "CSC 223 - C++ Programming",
    "CSC 231 - Database Systems I",
    "CSC 311 - Operating Systems",
    "CSC 312 - Web Programming (HTML, CSS, JavaScript)",
    "CSC 321 - Computer Networks",
    "CSC 322 - Scripting Languages (Python/PHP)",
    "CSC 331 - Software Engineering",
    "CSC 411 - Artificial Intelligence",
    "CSC 412 - Mobile Application Development (Kotlin/Java)",
    "CSC 422 - Data Science with Python",
    "PHY 111 - General Physics I",
    "PHY 112 - General Physics II",
    "CHM 111 - General Chemistry I",
    "CHM 112 - General Chemistry II",
    "BIO 111 - General Biology I",
    "BIO 112 - General Biology II",
    "ECO 111 - Principles of Economics I",
    "ACC 111 - Principles of Accounting I",
    "EDU 111 - Introduction to Educational Foundations",
)


class ContactusForm(forms.Form):
    Name = forms.CharField(max_length=30)
    Email = forms.EmailField()
    Message = forms.CharField(max_length=500, widget=forms.Textarea(attrs={"rows": 3, "cols": 30}))


class CourseForm(forms.ModelForm):
    available_course = forms.ChoiceField(
        required=False,
        label="Available Courses (Dennis Osadebay University)",
        choices=(("", "Select from DOU course catalogue"),)
        + tuple((course, course) for course in DOU_COURSE_CATALOG),
    )

    class Meta:
        model = models.Course
        fields = [
            "course_name",
            "course_code",
            "level",
            "semester",
            "academic_session",
            "duration_minutes",
            "pass_mark",
            "max_attempts",
            "negative_mark_per_wrong",
            "shuffle_questions",
            "is_published",
            "available_from",
            "available_until",
            "instructions",
        ]
        widgets = {
            "instructions": forms.Textarea(attrs={"rows": 4}),
            "available_from": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "available_until": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course_name"].required = False
        for field_name in ("available_from", "available_until"):
            field = self.fields[field_name]
            field.required = False
            if self.instance and getattr(self.instance, field_name):
                field.initial = getattr(self.instance, field_name).strftime("%Y-%m-%dT%H:%M")
        instance_course_name = getattr(self.instance, "course_name", "")
        if instance_course_name in DOU_COURSE_CATALOG:
            self.fields["available_course"].initial = instance_course_name

    def clean(self):
        cleaned_data = super().clean()
        selected_course = (cleaned_data.get("available_course") or "").strip()
        typed_course = (cleaned_data.get("course_name") or "").strip()

        if selected_course:
            cleaned_data["course_name"] = selected_course
        elif not typed_course:
            self.add_error(
                "course_name",
                "Select a course from the DOU catalogue or enter a course name manually.",
            )
        else:
            cleaned_data["course_name"] = typed_course

        available_from = cleaned_data.get("available_from")
        available_until = cleaned_data.get("available_until")
        if available_from and available_until and available_until <= available_from:
            self.add_error("available_until", "Available until must be later than available from.")

        return cleaned_data

    def clean_duration_minutes(self):
        duration = self.cleaned_data["duration_minutes"]
        if duration <= 0:
            raise forms.ValidationError("Duration must be greater than 0 minutes.")
        return duration

    def clean_pass_mark(self):
        pass_mark = self.cleaned_data["pass_mark"]
        if pass_mark < 0 or pass_mark > 100:
            raise forms.ValidationError("Pass mark must be between 0 and 100.")
        return pass_mark

    def clean_max_attempts(self):
        max_attempts = self.cleaned_data["max_attempts"]
        if max_attempts <= 0:
            raise forms.ValidationError("Max attempts must be at least 1.")
        return max_attempts

    def clean_negative_mark_per_wrong(self):
        negative_mark = self.cleaned_data["negative_mark_per_wrong"]
        if negative_mark < 0:
            raise forms.ValidationError("Negative mark value cannot be less than 0.")
        return negative_mark

    def clean_academic_session(self):
        academic_session = (self.cleaned_data.get("academic_session") or "").strip()
        if academic_session and not re.match(r"^\d{4}/\d{4}$", academic_session):
            raise forms.ValidationError("Academic session must follow the format YYYY/YYYY.")
        return academic_session


class InstitutionSettingsForm(forms.ModelForm):
    class Meta:
        model = models.InstitutionSettings
        fields = [
            "institution_name",
            "short_name",
            "official_website",
            "support_email",
            "support_phone",
            "address",
            "current_session",
            "current_semester",
            "allow_student_signup",
            "allow_teacher_signup",
        ]

    def clean_current_session(self):
        current_session = (self.cleaned_data.get("current_session") or "").strip()
        if not re.match(r"^\d{4}/\d{4}$", current_session):
            raise forms.ValidationError("Current session must follow the format YYYY/YYYY.")
        return current_session


class AdminAnnouncementForm(forms.ModelForm):
    class Meta:
        model = models.AdminAnnouncement
        fields = ["title", "audience", "message", "is_active", "starts_at", "ends_at"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4}),
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "ends_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("starts_at", "ends_at"):
            field = self.fields[field_name]
            field.required = False
            if self.instance and getattr(self.instance, field_name):
                field.initial = getattr(self.instance, field_name).strftime("%Y-%m-%dT%H:%M")

    def clean(self):
        cleaned_data = super().clean()
        starts_at = cleaned_data.get("starts_at")
        ends_at = cleaned_data.get("ends_at")
        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error("ends_at", "End time must be later than start time.")
        return cleaned_data


class QuestionForm(forms.ModelForm):
    # Show course names in dropdown via __str__.
    courseID = forms.ModelChoiceField(
        queryset=models.Course.objects.all().order_by("course_name"),
        empty_label="Select Course",
        to_field_name="id",
    )

    class Meta:
        model = models.Question
        fields = [
            "marks",
            "question",
            "option1",
            "option2",
            "option3",
            "option4",
            "answer",
            "difficulty",
            "explanation",
        ]
        widgets = {
            "question": forms.Textarea(attrs={"rows": 4}),
            "explanation": forms.Textarea(attrs={"rows": 3}),
        }
