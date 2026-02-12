from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.db.models import Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from student.models import Student


class Course(models.Model):
    LEVEL_CHOICES = (
        ("JUPEB", "JUPEB"),
        ("100", "100 Level"),
        ("200", "200 Level"),
        ("300", "300 Level"),
        ("400", "400 Level"),
        ("500", "500 Level"),
        ("600", "600 Level"),
        ("PG", "Postgraduate"),
    )

    SEMESTER_CHOICES = (
        ("FIRST", "First Semester"),
        ("SECOND", "Second Semester"),
        ("SUMMER", "Summer Semester"),
    )

    course_name = models.CharField(max_length=120)
    course_code = models.CharField(max_length=30, blank=True, default="")
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default="100")
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, default="FIRST")
    academic_session = models.CharField(max_length=20, blank=True, default="")
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
    is_published = models.BooleanField(default=True)
    available_from = models.DateTimeField(null=True, blank=True)
    available_until = models.DateTimeField(null=True, blank=True)
    instructions = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["course_name"]

    def __str__(self):
        if self.course_code:
            return f"{self.course_code} - {self.course_name}"
        return self.course_name

    def is_available_now(self, at=None):
        at = at or timezone.now()
        if not self.is_published:
            return False
        if self.available_from and at < self.available_from:
            return False
        if self.available_until and at > self.available_until:
            return False
        return True

    def refresh_assessment_totals(self):
        metrics = self.question_set.aggregate(
            question_total=models.Count("id"),
            mark_total=Sum("marks"),
        )
        self.question_number = metrics["question_total"] or 0
        self.total_marks = metrics["mark_total"] or 0
        self.save(update_fields=["question_number", "total_marks"])


class InstitutionSettings(models.Model):
    institution_name = models.CharField(max_length=160, default="Dennis Osadebay University")
    short_name = models.CharField(max_length=40, default="DOU")
    official_website = models.URLField(blank=True, default="")
    support_email = models.EmailField(blank=True, default="")
    support_phone = models.CharField(max_length=30, blank=True, default="")
    address = models.CharField(max_length=220, blank=True, default="")
    current_session = models.CharField(max_length=20, default="2026/2027")
    current_semester = models.CharField(max_length=10, choices=Course.SEMESTER_CHOICES, default="FIRST")
    allow_student_signup = models.BooleanField(default=True)
    allow_teacher_signup = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Institution Settings"
        verbose_name_plural = "Institution Settings"

    def __str__(self):
        return f"{self.institution_name} Settings"


class AdminAnnouncement(models.Model):
    AUDIENCE_ALL = "ALL"
    AUDIENCE_STUDENT = "STUDENT"
    AUDIENCE_TEACHER = "TEACHER"
    AUDIENCE_CHOICES = (
        (AUDIENCE_ALL, "All Users"),
        (AUDIENCE_STUDENT, "Students"),
        (AUDIENCE_TEACHER, "Teachers"),
    )

    title = models.CharField(max_length=180)
    message = models.TextField()
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default=AUDIENCE_ALL)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @classmethod
    def active_for(cls, audience, at=None):
        at = at or timezone.now()
        return cls.objects.filter(
            is_active=True,
            audience__in=[cls.AUDIENCE_ALL, audience],
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=at),
            Q(ends_at__isnull=True) | Q(ends_at__gte=at),
        )


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
