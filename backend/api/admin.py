"""Admin configuration for VantagePoint models."""
from django.contrib import admin
from .models import Company, CompetitorRelationship, DataPoint, Pattern, Insight, ScrapeJob


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'industry', 'domain', 'is_competitor', 'created_at']
    list_filter = ['industry', 'is_competitor']
    search_fields = ['name', 'description']


@admin.register(CompetitorRelationship)
class CompetitorRelationshipAdmin(admin.ModelAdmin):
    list_display = ['company', 'competitor', 'overlap_score']


@admin.register(DataPoint)
class DataPointAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'category', 'sentiment', 'impact', 'created_at']
    list_filter = ['category', 'sentiment', 'impact', 'is_verified']
    search_fields = ['title', 'content']


@admin.register(Pattern)
class PatternAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'pattern_type', 'confidence', 'is_active']
    list_filter = ['pattern_type', 'is_active']


@admin.register(Insight)
class InsightAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'priority', 'status', 'probability', 'created_at']
    list_filter = ['priority', 'status']


@admin.register(ScrapeJob)
class ScrapeJobAdmin(admin.ModelAdmin):
    list_display = ['company', 'spider_name', 'status', 'items_scraped', 'created_at']
    list_filter = ['status', 'spider_name']
