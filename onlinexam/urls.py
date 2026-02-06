from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

from exam import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('teacher/', include('teacher.urls')),
    path('student/', include('student.urls')),

    path('', views.home_view, name=''),
    path('logout', LogoutView.as_view(template_name='exam/logout.html'), name='logout'),
    path('contactus', views.contactus_view),
    path('afterlogin', views.afterlogin_view, name='afterlogin'),

    path('adminclick', views.adminclick_view),
    path('adminlogin', LoginView.as_view(template_name='exam/adminlogin.html'), name='adminlogin'),
    path('admin-dashboard', views.admin_dashboard_view, name='admin-dashboard'),
    path('admin-results', views.admin_results_view, name='admin-results'),
    path('delete-result/<int:pk>', views.delete_result_view, name='delete-result'),

    path('admin-export-results-csv', views.admin_export_results_csv_view, name='admin-export-results-csv'),
    path('admin-export-results-excel', views.admin_export_results_excel_view, name='admin-export-results-excel'),
    path('admin-export-students-csv', views.admin_export_students_csv_view, name='admin-export-students-csv'),
    path('admin-export-teachers-csv', views.admin_export_teachers_csv_view, name='admin-export-teachers-csv'),
    path('admin-export-courses-csv', views.admin_export_courses_csv_view, name='admin-export-courses-csv'),

    path('admin-teacher', views.admin_teacher_view, name='admin-teacher'),
    path('admin-view-teacher', views.admin_view_teacher_view, name='admin-view-teacher'),
    path('update-teacher/<int:pk>', views.update_teacher_view, name='update-teacher'),
    path('delete-teacher/<int:pk>', views.delete_teacher_view, name='delete-teacher'),
    path('admin-view-pending-teacher', views.admin_view_pending_teacher_view, name='admin-view-pending-teacher'),
    path('approve-teacher/<int:pk>', views.approve_teacher_view, name='approve-teacher'),
    path('reject-teacher/<int:pk>', views.reject_teacher_view, name='reject-teacher'),

    path('admin-student', views.admin_student_view, name='admin-student'),
    path('admin-view-student', views.admin_view_student_view, name='admin-view-student'),
    path('admin-view-student-marks', views.admin_view_student_marks_view, name='admin-view-student-marks'),
    path('admin-view-marks/<int:student_id>', views.admin_view_marks_view, name='admin-view-marks'),
    path('admin-check-marks/<int:student_id>/<int:course_id>', views.admin_check_marks_view, name='admin-check-marks'),
    path('update-student/<int:pk>', views.update_student_view, name='update-student'),
    path('delete-student/<int:pk>', views.delete_student_view, name='delete-student'),

    path('admin-course', views.admin_course_view, name='admin-course'),
    path('admin-add-course', views.admin_add_course_view, name='admin-add-course'),
    path('admin-view-course', views.admin_view_course_view, name='admin-view-course'),
    path('update-course/<int:pk>', views.update_course_view, name='update-course'),
    path('delete-course/<int:pk>', views.delete_course_view, name='delete-course'),

    path('admin-question', views.admin_question_view, name='admin-question'),
    path('admin-add-question', views.admin_add_question_view, name='admin-add-question'),
    path('admin-view-question', views.admin_view_question_view, name='admin-view-question'),
    path('view-question/<int:pk>', views.view_question_view, name='view-question'),
    path('update-question/<int:pk>', views.update_question_view, name='update-question'),
    path('delete-question/<int:pk>', views.delete_question_view, name='delete-question'),
]
