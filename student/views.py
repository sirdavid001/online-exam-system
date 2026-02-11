import random
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from exam import models as QMODEL

from . import forms, models


def _exam_session_key(course_id, field):
    return f"exam_{course_id}_{field}"


def _clear_exam_session(request, course_id):
    request.session.pop(_exam_session_key(course_id, "question_ids"), None)
    request.session.pop(_exam_session_key(course_id, "started_at"), None)


def student_signup_view(request):
    userForm = forms.StudentUserForm()
    studentForm = forms.StudentForm()

    if request.method == "POST":
        userForm = forms.StudentUserForm(request.POST)
        studentForm = forms.StudentForm(request.POST, request.FILES)
        if userForm.is_valid() and studentForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            student = studentForm.save(commit=False)
            student.user = user
            student.save()
            my_student_group = Group.objects.get_or_create(name="STUDENT")
            my_student_group[0].user_set.add(user)
            messages.success(request, "Student account created successfully.")
            return HttpResponseRedirect("studentlogin")
        messages.error(request, "Please provide valid institutional student details.")

    return render(
        request,
        "student/studentsignup.html",
        context={"userForm": userForm, "studentForm": studentForm},
    )


def is_student(user):
    return user.groups.filter(name="STUDENT").exists()


@login_required(login_url="studentlogin")
@user_passes_test(is_student, login_url="studentlogin")
def student_dashboard_view(request):
    context = {
        "total_course": QMODEL.Course.objects.all().count(),
        "total_question": QMODEL.Question.objects.all().count(),
    }
    return render(request, "student/student_dashboard.html", context=context)


@login_required(login_url="studentlogin")
@user_passes_test(is_student, login_url="studentlogin")
def student_exam_view(request):
    courses = QMODEL.Course.objects.all()
    return render(request, "student/student_exam.html", {"courses": courses})


@login_required(login_url="studentlogin")
@user_passes_test(is_student, login_url="studentlogin")
def take_exam_view(request, pk):
    course = get_object_or_404(QMODEL.Course, id=pk)
    questions = QMODEL.Question.objects.filter(course=course)
    total_questions = questions.count()
    total_marks = sum(question.marks for question in questions)

    student = get_object_or_404(models.Student, user_id=request.user.id)
    attempts_taken = QMODEL.Result.objects.filter(student=student, exam=course).count()
    remaining_attempts = max(course.max_attempts - attempts_taken, 0)

    context = {
        "course": course,
        "total_questions": total_questions,
        "total_marks": total_marks,
        "attempts_taken": attempts_taken,
        "remaining_attempts": remaining_attempts,
    }
    return render(request, "student/take_exam.html", context)


@login_required(login_url="studentlogin")
@user_passes_test(is_student, login_url="studentlogin")
def start_exam_view(request, pk):
    course = get_object_or_404(QMODEL.Course, id=pk)
    student = get_object_or_404(models.Student, user_id=request.user.id)
    attempts_taken = QMODEL.Result.objects.filter(student=student, exam=course).count()

    if attempts_taken >= course.max_attempts:
        messages.error(
            request,
            f"You have reached the maximum attempts ({course.max_attempts}) for this exam.",
        )
        return redirect("take-exam", pk=course.id)

    questions = list(QMODEL.Question.objects.filter(course=course))
    if not questions:
        messages.warning(request, "No questions are available for this course yet.")
        return redirect("student-exam")

    if course.shuffle_questions:
        random.shuffle(questions)

    question_ids = [question.id for question in questions]
    request.session[_exam_session_key(course.id, "question_ids")] = question_ids
    request.session[_exam_session_key(course.id, "started_at")] = timezone.now().isoformat()

    context = {
        "course": course,
        "questions": questions,
        "duration_seconds": course.duration_minutes * 60,
        "attempt_number": attempts_taken + 1,
    }
    return render(request, "student/start_exam.html", context)


