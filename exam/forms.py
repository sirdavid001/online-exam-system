from django import forms
from . import models

class CategoryForm(forms.ModelForm):
    class Meta:
        model = models.Category
        fields = ["name", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }

class CourseForm(forms.ModelForm):
    class Meta:
        model = models.Course
        fields = [
            "course_name",
            "category",
            "duration_minutes",
            "pass_mark",
            "max_attempts",
            "negative_mark_per_wrong",
            "shuffle_questions",
            "shuffle_options",
            "enable_proctoring",
            "allow_navigation",
            "show_explanation_after_exam",
            "is_published",
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

class QuestionForm(forms.ModelForm):
    courseID = forms.ModelChoiceField(
        queryset=models.Course.objects.all().order_by("course_name"),
        empty_label="Select Course",
        to_field_name="id",
        required=False,
    )

    class Meta:
        model = models.Question
        fields = [
            "question_type",
            "marks",
            "question_text",
            "difficulty",
            "image",
            "option1",
            "option2",
            "option3",
            "option4",
            "answer",
            "explanation",
        ]
        widgets = {
            "question_text": forms.Textarea(attrs={"rows": 4}),
            "explanation": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        q_type = cleaned_data.get("question_type")
        answer = cleaned_data.get("answer")

        if q_type == "MCQ":
            if answer not in ["1", "2", "3", "4"]:
                self.add_error("answer", "For MCQ, enter the correct option number (1-4).")
        elif q_type == "TRUE_FALSE":
            if answer.lower() not in ["1", "2", "true", "false"]:
                self.add_error("answer", "For True/False, enter 1 (True) or 2 (False).")
            cleaned_data["option1"] = "True"
            cleaned_data["option2"] = "False"
            cleaned_data["option3"] = ""
            cleaned_data["option4"] = ""
        
        return cleaned_data
