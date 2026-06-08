"""Serializers for the VantagePoint API."""
from rest_framework import serializers
from .models import Company, CompetitorRelationship, DataPoint, Pattern, Insight, ScrapeJob


class CompanySerializer(serializers.ModelSerializer):
    data_points_count = serializers.SerializerMethodField()
    patterns_count = serializers.SerializerMethodField()
    insights_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = '__all__'
    
    def get_data_points_count(self, obj):
        return obj.data_points.count()
    
    def get_patterns_count(self, obj):
        return obj.patterns.count()
    
    def get_insights_count(self, obj):
        return obj.insights.count()


class CompanyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
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
            return {
                'title': latest.title,
                'category': latest.category,
                'date': latest.published_at or latest.created_at,
            }
        return None
    
    def get_threat_level(self, obj):
        """Calculate threat level based on recent high-impact data points."""
        high_impact = obj.data_points.filter(impact__in=['high', 'critical']).count()
        if high_impact >= 5:
            return 'critical'
        elif high_impact >= 3:
            return 'high'
        elif high_impact >= 1:
            return 'medium'
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
    class Meta:
        model = DataPoint
        fields = '__all__'


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


class ScrapeJobSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = ScrapeJob
        fields = '__all__'


class DashboardStatsSerializer(serializers.Serializer):
    """Dashboard aggregate statistics."""
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
