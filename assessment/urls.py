"""
URL Configuration for Assessment App
"""
from django.urls import path
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
    
    # HTMX endpoints
    path('attempt/<int:attempt_id>/answer/', views.submit_answer, name='submit_answer'),
    path('attempt/<int:attempt_id>/time/', views.get_time_remaining, name='get_time_remaining'),
]