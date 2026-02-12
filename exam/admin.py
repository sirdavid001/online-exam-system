from django.contrib import admin

from .models import AdminAnnouncement, Course, InstitutionSettings, Question, Result


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "course_code",
        "course_name",
        "level",
        "semester",
        "academic_session",
        "question_number",
        "total_marks",
        "duration_minutes",
        "pass_mark",
        "max_attempts",
        "negative_mark_per_wrong",
        "shuffle_questions",
        "is_published",
        "available_from",
        "available_until",
    )
    list_filter = (
        "is_published",
        "level",
        "semester",
        "shuffle_questions",
        "pass_mark",
        "max_attempts",
        "duration_minutes",
    )
    search_fields = ("course_name", "course_code", "academic_session", "instructions")
    ordering = ("course_name",)
    readonly_fields = ("question_number", "total_marks")
    fieldsets = (
        (
            "Course Details",
            {
                "fields": (
                    "course_name",
                    "course_code",
                    "level",
                    "semester",
                    "academic_session",
                    "instructions",
                ),
            },
        ),
        (
            "Exam Rules",
            {
                "fields": (
                    "duration_minutes",
                    "pass_mark",
                    "max_attempts",
                    "negative_mark_per_wrong",
                    "shuffle_questions",
                    "is_published",
                    "available_from",
                    "available_until",
                ),
            },
        ),
        (
            "Calculated Metrics",
            {
                "fields": ("question_number", "total_marks"),
            },
        ),
    )


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "course",
        "marks",
        "difficulty",
        "answer",
        "short_question",
    )
    list_filter = ("course", "difficulty", "marks")
    search_fields = (
        "question",
        "option1",
        "option2",
        "option3",
        "option4",
        "explanation",
    )
    autocomplete_fields = ("course",)
    list_select_related = ("course",)
    ordering = ("course", "id")

    def short_question(self, obj):
        text = obj.question.strip()
        return text if len(text) <= 90 else f"{text[:87]}..."

    short_question.short_description = "Question"


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = (
        "student_name",
        "exam",
        "attempt_number",
        "marks",
        "total_possible_marks",
        "percentage",
        "passed",
        "date",
    )
    list_filter = ("exam", "passed", "date")
    search_fields = (
        "student__user__first_name",
        "student__user__last_name",
        "student__matric_number",
        "exam__course_name",
    )
    list_select_related = ("student", "student__user", "exam")
    ordering = ("-date", "-attempt_number")
    readonly_fields = ("date",)

    def student_name(self, obj):
        return obj.student.get_name

    student_name.short_description = "Student"


@admin.register(InstitutionSettings)
class InstitutionSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "institution_name",
        "short_name",
        "current_session",
        "current_semester",
        "allow_student_signup",
        "allow_teacher_signup",
        "updated_at",
    )
    search_fields = ("institution_name", "short_name", "support_email")
    readonly_fields = ("updated_at",)


@admin.register(AdminAnnouncement)
class AdminAnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "audience",
        "is_active",
        "starts_at",
        "ends_at",
        "updated_at",
    )
    list_filter = ("audience", "is_active", "starts_at", "ends_at")
    search_fields = ("title", "message")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


admin.site.site_header = "Online Examination Backend"
admin.site.site_title = "Online Examination Admin"
admin.site.index_title = "Administration"
