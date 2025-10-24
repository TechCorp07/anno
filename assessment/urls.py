"""
URL Configuration for Assessment App
"""
from django.urls import path
from assessment.admin import admin_dashboard_view
from assessment import proctoring_views, analytics_views
from . import views

urlpatterns = [
    # Authentication
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Tests
    path('test/<int:test_id>/', views.test_detail, name='test_detail'),
    path('test/<int:test_id>/start/', views.start_test, name='start_test'),
    path('attempt/<int:attempt_id>/take/', views.take_test, name='take_test'),
    path('attempt/<int:attempt_id>/submit/', views.submit_test, name='submit_test'),
    path('attempt/<int:attempt_id>/result/', views.test_result, name='test_result'),
    path('attempt/<int:attempt_id>/dicom/<int:question_id>/', views.dicom_question_view, name='dicom_question'),
    path('attempt/<int:attempt_id>/submit-dicom/', views.submit_dicom_answer, name='submit_dicom_answer'),
    
    # HTMX endpoints
    path('attempt/<int:attempt_id>/answer/', views.submit_answer, name='submit_answer'),
    path('attempt/<int:attempt_id>/time/', views.get_time_remaining, name='get_time_remaining'),
    
    # Proctoring URLs
    path('proctoring/snapshot/<int:attempt_id>/', proctoring_views.upload_proctoring_snapshot, name='upload_snapshot'),
    path('proctoring/event/<int:attempt_id>/', proctoring_views.log_proctoring_event, name='log_event'),
    path('test/<int:test_id>/consent/', proctoring_views.test_consent_form, name='test_consent'),
    
    # User Analytics
    path('analytics/', analytics_views.user_analytics_dashboard, name='user_analytics'),
    
    # Admin Dashboard
    path('admin/dashboard/', admin_dashboard_view, name='admin_dashboard_main'),
        
    # Admin Analytics (staff only)
    path('admin-analytics/', analytics_views.admin_analytics_dashboard, name='admin_analytics'),
    path('admin-analytics/export/', analytics_views.export_analytics_excel, name='export_analytics'),
]