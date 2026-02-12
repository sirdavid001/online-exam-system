from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from student.models import Student
from teacher.models import Teacher


class MultiIdentifierBackend(ModelBackend):
    """
    Authenticate users with institution-relevant identifiers.

    Supported identifiers:
    - Username (all roles)
    - Student matric/reg number or institutional email
    - Teacher staff ID or official email
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        identifier = (username or kwargs.get(user_model.USERNAME_FIELD) or "").strip()
        if not identifier or password is None:
            return None

        user = user_model.objects.filter(username__iexact=identifier).first()

        if user is None:
            student = Student.objects.select_related("user").filter(
                Q(matric_number__iexact=identifier) | Q(institutional_email__iexact=identifier)
            ).first()
            if student is not None:
                user = student.user

        if user is None:
            teacher = Teacher.objects.select_related("user").filter(
                Q(staff_id__iexact=identifier) | Q(official_email__iexact=identifier)
            ).first()
            if teacher is not None:
                user = teacher.user

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
