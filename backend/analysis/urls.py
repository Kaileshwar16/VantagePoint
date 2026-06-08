"""URL routing for analysis app."""
from django.urls import path
from . import views

urlpatterns = [
    path('run/<int:company_id>/', views.run_analysis, name='run-analysis'),
    path('run-all/', views.run_all_analysis, name='run-all-analysis'),
]
