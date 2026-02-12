from decimal import Decimal

from django.contrib.auth.models import AnonymousUser, Group, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse

from exam.models import Course, InstitutionSettings, Question, Result
from student.forms import StudentForm
from student.models import Student
from student import views as SVIEWS


class StudentProfileValidationTests(TestCase):
    def test_student_form_rejects_non_edu_ng_email(self):
        form = StudentForm(
            data={
                "matric_number": "UNN/2025/12345",
                "institutional_email": "student@gmail.com",
                "faculty": "Faculty of Computing",
                "department": "Computer Science",
                "programme": "B.Sc Computer Science",
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
                "faculty": "Faculty of Computing",
                "department": "Computer Science",
                "programme": "B.Sc Computer Science",
                "current_level": "200",
                "entry_year": 2024,
                "mobile": "08031234567",
                "address": "Nsukka Campus",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Matric/reg number must include digits.", form.errors["matric_number"])

    def test_student_form_rejects_department_not_in_selected_faculty(self):
        form = StudentForm(
            data={
                "matric_number": "DOU/2026/10001",
                "institutional_email": "student@dou.edu.ng",
                "faculty": "Faculty of Agriculture",
                "department": "Computer Science",
                "programme": "B.Sc Crop Science",
                "current_level": "100",
                "entry_year": 2026,
                "mobile": "08031234567",
                "address": "Asaba Campus",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Select a department that matches the selected faculty.",
            form.errors["department"],
        )


class StudentIdentifierLoginTests(TestCase):
    def setUp(self):
        self.password = "pass12345"
        self.user = User.objects.create_user(
            username="identifier_student",
            password=self.password,
        )
        Student.objects.create(
            user=self.user,
            matric_number="DOU/2026/00001",
            institutional_email="identifier.student@dou.edu.ng",
            faculty="Faculty of Science",
            department="Computer Science",
            programme="B.Sc Computer Science",
            current_level="JUPEB",
            entry_year=2026,
            address="Asaba Campus",
            mobile="08031234567",
        )
        student_group, _ = Group.objects.get_or_create(name="STUDENT")
        student_group.user_set.add(self.user)

    def test_student_can_login_with_matric_number(self):
        response = self.client.post(
            reverse("studentlogin"),
            {"username": "DOU/2026/00001", "password": self.password},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get("_auth_user_id"), str(self.user.id))

    def test_student_can_login_with_institutional_email(self):
        response = self.client.post(
            reverse("studentlogin"),
            {"username": "identifier.student@dou.edu.ng", "password": self.password},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get("_auth_user_id"), str(self.user.id))


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


class StudentSignupConsentTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _valid_signup_payload(self):
        return {
            "first_name": "Ada",
            "last_name": "Okafor",
            "username": "ada_policy_student",
            "password": "pass12345",
            "matric_number": "UNN/2026/10002",
            "institutional_email": "ada.okafor@unn.edu.ng",
            "faculty": "Faculty of Computing",
            "department": "Computer Science",
            "programme": "B.Sc Computer Science",
            "current_level": "300",
            "entry_year": 2024,
            "mobile": "08031234567",
            "address": "Nsukka Campus",
        }

    def _post_signup(self, payload):
        request = self.factory.post(reverse("studentsignup"), data=payload)
        request.user = AnonymousUser()

        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        request.session.save()
        setattr(request, "_messages", FallbackStorage(request))

        return SVIEWS.student_signup_view(request)

    def test_student_signup_requires_policy_acceptance(self):
        response = self._post_signup(self._valid_signup_payload())
        html = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("You must accept the Terms of Use and Privacy Policy to continue.", html)
        self.assertFalse(User.objects.filter(username="ada_policy_student").exists())

    def test_student_signup_succeeds_when_policy_is_accepted(self):
        payload = self._valid_signup_payload()
        payload["username"] = "ada_policy_student_ok"
        payload["matric_number"] = "UNN/2026/10003"
        payload["institutional_email"] = "ada.policy.ok@unn.edu.ng"
        payload["accept_policies"] = "on"

        response = self._post_signup(payload)

        self.assertEqual(response.status_code, 302)
        self.assertIn("studentlogin", response["Location"])
        self.assertTrue(User.objects.filter(username="ada_policy_student_ok").exists())
        self.assertTrue(Student.objects.filter(matric_number="UNN/2026/10003").exists())

    def test_student_signup_is_blocked_when_admin_disables_self_signup(self):
        InstitutionSettings.objects.create(
            institution_name="Dennis Osadebay University",
            short_name="DOU",
            current_session="2026/2027",
            current_semester="FIRST",
            allow_student_signup=False,
            allow_teacher_signup=True,
        )
        payload = self._valid_signup_payload()
        payload["accept_policies"] = "on"

        response = self._post_signup(payload)

        self.assertEqual(response.status_code, 302)
        self.assertIn("studentlogin", response["Location"])
        self.assertFalse(User.objects.filter(username="ada_policy_student").exists())
