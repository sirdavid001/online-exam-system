import csv

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Avg, Count, OuterRef, Q, Subquery
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from student import forms as SFORM
from student import models as SMODEL
from teacher import forms as TFORM
from teacher import models as TMODEL

from . import forms, models


def home_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect("afterlogin")
    return render(request, "exam/index.html")


def privacy_policy_view(request):
    return render(request, "exam/privacy_policy.html")


def terms_of_use_view(request):
    return render(request, "exam/terms_of_use.html")


def is_teacher(user):
    return user.groups.filter(name="TEACHER").exists()


def is_student(user):
    return user.groups.filter(name="STUDENT").exists()


def is_admin(user):
    return user.is_active and (user.is_staff or user.is_superuser)


def admin_required(view_func):
    return user_passes_test(is_admin, login_url="adminlogin")(view_func)


def afterlogin_view(request):
    if is_student(request.user):
        return redirect("student-dashboard")

    if is_teacher(request.user):
        accountapproval = TMODEL.Teacher.objects.filter(user_id=request.user.id, status=True)
        if accountapproval:
            return redirect("teacher-dashboard")
        return render(request, "teacher/teacher_wait_for_approval.html")

    if is_admin(request.user):
        return redirect("admin-dashboard")

    return redirect("logout")


def _result_export_queryset():
    return models.Result.objects.select_related("student__user", "exam").order_by("-date", "-attempt_number")


def _get_institution_settings():
    settings_obj, _ = models.InstitutionSettings.objects.get_or_create(
        pk=1,
        defaults={
            "institution_name": "Dennis Osadebay University",
            "short_name": "DOU",
            "current_session": "2026/2027",
            "current_semester": "FIRST",
        },
    )
    return settings_obj


@admin_required
def admin_dashboard_view(request):
    institution = _get_institution_settings()
    total_student = SMODEL.Student.objects.count()
    total_teacher = TMODEL.Teacher.objects.filter(status=True).count()
    total_course = models.Course.objects.count()
    total_question = models.Question.objects.count()
    published_courses = models.Course.objects.filter(is_published=True).count()
    unpublished_courses = total_course - published_courses

    total_attempts = models.Result.objects.count()
    pass_attempts = models.Result.objects.filter(passed=True).count()
    failed_attempts = total_attempts - pass_attempts
    pass_rate = round((pass_attempts * 100 / total_attempts), 2) if total_attempts else 0

    avg_score = models.Result.objects.aggregate(avg=Avg("percentage"))["avg"] or 0
    recent_results = _result_export_queryset()[:8]

    top_courses = (
        models.Course.objects.annotate(
            attempt_count=Count("result"),
            avg_percentage=Avg("result__percentage"),
            pass_count=Count("result", filter=Q(result__passed=True)),
        )
        .filter(attempt_count__gt=0)
        .order_by("-avg_percentage", "-attempt_count")[:5]
    )

    latest_result_subquery = models.Result.objects.filter(student=OuterRef("pk")).order_by("-date", "-attempt_number")
    at_risk_students = (
        SMODEL.Student.objects.annotate(
            last_percentage=Subquery(latest_result_subquery.values("percentage")[:1]),
            last_passed=Subquery(latest_result_subquery.values("passed")[:1]),
            attempts_taken=Count("result"),
        )
        .filter(attempts_taken__gt=0, last_passed=False)
        .order_by("last_percentage", "user__last_name", "user__first_name")[:8]
    )

    context = {
        "institution": institution,
        "total_student": total_student,
        "total_teacher": total_teacher,
        "total_course": total_course,
        "total_question": total_question,
        "published_courses": published_courses,
        "unpublished_courses": unpublished_courses,
        "total_attempts": total_attempts,
        "pass_attempts": pass_attempts,
        "failed_attempts": failed_attempts,
        "pass_rate": pass_rate,
        "avg_score": avg_score,
        "recent_results": recent_results,
        "active_courses": models.Course.objects.filter(question_number__gt=0).count(),
        "pending_teacher": TMODEL.Teacher.objects.filter(status=False).count(),
        "top_courses": top_courses,
        "at_risk_students": at_risk_students,
        "active_announcements": models.AdminAnnouncement.active_for(
            models.AdminAnnouncement.AUDIENCE_ALL
        ).count(),
        "latest_announcements": models.AdminAnnouncement.objects.order_by("-created_at")[:6],
        "governance_alert_courses": models.Course.objects.filter(
            Q(is_published=False) | Q(question_number=0)
        ).order_by("course_name")[:8],
    }
    return render(request, "exam/admin_dashboard.html", context=context)


