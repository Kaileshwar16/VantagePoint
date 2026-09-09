"""Views for the VantagePoint API — includes signal capture, advanced analysis, battlecards, dead reckoning."""
from datetime import timedelta
from django.db.models import Count, Q, Case, When, IntegerField
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import (Company, CompetitorRelationship, DataPoint, Pattern, Insight,
                     ScrapeJob, Signal, CompoundSignal, PricingSnapshot, Battlecard, DeadReckoning)
from .serializers import (
    CompanySerializer, CompanyListSerializer, CompetitorRelationshipSerializer,
    DataPointSerializer, DataPointCreateSerializer, PatternSerializer,
    InsightSerializer, ScrapeJobSerializer, SignalSerializer,
    CompoundSignalSerializer, PricingSnapshotSerializer,
    BattlecardSerializer, DeadReckoningSerializer,
)


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    filterset_fields = ['industry', 'is_competitor']
    search_fields = ['name', 'description', 'headquarters']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return CompanyListSerializer
        return CompanySerializer

    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        company = self.get_object()
        from rest_framework.exceptions import ValidationError
        try:
            days = int(request.query_params.get('days', 90))
            if not 1 <= days <= 730:
                raise ValueError
        except (ValueError, TypeError):
            raise ValidationError({'days': 'Use an integer from 1 to 730.'})
        since = timezone.now() - timedelta(days=days)
        data_points = company.data_points.filter(created_at__gte=since).values('category').annotate(count=Count('id')).order_by('category')
        timeline_data = company.data_points.filter(created_at__gte=since).order_by('-created_at')[:50]
        return Response({
            'category_breakdown': list(data_points),
            'timeline': DataPointSerializer(timeline_data, many=True).data,
        })

    @action(detail=True, methods=['get'])
    def competitors(self, request, pk=None):
        company = self.get_object()
        relationships = CompetitorRelationship.objects.filter(company=company)
        return Response(CompetitorRelationshipSerializer(relationships, many=True).data)

    @action(detail=True, methods=['post'])
    def scrape(self, request, pk=None):
        company = self.get_object()
        from scraping.jobs import execute_scrape
        return execute_scrape(company, request.data.get('spider', 'news'))

    @action(detail=True, methods=['post'], url_path='capture-signals')
    def capture_signals(self, request, pk=None):
        """Run all signal capture modules for a company."""
        company = self.get_object()
        from scraping.signal_capture import capture_all_signals
        results = capture_all_signals(company.id)
        return Response({'status': 'partial_failure' if results.get('errors') else 'completed', 'results': results}, status=502 if results.get('errors') else 200)

    @action(detail=True, methods=['post'], url_path='advanced-analysis')
    def advanced_analysis(self, request, pk=None):
        """Run advanced analysis (velocity, anomaly, compound, battlecard, dead reckoning)."""
        company = self.get_object()
        from analysis.advanced import run_advanced_analysis
        results = run_advanced_analysis(company.id)
        return Response({'status': 'partial_failure' if results.get('errors') else 'completed', 'results': results}, status=502 if results.get('errors') else 200)


class DataPointViewSet(viewsets.ModelViewSet):
    queryset = DataPoint.objects.select_related('company').all()
    filterset_fields = ['company', 'category', 'sentiment', 'impact', 'is_verified']
    search_fields = ['title', 'content', 'source_name']
    ordering_fields = ['published_at', 'created_at', 'impact']
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DataPointCreateSerializer
        return DataPointSerializer

    def perform_update(self, serializer):
        changed = any(key in serializer.validated_data for key in ('title', 'content', 'source_url', 'published_at'))
        verified = serializer.validated_data.get('is_verified', False)
        raw = dict(serializer.instance.raw_data or {})
        if 'is_verified' in serializer.validated_data or changed:
            raw['review'] = {'reviewer_id': self.request.user.id, 'reviewed_at': timezone.now().isoformat(), 'verified': verified}
            serializer.save(is_verified=verified, raw_data=raw)
        else:
            serializer.save()


