from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from exam.models import Course, Question
from teacher.forms import TeacherForm
from teacher.models import Teacher


class TeacherPermissionTests(TestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user(
            username="teacher_user",
            password="pass12345",
        )
        self.student_user = User.objects.create_user(
            username="student_user_for_teacher_test",
            password="pass12345",
        )

        teacher_group, _ = Group.objects.get_or_create(name="TEACHER")
        student_group, _ = Group.objects.get_or_create(name="STUDENT")
        teacher_group.user_set.add(self.teacher_user)
        student_group.user_set.add(self.student_user)

    def test_teacher_question_requires_teacher_group(self):
        self.client.force_login(self.student_user)

        response = self.client.get(reverse("teacher-question"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("teacherlogin"), response.url)

    def test_afterlogin_routes_approved_teacher_to_teacher_dashboard(self):
        Teacher.objects.create(
            user=self.teacher_user,
            staff_id="UNILAG/CSE/2025/001",
            official_email="teacher_user@unilag.edu.ng",
            faculty="Faculty of Science",
            department="Computer Science",
            designation="LECTURER_II",
            address="Room 101, ICT Block",
            mobile="08031234567",
            status=True,
        )
        self.client.force_login(self.teacher_user)

        response = self.client.get(reverse("afterlogin"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("teacher-dashboard"))

    def test_teacher_form_requires_official_university_email_domain(self):
        form = TeacherForm(
            data={
                "staff_id": "UNN/EEE/2025/010",
                "official_email": "ada.okafor@gmail.com",
                "faculty": "Engineering",
                "department": "Electrical Engineering",
                "designation": "LECTURER_I",
                "mobile": "08031234567",
                "address": "Room 5, Engineering Complex",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Use an official university email ending with .edu.ng.",
            form.errors["official_email"],
        )

    def test_teacher_can_bulk_upload_questions_from_csv(self):
        self.client.force_login(self.teacher_user)

        course = Course.objects.create(course_name="Physics 101")
        csv_content = (
            "question,marks,option1,option2,option3,option4,answer,difficulty,explanation\n"
            "What is 2+2?,5,4,5,6,7,A,Beginner,Basic arithmetic\n"
            "Solve \\(x^2=4\\),5,1,2,3,4,2,Intermediate,Use square roots\n"
        )
        upload = SimpleUploadedFile(
            "questions.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("teacher-upload-questions"),
            {
                "courseID": course.id,
                "questions_file": upload,
                "has_header": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("teacher-upload-questions"))
        self.assertEqual(Question.objects.filter(course=course).count(), 2)

        first = Question.objects.filter(course=course).order_by("id").first()
        self.assertEqual(first.answer, "Option1")
