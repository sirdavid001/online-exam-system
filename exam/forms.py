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
    question = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Question",
    )

    class Meta:
        model = models.Question
        fields = [
            "question_type",
            "marks",
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
            "explanation": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["question"].initial = self.instance.question_text

    def clean(self):
        cleaned_data = super().clean()
        q_type = cleaned_data.get("question_type")
        answer = (cleaned_data.get("answer") or "").strip()
        question_text = (cleaned_data.get("question") or "").strip()

        if not question_text:
            self.add_error("question", "Question text is required.")
        cleaned_data["question_text"] = question_text

        if q_type == "MCQ":
            mcq_map = {
                "1": "Option1",
                "2": "Option2",
                "3": "Option3",
                "4": "Option4",
                "option1": "Option1",
                "option2": "Option2",
                "option3": "Option3",
                "option4": "Option4",
            }
            normalized_answer = mcq_map.get(answer.lower())
            if not normalized_answer:
                self.add_error("answer", "For MCQ, select Option 1-4.")
            else:
                cleaned_data["answer"] = normalized_answer
        elif q_type == "TRUE_FALSE":
            true_false_map = {
                "1": "Option1",
                "true": "Option1",
                "option1": "Option1",
                "2": "Option2",
                "false": "Option2",
                "option2": "Option2",
            }
            normalized_answer = true_false_map.get(answer.lower())
            if not normalized_answer:
                self.add_error("answer", "For True/False, choose True or False.")
            else:
                cleaned_data["answer"] = normalized_answer
            cleaned_data["option1"] = "True"
            cleaned_data["option2"] = "False"
            cleaned_data["option3"] = ""
            cleaned_data["option4"] = ""
        elif q_type == "SHORT_ANSWER":
            if not answer:
                self.add_error("answer", "Provide the expected short answer text.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.question_text = self.cleaned_data["question_text"]
        if commit:
            instance.save()
            self.save_m2m()
        return instance
