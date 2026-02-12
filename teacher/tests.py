from django.contrib.auth.models import AnonymousUser, Group, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import reverse

from exam.models import Course, InstitutionSettings, Question
from teacher.forms import TeacherForm
from teacher.models import Teacher
from teacher import views as TVIEWS


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
                "faculty": "Faculty of Computing",
                "department": "Computer Science",
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

    def test_teacher_form_rejects_department_not_in_selected_faculty(self):
        form = TeacherForm(
            data={
                "staff_id": "DOU/COM/2026/010",
                "official_email": "ada.okafor@dou.edu.ng",
                "faculty": "Faculty of Agriculture",
                "department": "Computer Science",
                "designation": "LECTURER_I",
                "mobile": "08031234567",
                "address": "Room 5, Main Campus",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Select a department that matches the selected faculty.",
            form.errors["department"],
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


class TeacherIdentifierLoginTests(TestCase):
    def setUp(self):
        self.password = "pass12345"
        self.user = User.objects.create_user(
            username="identifier_teacher",
            password=self.password,
        )
        Teacher.objects.create(
            user=self.user,
            staff_id="DOU/CSE/2026/021",
            official_email="identifier.teacher@dou.edu.ng",
            faculty="Faculty of Science",
            department="Computer Science",
            designation="LECTURER_II",
            address="Room 103, ICT Block",
            mobile="08031234567",
            status=True,
        )
        teacher_group, _ = Group.objects.get_or_create(name="TEACHER")
        teacher_group.user_set.add(self.user)

    def test_teacher_can_login_with_staff_id(self):
        response = self.client.post(
            reverse("teacherlogin"),
            {"username": "DOU/CSE/2026/021", "password": self.password},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get("_auth_user_id"), str(self.user.id))

    def test_teacher_can_login_with_official_email(self):
        response = self.client.post(
            reverse("teacherlogin"),
            {"username": "identifier.teacher@dou.edu.ng", "password": self.password},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get("_auth_user_id"), str(self.user.id))


class TeacherSignupConsentTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _valid_signup_payload(self):
        return {
            "first_name": "Chinedu",
            "last_name": "Eze",
            "username": "chinedu_policy_teacher",
            "password": "pass12345",
            "staff_id": "UNN/CSE/2026/014",
            "official_email": "chinedu.eze@unn.edu.ng",
            "faculty": "Faculty of Computing",
            "department": "Computer Science",
            "designation": "LECTURER_II",
            "mobile": "08039876543",
            "address": "Room 212, ICT Building",
        }

    def _post_signup(self, payload):
        request = self.factory.post(reverse("teachersignup"), data=payload)
        request.user = AnonymousUser()

        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        request.session.save()
        setattr(request, "_messages", FallbackStorage(request))

        return TVIEWS.teacher_signup_view(request)

    def test_teacher_signup_requires_policy_acceptance(self):
        response = self._post_signup(self._valid_signup_payload())
        html = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("You must accept the Terms of Use and Privacy Policy to continue.", html)
        self.assertFalse(User.objects.filter(username="chinedu_policy_teacher").exists())

    def test_teacher_signup_succeeds_when_policy_is_accepted(self):
        payload = self._valid_signup_payload()
        payload["username"] = "chinedu_policy_teacher_ok"
        payload["staff_id"] = "UNN/CSE/2026/015"
        payload["official_email"] = "chinedu.policy.ok@unn.edu.ng"
        payload["accept_policies"] = "on"

        response = self._post_signup(payload)

        self.assertEqual(response.status_code, 302)
        self.assertIn("teacherlogin", response["Location"])
        self.assertTrue(User.objects.filter(username="chinedu_policy_teacher_ok").exists())
        self.assertTrue(Teacher.objects.filter(staff_id="UNN/CSE/2026/015").exists())

    def test_teacher_signup_is_blocked_when_admin_disables_self_signup(self):
        InstitutionSettings.objects.create(
            institution_name="Dennis Osadebay University",
            short_name="DOU",
            current_session="2026/2027",
            current_semester="FIRST",
            allow_student_signup=True,
            allow_teacher_signup=False,
        )
        payload = self._valid_signup_payload()
        payload["accept_policies"] = "on"

        response = self._post_signup(payload)

        self.assertEqual(response.status_code, 302)
        self.assertIn("teacherlogin", response["Location"])
        self.assertFalse(User.objects.filter(username="chinedu_policy_teacher").exists())
