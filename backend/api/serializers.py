"""Serializers for the VantagePoint API."""
from rest_framework import serializers
from .models import (Company, CompetitorRelationship, DataPoint, Pattern, Insight,
                     ScrapeJob, Signal, CompoundSignal, PricingSnapshot, Battlecard, DeadReckoning)


class CompanySerializer(serializers.ModelSerializer):
    data_points_count = serializers.SerializerMethodField()
    patterns_count = serializers.SerializerMethodField()
    insights_count = serializers.SerializerMethodField()
    signals_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = '__all__'

    def validate_domain(self, value):
        if value:
            from scraping.http import resolve_public_url
            try:
                resolve_public_url(value)
            except ValueError as exc:
                raise serializers.ValidationError(str(exc)) from exc
        return value

    def get_data_points_count(self, obj):
        return obj.data_points.count()
    def get_patterns_count(self, obj):
        return obj.patterns.count()
    def get_insights_count(self, obj):
        return obj.insights.count()
    def get_signals_count(self, obj):
        return obj.signals.count()


class CompanyListSerializer(serializers.ModelSerializer):
    data_points_count = serializers.SerializerMethodField()
    latest_activity = serializers.SerializerMethodField()
    threat_level = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = ['id', 'name', 'domain', 'industry', 'logo_url', 'headquarters',
                  'employee_count', 'is_competitor', 'data_points_count',
                  'latest_activity', 'threat_level', 'created_at', 'updated_at']

    def get_data_points_count(self, obj):
        return obj.data_points.count()

    def get_latest_activity(self, obj):
        latest = obj.data_points.first()
        if latest:
            return {'title': latest.title, 'category': latest.category,
                    'date': latest.published_at or latest.created_at}
        return None

    def get_threat_level(self, obj):
        high_impact = obj.data_points.filter(impact__in=['high', 'critical']).count()
        if high_impact >= 5: return 'critical'
        elif high_impact >= 3: return 'high'
        elif high_impact >= 1: return 'medium'
        return 'low'


class CompetitorRelationshipSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    class Meta:
        model = CompetitorRelationship
        fields = '__all__'


class DataPointSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    class Meta:
        model = DataPoint
        fields = '__all__'

class DataPointCreateSerializer(serializers.ModelSerializer):
    confidence_score = serializers.FloatField(min_value=0, max_value=1, required=False)
    class Meta:
        model = DataPoint
        fields = '__all__'

    def validate(self, attrs):
        verified = attrs.get('is_verified', getattr(self.instance, 'is_verified', False))
        source = attrs.get('source_url', getattr(self.instance, 'source_url', ''))
        if verified and not source:
            raise serializers.ValidationError({'source_url': 'A verified record requires a source URL.'})
        if verified:
            from django.utils import timezone
            published = attrs.get('published_at', getattr(self.instance, 'published_at', None))
            if published and published > timezone.now():
                raise serializers.ValidationError({'published_at': 'Future publication dates cannot be verified.'})
        return attrs


class PatternSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    supporting_data_count = serializers.SerializerMethodField()
    class Meta:
        model = Pattern
        fields = '__all__'
    def get_supporting_data_count(self, obj):
        return obj.supporting_data.count()


class InsightSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    related_patterns_count = serializers.SerializerMethodField()
    class Meta:
        model = Insight
        fields = '__all__'
    def get_related_patterns_count(self, obj):
        return obj.related_patterns.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['score_type'] = 'uncalibrated_heuristic'
        if instance.metadata.get('methodology') not in ('review-v1', 'compound-review-v1'):
            data['title'] = 'Legacy analysis — source review required'
            data['description'] = 'Legacy analysis withheld because its factual claims and benchmark statistics were not verified. Run analysis again after reviewing source records.'
            data['recommendation'] = 'Review original evidence and regenerate this analysis.'
            data['predicted_timeline'] = 'Unknown'
        return data


class ScrapeJobSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    class Meta:
        model = ScrapeJob
        fields = '__all__'


class SignalSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    class Meta:
        model = Signal
        fields = '__all__'


class CompoundSignalSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    contributing_signals = SignalSerializer(many=True, read_only=True)
    class Meta:
        model = CompoundSignal
        fields = '__all__'


class PricingSnapshotSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    class Meta:
        model = PricingSnapshot
        fields = '__all__'


class BattlecardSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    class Meta:
        model = Battlecard
        fields = '__all__'


class DeadReckoningSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    class Meta:
        model = DeadReckoning
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key in data:
            if key.startswith(('current_', 'projected_')) or key in ('funding_total', 'confidence'):
                data[key] = None
        data['forecast_status'] = 'unavailable'
        if 'methodology:observations-v1' not in instance.key_assumptions:
            data['projection_narrative'] = 'Legacy projection withheld: its inputs and methodology were not verified. Generate a new observation report.'
            data['key_assumptions'] = []
            data['risk_factors'] = ['Legacy estimates must not be used for business decisions.']
            for key in ('hiring_velocity', 'product_velocity', 'expansion_velocity'):
                data[key] = None
        return data


class DashboardStatsSerializer(serializers.Serializer):
    total_companies = serializers.IntegerField()
    total_data_points = serializers.IntegerField()
    total_patterns = serializers.IntegerField()
    total_insights = serializers.IntegerField()
    new_insights_count = serializers.IntegerField()
    recent_data_points = DataPointSerializer(many=True)
    top_insights = InsightSerializer(many=True)
    category_distribution = serializers.DictField()
    sentiment_distribution = serializers.DictField()
    activity_timeline = serializers.ListField()