@admin_required
def admin_system_settings_view(request):
    settings_obj = _get_institution_settings()
    form = forms.InstitutionSettingsForm(instance=settings_obj)

    if request.method == "POST":
        form = forms.InstitutionSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Institution settings updated successfully.")
            return redirect("admin-system-settings")
        messages.error(request, "Could not update institution settings. Review the fields below.")

    return render(request, "exam/admin_system_settings.html", {"form": form, "settings_obj": settings_obj})


@admin_required
def admin_announcements_view(request):
    announcement_id = request.GET.get("edit")
    edit_announcement = None
    if announcement_id:
        edit_announcement = get_object_or_404(models.AdminAnnouncement, id=announcement_id)

    form = forms.AdminAnnouncementForm(instance=edit_announcement)

    if request.method == "POST":
        posted_announcement_id = request.POST.get("announcement_id")
        instance = None
        if posted_announcement_id:
            instance = get_object_or_404(models.AdminAnnouncement, id=posted_announcement_id)
        form = forms.AdminAnnouncementForm(request.POST, instance=instance)
        if form.is_valid():
            announcement = form.save()
            action = "updated" if posted_announcement_id else "created"
            messages.success(request, f"Announcement '{announcement.title}' {action} successfully.")
            return redirect("admin-announcements")
        messages.error(request, "Could not save announcement. Review the fields below.")

    announcements = models.AdminAnnouncement.objects.all()
    return render(
        request,
        "exam/admin_announcements.html",
        {
            "form": form,
            "announcements": announcements,
            "edit_announcement": edit_announcement,
        },
    )


@admin_required
def toggle_announcement_view(request, pk):
    if request.method != "POST":
        messages.error(request, "Invalid announcement action request.")
        return redirect("admin-announcements")

    announcement = get_object_or_404(models.AdminAnnouncement, id=pk)
    announcement.is_active = not announcement.is_active
    announcement.save(update_fields=["is_active", "updated_at"])
    status = "active" if announcement.is_active else "inactive"
    messages.success(request, f"Announcement '{announcement.title}' is now {status}.")
    return redirect("admin-announcements")


@admin_required
def delete_announcement_view(request, pk):
    if request.method != "POST":
        messages.error(request, "Invalid announcement action request.")
        return redirect("admin-announcements")

    announcement = get_object_or_404(models.AdminAnnouncement, id=pk)
    title = announcement.title
    announcement.delete()
    messages.success(request, f"Announcement '{title}' deleted.")
    return redirect("admin-announcements")


@admin_required
def admin_export_results_csv_view(request):
    response = HttpResponse(content_type="text/csv")
    filename = timezone.now().strftime("exam_results_%Y%m%d_%H%M%S.csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Student Name",
            "Matric Number",
            "Exam",
            "Attempt",
            "Score",
            "Total Possible",
            "Percentage",
            "Passed",
            "Correct",
            "Wrong",
            "Unanswered",
            "Date",
        ]
    )

    for result in _result_export_queryset():
        writer.writerow(
            [
                result.student.get_name,
                result.student.matric_number,
                result.exam.course_name,
                result.attempt_number,
                result.marks,
                result.total_possible_marks,
                result.percentage,
                "Yes" if result.passed else "No",
                result.correct_answers,
                result.wrong_answers,
                result.unanswered,
                result.date.isoformat(),
            ]
        )

    return response


