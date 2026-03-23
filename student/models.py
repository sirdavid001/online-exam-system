from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

nigerian_phone_validator = RegexValidator(
    regex=r"^(\+234|0)[789][01]\d{8}$",
    message="Enter a valid Nigerian phone number (e.g. 08031234567 or +2348031234567).",
)

class Student(models.Model):
    LEVEL_CHOICES = (
        ("100", "100 Level"),
        ("200", "200 Level"),
        ("300", "300 Level"),
        ("400", "400 Level"),
        ("500", "500 Level"),
        ("600", "600 Level"),
        ("PG", "Postgraduate"),
    )

    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("GRADUATED", "Graduated"),
        ("SUSPENDED", "Suspended"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    matric_number = models.CharField(max_length=40, unique=True, null=True, blank=True)
    institutional_email = models.EmailField(unique=True, null=True, blank=True)
    faculty = models.CharField(max_length=120, null=True, blank=True)
    department = models.CharField(max_length=120, null=True, blank=True)
    programme = models.CharField(max_length=120, null=True, blank=True)
    current_level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default="100")
    entry_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1990), MaxValueValidator(2100)],
    )
    
    registration_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    bio = models.TextField(max_length=500, blank=True)
    profile_pic = models.ImageField(upload_to="profile_pic/Student/", null=True, blank=True)
    address = models.CharField(max_length=160, blank=True)
    mobile = models.CharField(max_length=20, validators=[nigerian_phone_validator], null=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def get_name(self):
        return f"{self.user.first_name} {self.user.last_name}"

    def __str__(self):
        return f"{self.user.username} ({self.matric_number})"
