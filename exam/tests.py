from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from exam.models import Course, Question, Result
from student.models import Student
from teacher.models import Teacher


class AdminPermissionTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin_user",
            password="pass12345",
            is_staff=True,
        )
        self.student_user = User.objects.create_user(
            username="student_user",
            password="pass12345",
        )
        student_group, _ = Group.objects.get_or_create(name="STUDENT")
        student_group.user_set.add(self.student_user)

    def test_admin_dashboard_redirects_anonymous_users_to_admin_login(self):
        response = self.client.get(reverse("admin-dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("adminlogin"), response.url)

    def test_admin_dashboard_blocks_non_admin_authenticated_users(self):
        self.client.force_login(self.student_user)

        response = self.client.get(reverse("admin-dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("adminlogin"), response.url)

    def test_afterlogin_routes_staff_user_to_admin_dashboard(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("afterlogin"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("admin-dashboard"))


class AdminExportTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin_export",
            password="pass12345",
            is_staff=True,
        )

        self.student_user = User.objects.create_user(
            username="scoring_student",
            first_name="Ada",
            last_name="Okeke",
            password="pass12345",
        )
        self.student = Student.objects.create(
            user=self.student_user,
            matric_number="UNN/2025/10001",
            institutional_email="ada.okeke@unn.edu.ng",
            faculty="Faculty of Engineering",
            department="Computer Engineering",
            programme="B.Eng Computer Engineering",
            current_level="300",
            entry_year=2023,
            mobile="08031234567",
            address="Nsukka Campus",
        )

        self.teacher_user = User.objects.create_user(
            username="lecturer_export",
            first_name="Chinedu",
            last_name="Ifeanyi",
            password="pass12345",
        )
        Teacher.objects.create(
            user=self.teacher_user,
            staff_id="UNN/CPE/2025/007",
            official_email="chinedu.ifeanyi@unn.edu.ng",
            faculty="Faculty of Engineering",
            department="Computer Engineering",
            designation="LECTURER_I",
            mobile="08032223344",
            address="Engineering Block B",
            status=True,
        )

        self.course = Course.objects.create(
            course_name="Algorithms",
            question_number=10,
            total_marks=50,
            duration_minutes=60,
            pass_mark=50,
            max_attempts=3,
            negative_mark_per_wrong=Decimal("1.00"),
            shuffle_questions=True,
        )

        Result.objects.create(
            student=self.student,
            exam=self.course,
            attempt_number=1,
            marks=Decimal("42.00"),
            total_possible_marks=50,
            total_questions=10,
            correct_answers=8,
            wrong_answers=2,
            unanswered=0,
            percentage=Decimal("84.00"),
            passed=True,
        )

    def test_non_admin_is_redirected_from_export_endpoint(self):
        self.client.force_login(self.student_user)

        response = self.client.get(reverse("admin-export-results-csv"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("adminlogin"), response.url)

    def test_admin_can_export_results_csv(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-export-results-csv"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn('attachment; filename="exam_results_', response["Content-Disposition"])

        content = response.content.decode("utf-8")
        self.assertIn("Student Name,Matric Number,Exam,Attempt,Score", content)
        self.assertIn("Ada Okeke", content)
        self.assertIn("UNN/2025/10001", content)
        self.assertIn("Algorithms", content)

    def test_admin_can_export_results_excel_tsv(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin-export-results-excel"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/vnd.ms-excel", response["Content-Type"])
        self.assertIn('attachment; filename="exam_results_', response["Content-Disposition"])

        content = response.content.decode("utf-8")
        self.assertIn("Student Name\tMatric Number\tExam", content)
        self.assertIn("Ada Okeke", content)

    def test_admin_can_export_students_teachers_and_courses_csv(self):
        self.client.force_login(self.admin_user)

        students_response = self.client.get(reverse("admin-export-students-csv"))
        teachers_response = self.client.get(reverse("admin-export-teachers-csv"))
        courses_response = self.client.get(reverse("admin-export-courses-csv"))

        self.assertEqual(students_response.status_code, 200)
        self.assertEqual(teachers_response.status_code, 200)
        self.assertEqual(courses_response.status_code, 200)

        students_content = students_response.content.decode("utf-8")
        teachers_content = teachers_response.content.decode("utf-8")
        courses_content = courses_response.content.decode("utf-8")

        self.assertIn("Name,Matric Number,Institutional Email", students_content)
        self.assertIn("UNN/2025/10001", students_content)

        self.assertIn("Name,Staff ID,Official Email", teachers_content)
        self.assertIn("UNN/CPE/2025/007", teachers_content)

        self.assertIn("Course,Questions,Total Marks,Duration Minutes", courses_content)
        self.assertIn("Algorithms", courses_content)


class AdminManagementTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin_manager",
            password="pass12345",
            is_staff=True,
        )

        self.student_user = User.objects.create_user(
            username="normal_user",
            first_name="Ifeoma",
            last_name="Nwosu",
            password="pass12345",
        )
        self.student = Student.objects.create(
            user=self.student_user,
            matric_number="UNILAG/2025/11111",
            institutional_email="ifeoma.nwosu@unilag.edu.ng",
            faculty="Faculty of Science",
            department="Computer Science",
            programme="B.Sc Computer Science",
            current_level="400",
            entry_year=2022,
            mobile="08035556677",
            address="Akoka Campus",
        )
        student_group, _ = Group.objects.get_or_create(name="STUDENT")
        student_group.user_set.add(self.student_user)

        self.course = Course.objects.create(
            course_name="Database Systems",
            duration_minutes=90,
            pass_mark=50,
            max_attempts=3,
            negative_mark_per_wrong=Decimal("0.50"),
            shuffle_questions=True,
            instructions="Answer all questions.",
        )
        self.alt_course = Course.objects.create(
            course_name="Data Structures",
            duration_minutes=60,
            pass_mark=50,
            max_attempts=2,
            negative_mark_per_wrong=Decimal("0.25"),
            shuffle_questions=True,
            instructions="Attempt carefully.",
        )

        self.question = Question.objects.create(
            course=self.course,
            marks=5,
            question="Which data model is used in relational databases?",
            option1="Network",
            option2="Relational",
            option3="Hierarchical",
            option4="Object",
            answer="Option2",
            difficulty="INTERMEDIATE",
            explanation="Relational databases use tables and relations.",
        )

        self.result = Result.objects.create(
            student=self.student,
            exam=self.course,
            attempt_number=1,
            marks=Decimal("35.00"),
            total_possible_marks=50,
            total_questions=10,
            correct_answers=7,
            wrong_answers=3,
            unanswered=0,
            percentage=Decimal("70.00"),
            passed=True,
        )

    def test_admin_results_page_requires_admin(self):
        self.client.force_login(self.student_user)

        response = self.client.get(reverse("admin-results"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("adminlogin"), response.url)

    def test_admin_can_update_course_from_admin_page(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("update-course", args=[self.course.id]),
            {
                "course_name": "Database Systems II",
                "duration_minutes": 120,
                "pass_mark": 60,
                "max_attempts": 4,
                "negative_mark_per_wrong": "0.75",
                "shuffle_questions": "on",
                "instructions": "Revised instructions",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("admin-view-course"))

        self.course.refresh_from_db()
        self.assertEqual(self.course.course_name, "Database Systems II")
        self.assertEqual(self.course.duration_minutes, 120)
        self.assertEqual(self.course.pass_mark, 60)
        self.assertEqual(self.course.max_attempts, 4)
        self.assertEqual(self.course.negative_mark_per_wrong, Decimal("0.75"))

    def test_admin_can_update_question_and_change_course(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("update-question", args=[self.question.id]),
            {
                "courseID": self.alt_course.id,
                "marks": 6,
                "question": "Which structure is LIFO?",
                "option1": "Queue",
                "option2": "Stack",
                "option3": "Array",
                "option4": "Tree",
                "answer": "Option2",
                "difficulty": "BEGINNER",
                "explanation": "Stack follows Last In First Out.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("view-question", args=[self.alt_course.id]))

        self.question.refresh_from_db()
        self.assertEqual(self.question.course_id, self.alt_course.id)
        self.assertEqual(self.question.marks, 6)
        self.assertEqual(self.question.difficulty, "BEGINNER")

    def test_admin_can_delete_attempt_from_results_manager(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("delete-result", args=[self.result.id]),
            {"next": reverse("admin-results")},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("admin-results"))
        self.assertEqual(Result.objects.count(), 0)