@admin_required
def admin_export_results_excel_view(request):
    response = HttpResponse(content_type="application/vnd.ms-excel")
    filename = timezone.now().strftime("exam_results_%Y%m%d_%H%M%S.xls")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response, delimiter="\t")
    writer.writerow(
        [
            "Student Name",
            "Matric Number",
            "Exam",
            "Attempt",
            "Score",
            "Total Possible",
            "Percentage",
            "Passed",
            "Correct",
            "Wrong",
            "Unanswered",
            "Date",
        ]
    )

    for result in _result_export_queryset():
        writer.writerow(
            [
                result.student.get_name,
                result.student.matric_number,
                result.exam.course_name,
                result.attempt_number,
                result.marks,
                result.total_possible_marks,
                result.percentage,
                "Yes" if result.passed else "No",
                result.correct_answers,
                result.wrong_answers,
                result.unanswered,
                result.date.isoformat(),
            ]
        )

    return response


@admin_required
def admin_export_students_csv_view(request):
    response = HttpResponse(content_type="text/csv")
    filename = timezone.now().strftime("students_%Y%m%d_%H%M%S.csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Name",
            "Matric Number",
            "Institutional Email",
            "Faculty",
            "Department",
            "Programme",
            "Level",
            "Entry Year",
            "Phone",
            "Address",
        ]
    )

    for student in SMODEL.Student.objects.select_related("user").order_by("user__last_name", "user__first_name"):
        writer.writerow(
            [
                student.get_name,
                student.matric_number,
                student.institutional_email,
                student.faculty,
                student.department,
                student.programme,
                student.get_current_level_display(),
                student.entry_year,
                student.mobile,
                student.address,
            ]
        )

    return response


@admin_required
def admin_export_teachers_csv_view(request):
    response = HttpResponse(content_type="text/csv")
    filename = timezone.now().strftime("teachers_%Y%m%d_%H%M%S.csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Name",
            "Staff ID",
            "Official Email",
            "Designation",
            "Faculty",
            "Department",
            "Phone",
            "Address",
            "Approved",
        ]
    )

    for teacher in TMODEL.Teacher.objects.select_related("user").order_by("user__last_name", "user__first_name"):
        writer.writerow(
            [
                teacher.get_name,
                teacher.staff_id,
                teacher.official_email,
                teacher.get_designation_display(),
                teacher.faculty,
                teacher.department,
                teacher.mobile,
                teacher.address,
                "Yes" if teacher.status else "No",
            ]
        )

    return response


@admin_required
def admin_export_courses_csv_view(request):
    response = HttpResponse(content_type="text/csv")
    filename = timezone.now().strftime("courses_%Y%m%d_%H%M%S.csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Course",
            "Course Code",
            "Level",
            "Semester",
            "Academic Session",
            "Questions",
            "Total Marks",
            "Duration Minutes",
            "Pass Mark %",
            "Max Attempts",
            "Negative Mark Per Wrong",
            "Shuffle Questions",
            "Published",
            "Available From",
            "Available Until",
        ]
    )

    for course in models.Course.objects.order_by("course_name"):
        writer.writerow(
            [
                course.course_name,
                course.course_code,
                course.get_level_display(),
                course.get_semester_display(),
                course.academic_session,
                course.question_number,
                course.total_marks,
                course.duration_minutes,
                course.pass_mark,
                course.max_attempts,
                course.negative_mark_per_wrong,
                "Yes" if course.shuffle_questions else "No",
                "Yes" if course.is_published else "No",
                course.available_from.isoformat() if course.available_from else "",
                course.available_until.isoformat() if course.available_until else "",
            ]
        )

    return response


@admin_required
def admin_teacher_view(request):
    context = {
        "total_teacher": TMODEL.Teacher.objects.filter(status=True).count(),
        "pending_teacher": TMODEL.Teacher.objects.filter(status=False).count(),
    }
    return render(request, "exam/admin_teacher.html", context=context)


@admin_required
def admin_view_teacher_view(request):
    selected_q = request.GET.get("q", "").strip()
    teachers = TMODEL.Teacher.objects.filter(status=True).select_related("user")

    if selected_q:
        teachers = teachers.filter(
            Q(user__first_name__icontains=selected_q)
            | Q(user__last_name__icontains=selected_q)
            | Q(staff_id__icontains=selected_q)
            | Q(official_email__icontains=selected_q)
            | Q(department__icontains=selected_q)
            | Q(faculty__icontains=selected_q)
        )

    teachers = teachers.order_by("user__last_name", "user__first_name")
    return render(
        request,
        "exam/admin_view_teacher.html",
        {"teachers": teachers, "selected_q": selected_q, "teachers_count": teachers.count()},
    )