@login_required(login_url="studentlogin")
@user_passes_test(is_student, login_url="studentlogin")
def calculate_marks_view(request):
    if request.method != "POST":
        return redirect("student-exam")

    course_id = request.POST.get("course_id")
    if not course_id:
        messages.error(request, "Invalid submission. Course was not provided.")
        return redirect("student-exam")

    course = get_object_or_404(QMODEL.Course, id=course_id)
    student = get_object_or_404(models.Student, user_id=request.user.id)

    attempts_taken = QMODEL.Result.objects.filter(student=student, exam=course).count()
    if attempts_taken >= course.max_attempts:
        messages.error(
            request,
            f"Maximum attempts reached for {course.course_name}.",
        )
        return redirect("take-exam", pk=course.id)

    session_question_ids = request.session.get(_exam_session_key(course.id, "question_ids"))
    if session_question_ids:
        questions = list(QMODEL.Question.objects.filter(course=course, id__in=session_question_ids))
    else:
        # Fallback keeps compatibility if session data is unavailable.
        questions = list(QMODEL.Question.objects.filter(course=course))

    if not questions:
        messages.error(request, "No valid exam questions found for scoring.")
        return redirect("student-exam")

    started_at_raw = request.session.get(_exam_session_key(course.id, "started_at"))
    timed_out = False
    if started_at_raw:
        try:
            started_at = timezone.datetime.fromisoformat(started_at_raw)
            if timezone.is_naive(started_at):
                started_at = timezone.make_aware(started_at, timezone.get_current_timezone())
            timed_out = timezone.now() > (started_at + timedelta(minutes=course.duration_minutes))
        except ValueError:
            timed_out = False

    raw_marks = Decimal("0.00")
    correct_answers = 0
    wrong_answers = 0
    unanswered = 0

    for question in questions:
        selected_ans = request.POST.get(f"question_{question.id}")
        if selected_ans not in {"Option1", "Option2", "Option3", "Option4"}:
            unanswered += 1
            continue

        if selected_ans == question.answer:
            correct_answers += 1
            raw_marks += Decimal(question.marks)
        else:
            wrong_answers += 1

    negative_marks = Decimal(wrong_answers) * course.negative_mark_per_wrong
    final_marks = raw_marks - negative_marks
    if final_marks < 0:
        final_marks = Decimal("0.00")

    final_marks = final_marks.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_possible_marks = sum(question.marks for question in questions)

    percentage = Decimal("0.00")
    if total_possible_marks > 0:
        percentage = (final_marks / Decimal(total_possible_marks)) * Decimal("100")
        percentage = percentage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    attempt_number = attempts_taken + 1
    passed = percentage >= Decimal(course.pass_mark)

    QMODEL.Result.objects.create(
        student=student,
        exam=course,
        attempt_number=attempt_number,
        marks=final_marks,
        total_possible_marks=total_possible_marks,
        total_questions=len(questions),
        correct_answers=correct_answers,
        wrong_answers=wrong_answers,
        unanswered=unanswered,
        percentage=percentage,
        passed=passed,
    )

    _clear_exam_session(request, course.id)

    if timed_out:
        messages.warning(request, "Exam was submitted after the official duration limit.")

    result_status = "passed" if passed else "did not pass"
    messages.success(
        request,
        (
            f"Attempt {attempt_number} submitted. Score: {final_marks}/{total_possible_marks} "
            f"({percentage}%). You {result_status}."
        ),
    )
    return redirect("check-marks", pk=course.id)


@login_required(login_url="studentlogin")
@user_passes_test(is_student, login_url="studentlogin")
def view_result_view(request):
    courses = QMODEL.Course.objects.all()
    return render(request, "student/view_result.html", {"courses": courses})


@login_required(login_url="studentlogin")
@user_passes_test(is_student, login_url="studentlogin")
def check_marks_view(request, pk):
    course = get_object_or_404(QMODEL.Course, id=pk)
    student = get_object_or_404(models.Student, user_id=request.user.id)
    results = QMODEL.Result.objects.filter(exam=course, student=student)
    return render(request, "student/check_marks.html", {"results": results, "course": course})


@login_required(login_url="studentlogin")
@user_passes_test(is_student, login_url="studentlogin")
def student_marks_view(request):
    courses = QMODEL.Course.objects.all()
    return render(request, "student/student_marks.html", {"courses": courses})