class PatternViewSet(viewsets.ModelViewSet):
    queryset = Pattern.objects.select_related('company').all()
    serializer_class = PatternSerializer
    filterset_fields = ['company', 'pattern_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['detected_at', 'confidence']


class InsightViewSet(viewsets.ModelViewSet):
    queryset = Insight.objects.select_related('company').all()
    serializer_class = InsightSerializer
    filterset_fields = ['company', 'priority', 'status']
    search_fields = ['title', 'description', 'recommendation']
    ordering_fields = ['created_at', 'priority', 'probability']


class ScrapeJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ScrapeJob.objects.select_related('company').all()
    serializer_class = ScrapeJobSerializer
    filterset_fields = ['company', 'status', 'spider_name']


class SignalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Signal.objects.select_related('company').all()
    serializer_class = SignalSerializer
    filterset_fields = ['company', 'signal_type']
    search_fields = ['title', 'description', 'role_type', 'keyword']
    ordering_fields = ['captured_at', 'strength', 'velocity', 'anomaly_score']


class CompoundSignalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CompoundSignal.objects.select_related('company').all()
    serializer_class = CompoundSignalSerializer
    filterset_fields = ['company', 'severity', 'is_active']
    ordering_fields = ['detected_at', 'confidence']


class PricingSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PricingSnapshot.objects.select_related('company').all()
    serializer_class = PricingSnapshotSerializer
    filterset_fields = ['company', 'has_changed']


class BattlecardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Battlecard.objects.select_related('company').all()
    serializer_class = BattlecardSerializer
    filterset_fields = ['company']


class DeadReckoningViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeadReckoning.objects.select_related('company').all()
    serializer_class = DeadReckoningSerializer
    filterset_fields = ['company']
    ordering_fields = ['created_at', 'confidence']


@api_view(['GET'])
def dashboard_stats(request):
    now = timezone.now()
    last_30_days = now - timedelta(days=30)
    last_7_days = now - timedelta(days=7)

    category_dist = dict(DataPoint.objects.values_list('category').annotate(count=Count('id')).values_list('category', 'count'))
    sentiment_dist = dict(DataPoint.objects.values_list('sentiment').annotate(count=Count('id')).values_list('sentiment', 'count'))

    activity = []
    for i in range(30):
        day = now - timedelta(days=29 - i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = DataPoint.objects.filter(created_at__gte=day_start, created_at__lt=day_end).count()
        activity.append({'date': day_start.strftime('%Y-%m-%d'), 'count': count})

    impact_dist = dict(DataPoint.objects.values_list('impact').annotate(count=Count('id')).values_list('impact', 'count'))
    company_activity = list(Company.objects.annotate(dp_count=Count('data_points')).order_by('-dp_count').values('id', 'name', 'dp_count')[:10])

    # Signal stats
    signal_dist = dict(Signal.objects.values_list('signal_type').annotate(count=Count('id')).values_list('signal_type', 'count'))
    compound_count = CompoundSignal.objects.filter(is_active=True).count()

    return Response({
        'total_companies': Company.objects.count(),
        'total_data_points': DataPoint.objects.count(),
        'total_patterns': Pattern.objects.count(),
        'total_insights': Insight.objects.count(),
        'total_signals': Signal.objects.count(),
        'new_insights_count': Insight.objects.filter(status='new').count(),
        'compound_signals_active': compound_count,
        'recent_data_points': DataPointSerializer(DataPoint.objects.select_related('company').all()[:10], many=True).data,
        'top_insights': InsightSerializer(Insight.objects.select_related('company').filter(status='new').annotate(priority_rank=Case(When(priority='urgent', then=4), When(priority='high', then=3), When(priority='medium', then=2), default=1, output_field=IntegerField())).order_by('-priority_rank', '-probability')[:5], many=True).data,
        'category_distribution': category_dist,
        'sentiment_distribution': sentiment_dist,
        'impact_distribution': impact_dist,
        'signal_distribution': signal_dist,
        'activity_timeline': activity,
        'company_activity': company_activity,
        'data_points_last_7_days': DataPoint.objects.filter(created_at__gte=last_7_days).count(),
        'data_points_last_30_days': DataPoint.objects.filter(created_at__gte=last_30_days).count(),
    })


@api_view(['POST'])
def timeline_overlay(request):
    """Compare multiple competitors' signal timelines."""
    company_ids = request.data.get('company_ids', [])
    days = request.data.get('days', 180)
    if (not isinstance(company_ids, list) or not 2 <= len(company_ids) <= 10
            or any(type(cid) is not int for cid in company_ids)
            or len(set(company_ids)) != len(company_ids)):
        return Response({'error': 'Provide at least 2 company_ids'}, status=400)
    if type(days) is not int or not 1 <= days <= 730:
        return Response({'error': 'days must be an integer from 1 to 730'}, status=400)
    if Company.objects.filter(id__in=company_ids).count() != len(company_ids):
        return Response({'error': 'One or more companies do not exist'}, status=400)
    from analysis.advanced import get_timeline_overlay
    data = get_timeline_overlay(company_ids, days)
    return Response(data)


@api_view(['GET'])
def data_quality(request):
    """Evidence coverage, not a claim that sourced records are accurate."""
    points = DataPoint.objects.all()
    cutoff = timezone.now() - timedelta(days=90)
    return Response({
        'total_records': points.count(),
        'verified_records': points.filter(is_verified=True).exclude(source_url='').count(),
        'missing_sources': points.filter(source_url='').count(),
        'unknown_publication_dates': points.filter(published_at__isnull=True).count(),
        'older_than_90_days': points.filter(published_at__lt=cutoff).count(),
        'future_publication_dates': points.filter(published_at__gt=timezone.now()).count(),
        'last_collection': ScrapeJob.objects.filter(status='completed').order_by('-completed_at').values_list('completed_at', flat=True).first(),
        'failed_collections': ScrapeJob.objects.filter(status='failed').count(),
        'notice': 'Source links and automated scores do not establish truth. Existing company profiles and legacy records require source review. Analysis scores are uncalibrated heuristics, not probabilities.',
    })
