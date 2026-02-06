from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from exam.models import Course, Question, Result
from student.forms import StudentForm
from student.models import Student


class StudentProfileValidationTests(TestCase):
    def test_student_form_rejects_non_edu_ng_email(self):
        form = StudentForm(
            data={
                "matric_number": "UNN/2025/12345",
                "institutional_email": "student@gmail.com",
                "faculty": "Faculty of Engineering",
                "department": "Mechanical Engineering",
                "programme": "B.Eng Mechanical Engineering",
                "current_level": "200",
                "entry_year": 2024,
                "mobile": "08031234567",
                "address": "Nsukka Campus",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Use an institutional email ending with .edu.ng.", form.errors["institutional_email"])

    def test_student_form_rejects_invalid_matric_number(self):
        form = StudentForm(
            data={
                "matric_number": "INVALID",
                "institutional_email": "student@unn.edu.ng",
                "faculty": "Faculty of Engineering",
                "department": "Mechanical Engineering",
                "programme": "B.Eng Mechanical Engineering",
                "current_level": "200",
                "entry_year": 2024,
                "mobile": "08031234567",
                "address": "Nsukka Campus",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Matric/reg number must include digits.", form.errors["matric_number"])


class ExamScoringTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student_scorer",
            password="pass12345",
        )
        self.student = Student.objects.create(
            user=self.user,
            matric_number="UNN/2025/00001",
            institutional_email="student_scorer@unn.edu.ng",
            faculty="Faculty of Science",
            department="Mathematics",
            programme="B.Sc Mathematics",
            current_level="300",
            entry_year=2023,
            address="Test Address",
            mobile="08031234567",
        )
        student_group, _ = Group.objects.get_or_create(name="STUDENT")
        student_group.user_set.add(self.user)

        self.course = Course.objects.create(
            course_name="Mathematics",
            duration_minutes=60,
            pass_mark=50,
            max_attempts=3,
            negative_mark_per_wrong=Decimal("1.25"),
        )
        self.question_1 = Question.objects.create(
            course=self.course,
            marks=10,
            question="2 + 2 = ?",
            option1="4",
            option2="5",
            option3="6",
            option4="7",
            answer="Option1",
        )
        self.question_2 = Question.objects.create(
            course=self.course,
            marks=5,
            question="3 + 2 = ?",
            option1="4",
            option2="5",
            option3="6",
            option4="7",
            answer="Option2",
        )

    def test_calculate_marks_creates_attempt_with_analytics(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("calculate-marks"),
            {
                "course_id": str(self.course.id),
                f"question_{self.question_1.id}": "Option1",
                f"question_{self.question_2.id}": "Option4",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("check-marks", args=[self.course.id]))

        result = Result.objects.get(student=self.student, exam=self.course, attempt_number=1)
        self.assertEqual(result.correct_answers, 1)
        self.assertEqual(result.wrong_answers, 1)
        self.assertEqual(result.unanswered, 0)
        self.assertEqual(result.total_questions, 2)
        self.assertEqual(result.total_possible_marks, 15)
        self.assertEqual(result.marks, Decimal("8.75"))

    def test_calculate_marks_creates_new_result_for_each_attempt(self):
        self.client.force_login(self.user)

        self.client.post(
            reverse("calculate-marks"),
            {
                "course_id": str(self.course.id),
                f"question_{self.question_1.id}": "Option1",
                f"question_{self.question_2.id}": "Option4",
            },
        )

        self.client.post(
            reverse("calculate-marks"),
            {
                "course_id": str(self.course.id),
                f"question_{self.question_1.id}": "Option1",
                f"question_{self.question_2.id}": "Option2",
            },
        )

        results = Result.objects.filter(student=self.student, exam=self.course).order_by("attempt_number")
        self.assertEqual(results.count(), 2)
        self.assertEqual(results[0].attempt_number, 1)
        self.assertEqual(results[1].attempt_number, 2)
        self.assertEqual(results[1].marks, Decimal("15.00"))

    def test_calculate_marks_blocks_when_max_attempts_reached(self):
        self.client.force_login(self.user)
        self.course.max_attempts = 1
        self.course.save(update_fields=["max_attempts"])

        self.client.post(
            reverse("calculate-marks"),
            {
                "course_id": str(self.course.id),
                f"question_{self.question_1.id}": "Option1",
                f"question_{self.question_2.id}": "Option2",
            },
        )

        response = self.client.post(
            reverse("calculate-marks"),
            {
                "course_id": str(self.course.id),
                f"question_{self.question_1.id}": "Option1",
                f"question_{self.question_2.id}": "Option2",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("take-exam", args=[self.course.id]))
        self.assertEqual(Result.objects.filter(student=self.student, exam=self.course).count(), 1)

    def test_calculate_marks_get_redirects_back_to_exam_list(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("calculate-marks"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("student-exam"))