@admin_required
def update_teacher_view(request, pk):
    teacher = get_object_or_404(TMODEL.Teacher, id=pk)
    user = get_object_or_404(TMODEL.User, id=teacher.user_id)
    userForm = TFORM.TeacherUserForm(instance=user)
    teacherForm = TFORM.TeacherForm(request.FILES, instance=teacher)
    mydict = {"userForm": userForm, "teacherForm": teacherForm}

    if request.method == "POST":
        userForm = TFORM.TeacherUserForm(request.POST, instance=user)
        teacherForm = TFORM.TeacherForm(request.POST, request.FILES, instance=teacher)
        if userForm.is_valid() and teacherForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            teacherForm.save()
            messages.success(request, "Teacher updated successfully.")
            return redirect("admin-view-teacher")

        messages.error(request, "Could not update teacher. Please review the form fields.")

    return render(request, "exam/update_teacher.html", context=mydict)


@admin_required
def delete_teacher_view(request, pk):
    teacher = get_object_or_404(TMODEL.Teacher, id=pk)
    user = get_object_or_404(User, id=teacher.user_id)
    user.delete()
    teacher.delete()
    messages.success(request, "Teacher deleted.")
    return HttpResponseRedirect("/admin-view-teacher")


@admin_required
def admin_view_pending_teacher_view(request):
    teachers = TMODEL.Teacher.objects.filter(status=False)
    return render(request, "exam/admin_view_pending_teacher.html", {"teachers": teachers})


@admin_required
def approve_teacher_view(request, pk):
    teacher = get_object_or_404(TMODEL.Teacher, id=pk)
    if teacher.status:
        messages.info(request, "Teacher is already approved.")
    else:
        teacher.status = True
        teacher.save(update_fields=["status"])
        messages.success(request, "Teacher approved successfully.")
    return HttpResponseRedirect("/admin-view-pending-teacher")


@admin_required
def reject_teacher_view(request, pk):
    teacher = get_object_or_404(TMODEL.Teacher, id=pk)
    user = get_object_or_404(User, id=teacher.user_id)
    user.delete()
    teacher.delete()
    messages.success(request, "Teacher request rejected and deleted.")
    return HttpResponseRedirect("/admin-view-pending-teacher")


@admin_required
def admin_student_view(request):
    context = {
        "total_student": SMODEL.Student.objects.all().count(),
    }
    return render(request, "exam/admin_student.html", context=context)


@admin_required
def admin_view_student_view(request):
    selected_q = request.GET.get("q", "").strip()
    students = SMODEL.Student.objects.select_related("user")

    if selected_q:
        students = students.filter(
            Q(user__first_name__icontains=selected_q)
            | Q(user__last_name__icontains=selected_q)
            | Q(matric_number__icontains=selected_q)
            | Q(institutional_email__icontains=selected_q)
            | Q(department__icontains=selected_q)
            | Q(faculty__icontains=selected_q)
            | Q(programme__icontains=selected_q)
        )

    students = students.order_by("user__last_name", "user__first_name")
    return render(
        request,
        "exam/admin_view_student.html",
        {"students": students, "selected_q": selected_q, "students_count": students.count()},
    )


@admin_required
def update_student_view(request, pk):
    student = get_object_or_404(SMODEL.Student, id=pk)
    user = get_object_or_404(SMODEL.User, id=student.user_id)
    userForm = SFORM.StudentUserForm(instance=user)
    studentForm = SFORM.StudentForm(request.FILES, instance=student)
    mydict = {"userForm": userForm, "studentForm": studentForm}

    if request.method == "POST":
        userForm = SFORM.StudentUserForm(request.POST, instance=user)
        studentForm = SFORM.StudentForm(request.POST, request.FILES, instance=student)
        if userForm.is_valid() and studentForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            studentForm.save()
            messages.success(request, "Student updated successfully.")
            return redirect("admin-view-student")

        messages.error(request, "Could not update student. Please review the form fields.")

    return render(request, "exam/update_student.html", context=mydict)


