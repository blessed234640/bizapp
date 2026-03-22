from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/projects/', views.api_projects, name='api_projects'),
    path('api/tasks/', views.api_tasks, name='api_tasks'),
    path('api/reports/tasks-stats/', views.api_stats, name='api_stats'),
]