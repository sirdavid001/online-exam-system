from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render

from exam import forms as QFORM
from exam import models as QMODEL
from student import models as SMODEL

from . import forms, models
from .services import QuestionUploadError, parse_questions_upload


def teacher_signup_view(request):
    userForm = forms.TeacherUserForm()
    teacherForm = forms.TeacherForm()

    if request.method == "POST":
        userForm = forms.TeacherUserForm(request.POST)
        teacherForm = forms.TeacherForm(request.POST, request.FILES)
        if userForm.is_valid() and teacherForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            teacher = teacherForm.save(commit=False)
            teacher.user = user
            teacher.save()
            my_teacher_group = Group.objects.get_or_create(name="TEACHER")
            my_teacher_group[0].user_set.add(user)
            messages.success(request, "Teacher account created. Waiting for admin approval.")
            return HttpResponseRedirect("teacherlogin")
        messages.error(request, "Please provide valid professional details for verification.")

    return render(
        request,
        "teacher/teachersignup.html",
        context={"userForm": userForm, "teacherForm": teacherForm},
    )


def is_teacher(user):
    return user.groups.filter(name="TEACHER").exists()


@login_required(login_url="teacherlogin")
@user_passes_test(is_teacher, login_url="teacherlogin")
def teacher_dashboard_view(request):
    context = {
        "total_course": QMODEL.Course.objects.all().count(),
        "total_question": QMODEL.Question.objects.all().count(),
        "total_student": SMODEL.Student.objects.all().count(),
    }
    return render(request, "teacher/teacher_dashboard.html", context=context)


@login_required(login_url="teacherlogin")
@user_passes_test(is_teacher, login_url="teacherlogin")
def teacher_exam_view(request):
    return render(request, "teacher/teacher_exam.html")


@login_required(login_url="teacherlogin")
@user_passes_test(is_teacher, login_url="teacherlogin")
def teacher_add_exam_view(request):
    courseForm = QFORM.CourseForm()
    if request.method == "POST":
        courseForm = QFORM.CourseForm(request.POST)
        if courseForm.is_valid():
            course = courseForm.save()
            messages.success(request, f"Course '{course.course_name}' created successfully.")
            return HttpResponseRedirect("/teacher/teacher-view-exam")
        messages.error(request, "Could not create course. Please fix the highlighted fields.")
    return render(request, "teacher/teacher_add_exam.html", {"courseForm": courseForm})


@login_required(login_url="teacherlogin")
@user_passes_test(is_teacher, login_url="teacherlogin")
def teacher_view_exam_view(request):
    courses = QMODEL.Course.objects.all()
    return render(request, "teacher/teacher_view_exam.html", {"courses": courses})


@login_required(login_url="teacherlogin")
@user_passes_test(is_teacher, login_url="teacherlogin")
def delete_exam_view(request, pk):
    course = get_object_or_404(QMODEL.Course, id=pk)
    course_name = course.course_name
    course.delete()
    messages.success(request, f"Course '{course_name}' deleted.")
    return HttpResponseRedirect("/teacher/teacher-view-exam")


@login_required(login_url="teacherlogin")
@user_passes_test(is_teacher, login_url="teacherlogin")
def teacher_question_view(request):
    return render(request, "teacher/teacher_question.html")


@login_required(login_url="teacherlogin")
@user_passes_test(is_teacher, login_url="teacherlogin")
def teacher_add_question_view(request):
    questionForm = QFORM.QuestionForm()
    if request.method == "POST":
        questionForm = QFORM.QuestionForm(request.POST)
        if questionForm.is_valid():
            question = questionForm.save(commit=False)
            course = get_object_or_404(QMODEL.Course, id=request.POST.get("courseID"))
            question.course = course
            question.save()
            messages.success(request, "Question saved successfully.")
            return HttpResponseRedirect("/teacher/teacher-view-question")
        messages.error(request, "Could not save question. Please review the form fields.")
    return render(request, "teacher/teacher_add_question.html", {"questionForm": questionForm})


@login_required(login_url="teacherlogin")
@user_passes_test(is_teacher, login_url="teacherlogin")
def teacher_upload_questions_view(request):
    uploadForm = forms.QuestionUploadForm()

    if request.method == "POST":
        uploadForm = forms.QuestionUploadForm(request.POST, request.FILES)
        if uploadForm.is_valid():
            course = uploadForm.cleaned_data["courseID"]
            upload_file = uploadForm.cleaned_data["questions_file"]
            has_header = uploadForm.cleaned_data["has_header"]

            try:
                outcome = parse_questions_upload(upload_file, course=course, has_header=has_header)
            except QuestionUploadError as exc:
                messages.error(request, str(exc))
            else:
                if outcome.questions:
                    with transaction.atomic():
                        QMODEL.Question.objects.bulk_create(outcome.questions)
                        course.refresh_assessment_totals()
                    messages.success(
                        request,
                        f"Imported {len(outcome.questions)} questions into {course.course_name}.",
                    )
                else:
                    messages.warning(request, "No valid rows were found to import.")

                if outcome.errors:
                    preview_limit = 8
                    for err in outcome.errors[:preview_limit]:
                        messages.warning(request, err)
                    hidden_count = len(outcome.errors) - preview_limit
                    if hidden_count > 0:
                        messages.warning(
                            request,
                            f"{hidden_count} more row errors were found. Fix your file and re-upload.",
                        )

                return redirect("teacher-upload-questions")
        else:
            messages.error(request, "Please fix the form errors and try again.")

    context = {
        "uploadForm": uploadForm,
        "sample_columns": "question,marks,option1,option2,option3,option4,answer,difficulty,explanation",
    }
    return render(request, "teacher/teacher_upload_questions.html", context)


@login_required(login_url="teacherlogin")
@user_passes_test(is_teacher, login_url="teacherlogin")
def teacher_view_question_view(request):
    courses = QMODEL.Course.objects.all()
    return render(request, "teacher/teacher_view_question.html", {"courses": courses})


@login_required(login_url="teacherlogin")
@user_passes_test(is_teacher, login_url="teacherlogin")
def see_question_view(request, pk):
    questions = QMODEL.Question.objects.filter(course_id=pk)
    return render(request, "teacher/see_question.html", {"questions": questions})


@login_required(login_url="teacherlogin")
@user_passes_test(is_teacher, login_url="teacherlogin")
def remove_question_view(request, pk):
    question = get_object_or_404(QMODEL.Question, id=pk)
    question.delete()
    messages.success(request, "Question deleted.")
    return HttpResponseRedirect("/teacher/teacher-view-question")
