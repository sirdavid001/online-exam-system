from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models

nigerian_phone_validator = RegexValidator(
    regex=r"^(\+234|0)[789][01]\d{8}$",
    message="Enter a valid Nigerian phone number (e.g. 08031234567 or +2348031234567).",
)

class Teacher(models.Model):
    DESIGNATION_CHOICES = (
        ("GRADUATE_ASSISTANT", "Graduate Assistant"),
        ("ASSISTANT_LECTURER", "Assistant Lecturer"),
        ("LECTURER_II", "Lecturer II"),
        ("LECTURER_I", "Lecturer I"),
        ("SENIOR_LECTURER", "Senior Lecturer"),
        ("ASSOCIATE_PROFESSOR", "Associate Professor"),
        ("PROFESSOR", "Professor"),
        ("ADJUNCT", "Adjunct Lecturer"),
    )

    VERIFICATION_STATUS = (
        ("PENDING", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    staff_id = models.CharField(max_length=40, unique=True, null=True, blank=True)
    official_email = models.EmailField(unique=True, null=True, blank=True)
    faculty = models.CharField(max_length=120, null=True, blank=True)
    department = models.CharField(max_length=120, null=True, blank=True)
    designation = models.CharField(
        max_length=30,
        choices=DESIGNATION_CHOICES,
        default="LECTURER_II",
    )

    bio = models.TextField(max_length=500, blank=True)
    profile_pic = models.ImageField(upload_to="profile_pic/Teacher/", null=True, blank=True)
    address = models.CharField(max_length=160, blank=True)
    mobile = models.CharField(max_length=20, validators=[nigerian_phone_validator], null=False)
    
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default="PENDING")
    status = models.BooleanField(default=False, help_text="Active/Inactive status")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def get_name(self):
        return f"{self.user.first_name} {self.user.last_name}"

    def __str__(self):
        return f"{self.user.username} ({self.staff_id})"
