"""URL routing for the VantagePoint API."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CompanyViewSet, DataPointViewSet, PatternViewSet,
    InsightViewSet, ScrapeJobViewSet, dashboard_stats,
)

router = DefaultRouter()
router.register(r'companies', CompanyViewSet)
router.register(r'datapoints', DataPointViewSet)
router.register(r'patterns', PatternViewSet)
router.register(r'insights', InsightViewSet)
router.register(r'scrape-jobs', ScrapeJobViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', dashboard_stats, name='dashboard-stats'),
]
