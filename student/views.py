import json
import random
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from exam import models as QMODEL

from . import forms, models


def is_student(user):
    return user.groups.filter(name="STUDENT").exists()


@login_required(login_url="studentlogin")
@user_passes_test(is_student, login_url="studentlogin")
def ajax_save_answer_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            course_id = data.get("course_id")
            question_id = data.get("question_id")
            selected_ans = data.get("option")

            if course_id and question_id:
                session_key = _exam_session_key(course_id, "saved_answers")
                saved_answers = request.session.get(session_key, {})
                saved_answers[str(question_id)] = selected_ans
                request.session[session_key] = saved_answers
                request.session.modified = True
                return JsonResponse({"status": "success"})
            return JsonResponse({"status": "error", "message": "Missing course_id or question_id"}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


# for showing signup/login button for student

def studentclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect("afterlogin")
    return render(request, "student/studentclick.html")


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


def _exam_session_key(course_id, field):
    return f"exam_{course_id}_{field}"


def _clear_exam_session(request, course_id):
    request.session.pop(_exam_session_key(course_id, "question_ids"), None)
    request.session.pop(_exam_session_key(course_id, "started_at"), None)
    request.session.pop(_exam_session_key(course_id, "saved_answers"), None)




@login_required(login_url="studentlogin")
@user_passes_test(is_student, login_url="studentlogin")
def student_dashboard_view(request):
    student = get_object_or_404(models.Student, user_id=request.user.id)
    recent_results = QMODEL.Result.objects.filter(student=student).order_by("-date")[:10]

    # Prepare data for performance chart (ordered by date ascending for the chart)
    perf_results = list(reversed(recent_results))
    chart_labels = [r.exam.course_name for r in perf_results]
    chart_data = [float(r.percentage) for r in perf_results]

    # Calculate average performance for the new tile
    all_results = QMODEL.Result.objects.filter(student=student)
    avg_perf = 0
    if all_results.exists():
        avg_perf = sum(r.percentage for r in all_results) / all_results.count()
        avg_perf = float(avg_perf.quantize(Decimal("0.1")))

    context = {
        "total_course": QMODEL.Course.objects.filter(is_published=True).count(),
        "total_question": QMODEL.Question.objects.filter(course__is_published=True).count(),
        "recent_results": recent_results,
        "performance_data": json.dumps({"labels": chart_labels, "series": chart_data}),
        "performance_data_avg": avg_perf,
    }
    return render(request, "student/student_dashboard.html", context=context)


@login_required(login_url="studentlogin")
@user_passes_test(is_student, login_url="studentlogin")
def student_exam_view(request):
    courses = QMODEL.Course.objects.filter(is_published=True)
    return render(request, "student/student_exam.html", {"courses": courses})

@login_required(login_url="studentlogin")
@user_passes_test(is_student, login_url="studentlogin")
def take_exam_view(request, pk):
    """V2.0 Entrance: Shows exam instructions and attempt status"""
    course = get_object_or_404(QMODEL.Course, id=pk)
    student = get_object_or_404(models.Student, user_id=request.user.id)
    
    attempts_taken = QMODEL.Result.objects.filter(student=student, exam=course).count()
    remaining_attempts = max(course.max_attempts - attempts_taken, 0)
    
    # Check for active session
    active_session = QMODEL.ExamSession.objects.filter(
        student=student, course=course, is_completed=False
    ).first()

    context = {
        "course": course,
        "attempts_taken": attempts_taken,
        "remaining_attempts": remaining_attempts,
        "active_session": active_session,
    }
    return render(request, "student/take_exam.html", context)

@login_required(login_url="studentlogin")
@user_passes_test(is_student, login_url="studentlogin")
def start_exam_view(request, pk):
    """V2.0 Start/Resume: Redirects to the HTMX Engine"""
    from exam.views import take_exam_view as v2_engine
    return v2_engine(request, pk)

@login_required(login_url="studentlogin")
@user_passes_test(is_student, login_url="studentlogin")
def calculate_marks_view(request, pk=None):
    """V2.0 Grading: Processes ExamSession data into Result"""
    course_id = pk or request.POST.get("course_id")
    course = get_object_or_404(QMODEL.Course, id=course_id)
    student = get_object_or_404(models.Student, user_id=request.user.id)
    
    session = get_object_or_404(QMODEL.ExamSession, student=student, course=course, is_completed=False)
    
    # Logic to aggregate StudentAnswer instances into a Result
    answers = QMODEL.StudentAnswer.objects.filter(session=session)
    questions = QMODEL.Question.objects.filter(course=course)
    
    correct_count = answers.filter(is_correct=True).count()
    total_q = questions.count()
    
    # Simple calculation for now (expandable with weighting/negative marks)
    raw_marks = Decimal(sum(a.question.marks for a in answers.filter(is_correct=True)))
    
    # Handle negative marking
    wrong_count = answers.filter(is_correct=False).count()
    unanswered_count = total_q - (correct_count + wrong_count)
    
    negative_deduction = Decimal(wrong_count) * course.negative_mark_per_wrong
    final_marks = max(raw_marks - negative_deduction, Decimal("0.00"))
    
    total_possible = sum(q.marks for q in questions)
    percentage = (final_marks / Decimal(total_possible) * 100) if total_possible > 0 else 0
    
    attempt_num = QMODEL.Result.objects.filter(student=student, exam=course).count() + 1
    
    result = QMODEL.Result.objects.create(
        student=student,
        exam=course,
        attempt_number=attempt_num,
        marks=final_marks,
        total_possible_marks=total_possible,
        total_questions=total_q,
        correct_answers=correct_count,
        wrong_answers=wrong_count,
        unanswered=unanswered_count,
        percentage=percentage,
        passed=(percentage >= course.pass_mark),
        tab_switches=session.current_question_index, # We'll reuse fields for now or expand session
    )
    
    session.is_completed = True
    session.save()
    
    messages.success(request, f"Exam submitted! You scored {percentage}%")
    return redirect("check-marks", pk=course.id)
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
        selected_ans = request.POST.get(f"question_{question.id}", "").strip()

        if not selected_ans:
            unanswered += 1
            continue

        is_correct = False
        if question.question_type in ["MCQ", "TRUE_FALSE"]:
            # Standard MCQ/TF handles answers as Option1, Option2, etc.
            if selected_ans == question.answer:
                is_correct = True
        elif question.question_type == "SHORT_ANSWER":
            # Case-insensitive comparison for short answers
            if selected_ans.lower() == question.answer.lower():
                is_correct = True

        if is_correct:
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

    tab_switches = int(request.POST.get("tab_switches", 0))
    attempt_number = attempts_taken + 1
    passed = percentage >= Decimal(course.pass_mark)

    result = QMODEL.Result.objects.create(
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
        tab_switches=tab_switches,
    )

    # Send Notification Email
    try:
        subject = f"Exam Result: {course.course_name}"
        message = (
            f"Hello {student.user.first_name},\n\n"
            f"You have completed your attempt #{attempt_number} for {course.course_name}.\n\n"
            f"Summary:\n"
            f"- Score: {final_marks}/{total_possible_marks}\n"
            f"- Percentage: {percentage}%\n"
            f"- Status: {'PASSED' if passed else 'FAILED'}\n"
            f"- Tab Switches: {tab_switches}\n\n"
            f"Login to the portal to view the full report.\n"
            f"Regards,\nExam System"
        )
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [student.institutional_email],
            fail_silently=True,
        )
    except Exception:
        pass

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