@admin_required
def delete_student_view(request, pk):
    student = get_object_or_404(SMODEL.Student, id=pk)
    user = get_object_or_404(User, id=student.user_id)
    user.delete()
    student.delete()
    messages.success(request, "Student deleted.")
    return HttpResponseRedirect("/admin-view-student")


@admin_required
def admin_course_view(request):
    return render(request, "exam/admin_course.html")


@admin_required
def admin_add_course_view(request):
    courseForm = forms.CourseForm()

    if request.method == "POST":
        courseForm = forms.CourseForm(request.POST)
        if courseForm.is_valid():
            course = courseForm.save()
            messages.success(request, f"Course '{course.course_name}' created successfully.")
            return HttpResponseRedirect("/admin-view-course")

        messages.error(request, "Could not create course. Please review the form fields.")

    return render(request, "exam/admin_add_course.html", {"courseForm": courseForm})


@admin_required
def admin_view_course_view(request):
    selected_q = request.GET.get("q", "").strip()
    selected_status = request.GET.get("status", "").strip()
    courses = models.Course.objects.all()

    if selected_q:
        courses = courses.filter(
            Q(course_name__icontains=selected_q)
            | Q(course_code__icontains=selected_q)
            | Q(academic_session__icontains=selected_q)
        )

    if selected_status == "published":
        courses = courses.filter(is_published=True)
    elif selected_status == "unpublished":
        courses = courses.filter(is_published=False)

    courses = courses.order_by("course_name")
    return render(
        request,
        "exam/admin_view_course.html",
        {
            "courses": courses,
            "selected_q": selected_q,
            "selected_status": selected_status,
            "courses_count": courses.count(),
        },
    )


@admin_required
def update_course_view(request, pk):
    course = get_object_or_404(models.Course, id=pk)
    courseForm = forms.CourseForm(instance=course)

    if request.method == "POST":
        courseForm = forms.CourseForm(request.POST, instance=course)
        if courseForm.is_valid():
            updated_course = courseForm.save()
            messages.success(request, f"Course '{updated_course.course_name}' updated successfully.")
            return redirect("admin-view-course")

        messages.error(request, "Could not update course. Please review the form fields.")

    return render(
        request,
        "exam/update_course.html",
        {"courseForm": courseForm, "course": course},
    )


@admin_required
def delete_course_view(request, pk):
    course = get_object_or_404(models.Course, id=pk)
    course_name = course.course_name
    course.delete()
    messages.success(request, f"Course '{course_name}' deleted.")
    return HttpResponseRedirect("/admin-view-course")


@admin_required
def toggle_course_publish_view(request, pk):
    if request.method != "POST":
        messages.error(request, "Invalid publish action request.")
        return redirect("admin-view-course")

    course = get_object_or_404(models.Course, id=pk)
    course.is_published = not course.is_published
    course.save(update_fields=["is_published"])
    status = "published" if course.is_published else "unpublished"
    messages.success(request, f"Course '{course.course_name}' is now {status}.")

    next_url = request.GET.get("next")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect("admin-view-course")


@admin_required
def admin_question_view(request):
    return render(request, "exam/admin_question.html")


@admin_required
def admin_add_question_view(request):
    questionForm = forms.QuestionForm()

    if request.method == "POST":
        questionForm = forms.QuestionForm(request.POST)
        if questionForm.is_valid():
            question = questionForm.save(commit=False)
            course = get_object_or_404(models.Course, id=request.POST.get("courseID"))
            question.course = course
            question.save()
            messages.success(request, "Question saved successfully.")
            return HttpResponseRedirect("/admin-view-question")

        messages.error(request, "Could not save question. Please review the form fields.")

    return render(request, "exam/admin_add_question.html", {"questionForm": questionForm})


