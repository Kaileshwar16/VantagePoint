"""URL routing for scraping app."""
from django.urls import path
from . import views

urlpatterns = [
    path('trigger/<int:company_id>/', views.trigger_scrape, name='trigger-scrape'),
    path('status/<int:job_id>/', views.scrape_status, name='scrape-status'),
]
