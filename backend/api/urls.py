"""URL routing for the VantagePoint API."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CompanyViewSet, DataPointViewSet, PatternViewSet,
    InsightViewSet, ScrapeJobViewSet, SignalViewSet,
    CompoundSignalViewSet, PricingSnapshotViewSet,
    BattlecardViewSet, DeadReckoningViewSet,
    dashboard_stats, timeline_overlay, data_quality,
)

router = DefaultRouter()
router.register(r'companies', CompanyViewSet)
router.register(r'datapoints', DataPointViewSet)
router.register(r'patterns', PatternViewSet)
router.register(r'insights', InsightViewSet)
router.register(r'scrape-jobs', ScrapeJobViewSet)
router.register(r'signals', SignalViewSet)
router.register(r'compound-signals', CompoundSignalViewSet)
router.register(r'pricing-snapshots', PricingSnapshotViewSet)
router.register(r'battlecards', BattlecardViewSet)
router.register(r'dead-reckonings', DeadReckoningViewSet)

from .auth import session

urlpatterns = [
    path('session/', session),
    path('data-quality/', data_quality),
    path('', include(router.urls)),
    path('dashboard/', dashboard_stats, name='dashboard-stats'),
    path('timeline-overlay/', timeline_overlay, name='timeline-overlay'),
]
