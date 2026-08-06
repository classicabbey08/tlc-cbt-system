from django.urls import path

from . import views

app_name = 'attempts'

urlpatterns = [
    # Student
    path('available/', views.available_exams, name='available_exams'),
    path('start/<int:exam_id>/', views.start_exam, name='start_exam'),
    path('take/<int:attempt_id>/', views.take_exam, name='take_exam'),
    path('submit/<int:attempt_id>/', views.submit_exam, name='submit_exam'),
    path('result/<int:attempt_id>/', views.result_detail, name='result_detail'),

    # Teacher
    path('teacher/results/', views.teacher_results, name='teacher_results'),

    # Super Admin
    path('admin/results/', views.admin_results, name='admin_results'),
]