@admin_required
def admin_view_question_view(request):
    courses = models.Course.objects.all()
    return render(request, "exam/admin_view_question.html", {"courses": courses})


@admin_required
def view_question_view(request, pk):
    course = get_object_or_404(models.Course, id=pk)
    questions = models.Question.objects.filter(course=course)
    return render(
        request,
        "exam/view_question.html",
        {"questions": questions, "course": course},
    )


@admin_required
def update_question_view(request, pk):
    question = get_object_or_404(models.Question, id=pk)
    questionForm = forms.QuestionForm(instance=question, initial={"courseID": question.course_id})

    if request.method == "POST":
        questionForm = forms.QuestionForm(request.POST, instance=question)
        if questionForm.is_valid():
            updated_question = questionForm.save(commit=False)
            updated_question.course = questionForm.cleaned_data["courseID"]
            updated_question.save()
            messages.success(request, "Question updated successfully.")
            return redirect("view-question", pk=updated_question.course_id)

        messages.error(request, "Could not update question. Please review the form fields.")

    return render(
        request,
        "exam/update_question.html",
        {"questionForm": questionForm, "question": question},
    )


@admin_required
def delete_question_view(request, pk):
    question = get_object_or_404(models.Question, id=pk)
    course_id = question.course_id
    question.delete()
    messages.success(request, "Question deleted.")

    next_url = request.GET.get("next")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)

    return redirect("view-question", pk=course_id)


@admin_required
def admin_view_student_marks_view(request):
    students = SMODEL.Student.objects.all()
    return render(request, "exam/admin_view_student_marks.html", {"students": students})


@admin_required
def admin_view_marks_view(request, student_id):
    courses = models.Course.objects.all()
    return render(
        request,
        "exam/admin_view_marks.html",
        {"courses": courses, "student_id": student_id},
    )


@admin_required
def admin_check_marks_view(request, student_id, course_id):
    course = get_object_or_404(models.Course, id=course_id)
    student = get_object_or_404(SMODEL.Student, id=student_id)
    results = models.Result.objects.filter(exam=course, student=student).order_by("-attempt_number")
    return render(
        request,
        "exam/admin_check_marks.html",
        {"results": results, "course": course, "student": student},
    )


@admin_required
def admin_results_view(request):
    results = models.Result.objects.select_related("student__user", "exam").order_by("-date", "-attempt_number")
    students = SMODEL.Student.objects.select_related("user").order_by("user__last_name", "user__first_name")
    courses = models.Course.objects.order_by("course_name")

    selected_student = request.GET.get("student", "")
    selected_course = request.GET.get("course", "")
    selected_status = request.GET.get("status", "")

    if selected_student:
        results = results.filter(student_id=selected_student)

    if selected_course:
        results = results.filter(exam_id=selected_course)

    if selected_status == "passed":
        results = results.filter(passed=True)
    elif selected_status == "failed":
        results = results.filter(passed=False)

    context = {
        "results": results,
        "students": students,
        "courses": courses,
        "selected_student": selected_student,
        "selected_course": selected_course,
        "selected_status": selected_status,
        "results_count": results.count(),
    }
    return render(request, "exam/admin_results.html", context)


@admin_required
def delete_result_view(request, pk):
    result = get_object_or_404(models.Result.objects.select_related("student", "exam"), id=pk)
    student_name = result.student.get_name
    exam_name = result.exam.course_name
    result.delete()
    messages.success(request, f"Deleted attempt record for {student_name} ({exam_name}).")

    next_url = request.GET.get("next")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)

    return redirect("admin-results")


def aboutus_view(request):
    return render(request, "exam/aboutus.html")


def contactus_view(request):
    sub = forms.ContactusForm()
    if request.method == "POST":
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            email = sub.cleaned_data["Email"]
            name = sub.cleaned_data["Name"]
            message = sub.cleaned_data["Message"]
            send_mail(
                str(name) + " || " + str(email),
                message,
                settings.DEFAULT_FROM_EMAIL,
                settings.EMAIL_RECEIVING_USER,
                fail_silently=False,
            )
            return render(request, "exam/contactussuccess.html")
    return render(request, "exam/contactus.html", {"form": sub})
