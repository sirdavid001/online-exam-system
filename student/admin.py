from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "matric_number",
        "current_level",
        "faculty",
        "department",
        "programme",
        "institutional_email",
        "mobile",
    )
    list_filter = (
        "current_level",
        "faculty",
        "department",
        "entry_year",
    )
    search_fields = (
        "user__first_name",
        "user__last_name",
        "matric_number",
        "institutional_email",
        "department",
        "faculty",
        "programme",
        "mobile",
    )
    autocomplete_fields = ("user",)
    list_select_related = ("user",)
    list_editable = ("current_level",)
    ordering = ("user__first_name", "user__last_name")

    fieldsets = (
        (
            "User Link",
            {
                "fields": ("user",),
            },
        ),
        (
            "Institutional Identity",
            {
                "fields": (
                    "matric_number",
                    "institutional_email",
                ),
            },
        ),
        (
            "Academic Placement",
            {
                "fields": (
                    "faculty",
                    "department",
                    "programme",
                    "current_level",
                    "entry_year",
                ),
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
