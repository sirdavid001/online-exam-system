from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from student.models import Student

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Course(models.Model):
    course_name = models.CharField(max_length=120)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
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
    
    # Advanced V2.0 Controls
    shuffle_questions = models.BooleanField(default=True)
    shuffle_options = models.BooleanField(default=True)
    enable_proctoring = models.BooleanField(default=False)
    allow_navigation = models.BooleanField(default=True, help_text="Allow students to go back to previous questions")
    show_explanation_after_exam = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    
    instructions = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

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

    TYPE_CHOICES = (
        ("MCQ", "Multiple Choice Question"),
        ("TRUE_FALSE", "True/False"),
        ("SHORT_ANSWER", "Short Answer"),
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    question_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="MCQ",
    )
    marks = models.PositiveIntegerField(default=1)
    question_text = models.TextField()
    
    # MCQ Options
    option1 = models.CharField(max_length=500, blank=True, null=True)
    option2 = models.CharField(max_length=500, blank=True, null=True)
    option3 = models.CharField(max_length=500, blank=True, null=True)
    option4 = models.CharField(max_length=500, blank=True, null=True)
    
    answer = models.CharField(max_length=500, help_text="Correct option number (e.g. 1) or text for Short Answer")
    explanation = models.TextField(blank=True, default="")
    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default="INTERMEDIATE",
    )
    image = models.ImageField(upload_to="questions/", blank=True, null=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.course.course_name} - {self.question_text[:50]}"

class ExamSession(models.Model):
    """V2.0: Persistent state for ongoing exams"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField()
    is_completed = models.BooleanField(default=False)
    current_question_index = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ('student', 'course', 'is_completed')

    def save(self, *args, **kwargs):
        if not self.end_time:
            self.end_time = timezone.now() + timezone.timedelta(minutes=self.course.duration_minutes)
        super().save(*args, **kwargs)

class StudentAnswer(models.Model):
    """V2.0: Database-level persistence for answers"""
    session = models.ForeignKey(ExamSession, related_name="answers", on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=500, blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now=True)

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
    
    # Proctoring feedback
    tab_switches = models.PositiveIntegerField(default=0)
    suspicious_activity_count = models.PositiveIntegerField(default=0)
    
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
    instance.course.refresh_assessment_totals()

@receiver(post_delete, sender=Question)
def sync_course_metrics_on_delete(sender, instance, **kwargs):
    instance.course.refresh_assessment_totals()
