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
    ANSWER_CHOICES = (
        ("Option1", "Option 1"),
        ("Option2", "Option 2"),
        ("Option3", "Option 3"),
        ("Option4", "Option 4"),
    )

    TF_ANSWER_CHOICES = (
        ("Option1", "True"),
        ("Option2", "False"),
    )

    courseID = forms.ModelChoiceField(
        queryset=models.Course.objects.all().order_by("course_name"),
        empty_label="Select Course",
        to_field_name="id",
        required=False,
    )

    # Use a flexible answer field in the form as well.
    # We will override this in __init__ or just handle it in clean()
    answer = forms.CharField(max_length=200, help_text="For MCQ/TF, select the option. For Short Answer, enter the exact text.")

    class Meta:
        model = models.Question
        fields = [
            "question_type",
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

    def clean(self):
        cleaned_data = super().clean()
        q_type = cleaned_data.get("question_type")
        answer = cleaned_data.get("answer")

        if q_type == "MCQ":
            valid_options = ["Option1", "Option2", "Option3", "Option4"]
            if answer not in valid_options:
                self.add_error("answer", "Please select a valid option for Multiple Choice Questions.")
        elif q_type == "TRUE_FALSE":
            valid_options = ["Option1", "Option2"]
            if answer not in valid_options:
                self.add_error("answer", "Please select True or False.")
            # Clear unused options
            cleaned_data["option3"] = ""
            cleaned_data["option4"] = ""
            # Ensure options are set correctly
            cleaned_data["option1"] = "True"
            cleaned_data["option2"] = "False"
        elif q_type == "SHORT_ANSWER":
            if not answer:
                self.add_error("answer", "Please provide the correct answer for the short answer question.")
            # Options are not needed for short answer
            cleaned_data["option1"] = ""
            cleaned_data["option2"] = ""
            cleaned_data["option3"] = ""
            cleaned_data["option4"] = ""

        return cleaned_data
