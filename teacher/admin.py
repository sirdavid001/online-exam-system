from django.contrib import admin

from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "staff_id",
        "designation",
        "faculty",
        "department",
        "official_email",
        "mobile",
        "status",
    )
    list_filter = (
        "status",
        "designation",
        "faculty",
        "department",
    )
    search_fields = (
        "user__first_name",
        "user__last_name",
        "staff_id",
        "official_email",
        "department",
        "faculty",
        "mobile",
    )
    autocomplete_fields = ("user",)
    list_select_related = ("user",)
    list_editable = ("status",)
    ordering = ("user__first_name", "user__last_name")
    actions = ("approve_selected_teachers", "set_selected_teachers_pending")

    fieldsets = (
        (
            "User Link",
            {
                "fields": ("user", "status"),
            },
        ),
        (
            "Institutional Identity",
            {
                "fields": (
                    "staff_id",
                    "official_email",
                    "designation",
                ),
            },
        ),
        (
            "Academic Placement",
            {
                "fields": ("faculty", "department"),
            },
        ),
        (
            "Contact",
            {
                "fields": ("mobile", "address", "profile_pic"),
            },
        ),
    )

    def full_name(self, obj):
        return obj.get_name

    full_name.short_description = "Name"

    @admin.action(description="Approve selected teachers")
    def approve_selected_teachers(self, request, queryset):
        queryset.update(status=True)

    @admin.action(description="Mark selected teachers as pending")
    def set_selected_teachers_pending(self, request, queryset):
        queryset.update(status=False)
