from django import forms

from . import models


class ContactusForm(forms.Form):
    Name = forms.CharField(max_length=30)
    Email = forms.EmailField()
    Message = forms.CharField(max_length=500, widget=forms.Textarea(attrs={"rows": 3, "cols": 30}))


class CourseForm(forms.ModelForm):
    class Meta:
        model = models.Course
        fields = [
            "course_name",
            "duration_minutes",
            "pass_mark",
            "max_attempts",
            "negative_mark_per_wrong",
            "shuffle_questions",
            "instructions",
        ]
        widgets = {
            "instructions": forms.Textarea(attrs={"rows": 4}),
        }

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
