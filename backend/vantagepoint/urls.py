"""VantagePoint URL Configuration"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/scraping/', include('scraping.urls')),
    path('api/analysis/', include('analysis.urls')),
]
