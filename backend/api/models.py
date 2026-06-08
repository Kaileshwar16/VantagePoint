"""
Core models for VantagePoint competitive intelligence platform.
"""
from django.db import models
from django.contrib.auth.models import User


class Company(models.Model):
    """A company being tracked for competitive intelligence."""
    
    INDUSTRY_CHOICES = [
        ('tech', 'Technology'),
        ('finance', 'Finance'),
        ('healthcare', 'Healthcare'),
        ('retail', 'Retail'),
        ('manufacturing', 'Manufacturing'),
        ('energy', 'Energy'),
        ('media', 'Media & Entertainment'),
        ('education', 'Education'),
        ('real_estate', 'Real Estate'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=255)
    domain = models.URLField(max_length=500, blank=True)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES, default='tech')
    description = models.TextField(blank=True)
    logo_url = models.URLField(max_length=500, blank=True)
    founded_year = models.IntegerField(null=True, blank=True)
    headquarters = models.CharField(max_length=255, blank=True)
    employee_count = models.CharField(max_length=50, blank=True)
    revenue_range = models.CharField(max_length=100, blank=True)
    is_competitor = models.BooleanField(default=True)
    tracked_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tracked_companies', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'companies'
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name


class CompetitorRelationship(models.Model):
    """Defines which companies are competitors of each other."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='competitor_relationships')
    competitor = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='competing_with')
    overlap_score = models.FloatField(default=0.0, help_text='0-100 score of competitive overlap')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('company', 'competitor')
    
    def __str__(self):
        return f"{self.company.name} vs {self.competitor.name}"


class DataPoint(models.Model):
    """A single piece of intelligence data scraped about a company."""
    
    CATEGORY_CHOICES = [
        ('product_launch', 'Product Launch'),
        ('pricing_change', 'Pricing Change'),
        ('hiring', 'Hiring Activity'),
        ('partnership', 'Partnership'),
        ('funding', 'Funding Round'),
        ('acquisition', 'Acquisition'),
        ('expansion', 'Market Expansion'),
        ('leadership', 'Leadership Change'),
        ('technology', 'Technology Adoption'),
        ('marketing', 'Marketing Campaign'),
        ('legal', 'Legal/Regulatory'),
        ('news', 'General News'),
    ]
    
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]
    
    IMPACT_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='data_points')
    title = models.CharField(max_length=500)
    content = models.TextField()
    summary = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='news')
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, default='neutral')
    impact = models.CharField(max_length=20, choices=IMPACT_CHOICES, default='medium')
    source_url = models.URLField(max_length=1000, blank=True)
    source_name = models.CharField(max_length=255, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    confidence_score = models.FloatField(default=0.5, help_text='0-1 confidence in data accuracy')
    is_verified = models.BooleanField(default=False)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['company', 'category']),
            models.Index(fields=['company', 'published_at']),
        ]
    
    def __str__(self):
        return f"{self.company.name}: {self.title[:80]}"


class Pattern(models.Model):
    """A detected pattern in competitor behavior."""
    
    PATTERN_TYPE_CHOICES = [
        ('trend', 'Trend'),
        ('cycle', 'Cycle'),
        ('anomaly', 'Anomaly'),
        ('correlation', 'Correlation'),
        ('strategy_shift', 'Strategy Shift'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='patterns')
    name = models.CharField(max_length=255)
    description = models.TextField()
    pattern_type = models.CharField(max_length=50, choices=PATTERN_TYPE_CHOICES, default='trend')
    confidence = models.FloatField(default=0.5, help_text='0-1 confidence score')
    supporting_data = models.ManyToManyField(DataPoint, related_name='patterns', blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    detected_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-detected_at']
    
    def __str__(self):
        return f"{self.company.name}: {self.name}"


class Insight(models.Model):
    """Strategic insight / predicted next move based on patterns."""
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('acted_on', 'Acted On'),
        ('dismissed', 'Dismissed'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='insights')
    title = models.CharField(max_length=500)
    description = models.TextField()
    recommendation = models.TextField(blank=True, help_text='Suggested action to take')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    related_patterns = models.ManyToManyField(Pattern, related_name='insights', blank=True)
    predicted_timeline = models.CharField(max_length=100, blank=True, help_text='e.g., "Within 30 days"')
    probability = models.FloatField(default=0.5, help_text='0-1 probability of prediction')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company.name}: {self.title[:80]}"


class ScrapeJob(models.Model):
    """Tracks scraping jobs for monitoring and retry."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='scrape_jobs')
    spider_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    items_scraped = models.IntegerField(default=0)
    errors = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Scrape: {self.company.name} ({self.spider_name}) - {self.status}"
