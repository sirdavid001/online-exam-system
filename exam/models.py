from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from student.models import Student


class Course(models.Model):
    course_name = models.CharField(max_length=120)
    question_number = models.PositiveIntegerField(default=0)
    total_marks = models.PositiveIntegerField(default=0)

    # University-grade exam controls
    duration_minutes = models.PositiveIntegerField(default=60)
    pass_mark = models.PositiveIntegerField(default=50)
    max_attempts = models.PositiveIntegerField(default=3)
    negative_mark_per_wrong = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    shuffle_questions = models.BooleanField(default=True)
    instructions = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["course_name"]

    def __str__(self):
        return self.course_name

    def refresh_assessment_totals(self):
        metrics = self.question_set.aggregate(
            question_total=models.Count("id"),
            mark_total=Sum("marks"),
        )
        self.question_number = metrics["question_total"] or 0
        self.total_marks = metrics["mark_total"] or 0
        self.save(update_fields=["question_number", "total_marks"])


class Question(models.Model):
    DIFFICULTY_CHOICES = (
        ("BEGINNER", "Beginner"),
        ("INTERMEDIATE", "Intermediate"),
        ("ADVANCED", "Advanced"),
    )

    ANSWER_CHOICES = (
        ("Option1", "Option 1"),
        ("Option2", "Option 2"),
        ("Option3", "Option 3"),
        ("Option4", "Option 4"),
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    marks = models.PositiveIntegerField(default=1)
    question = models.TextField()
    option1 = models.CharField(max_length=500)
    option2 = models.CharField(max_length=500)
    option3 = models.CharField(max_length=500)
    option4 = models.CharField(max_length=500)
    answer = models.CharField(max_length=200, choices=ANSWER_CHOICES)
    explanation = models.TextField(blank=True, default="")
    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default="INTERMEDIATE",
    )

    class Meta:
        ordering = ["id"]


class Result(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Course, on_delete=models.CASCADE)
    attempt_number = models.PositiveIntegerField(default=1)

    marks = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    total_possible_marks = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)

    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    unanswered = models.PositiveIntegerField(default=0)

    percentage = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    passed = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-attempt_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "exam", "attempt_number"],
                name="unique_result_attempt_per_exam",
            )
        ]


@receiver(post_save, sender=Question)
def sync_course_metrics_on_save(sender, instance, **kwargs):
    metrics = instance.course.question_set.aggregate(
        question_total=models.Count("id"),
        mark_total=Sum("marks"),
    )
    Course.objects.filter(id=instance.course_id).update(
        question_number=metrics["question_total"] or 0,
        total_marks=metrics["mark_total"] or 0,
    )


@receiver(post_delete, sender=Question)
def sync_course_metrics_on_delete(sender, instance, **kwargs):
    metrics = Question.objects.filter(course_id=instance.course_id).aggregate(
        question_total=models.Count("id"),
        mark_total=Sum("marks"),
    )
    Course.objects.filter(id=instance.course_id).update(
        question_number=metrics["question_total"] or 0,
        total_marks=metrics["mark_total"] or 0,
    )
