"""
Core models for VantagePoint competitive intelligence platform.
Includes signal capture, compound signals, battlecards, and dead reckoning.
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
        ('patent', 'Patent Filing'),
        ('earnings', 'Earnings/Financial'),
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


class Signal(models.Model):
    """
    A structured signal captured from external sources.
    Types: job_posting, patent_filing, pricing_change, earnings_keyword, leadership_change
    """
    
    SIGNAL_TYPE_CHOICES = [
        ('job_posting', 'Job Posting'),
        ('patent_filing', 'Patent Filing'),
        ('pricing_change', 'Pricing Page Change'),
        ('earnings_keyword', 'Earnings Call Keyword'),
        ('leadership_change', 'Leadership Change'),
        ('funding_event', 'Funding Event'),
        ('product_signal', 'Product Signal'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='signals')
    signal_type = models.CharField(max_length=50, choices=SIGNAL_TYPE_CHOICES)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    source_url = models.URLField(max_length=1000, blank=True)
    
    # For job postings
    role_type = models.CharField(max_length=100, blank=True, help_text='e.g., Engineering, Sales, Marketing')
    seniority_level = models.CharField(max_length=50, blank=True, help_text='e.g., VP, Director, Senior, Entry')
    department = models.CharField(max_length=100, blank=True)
    
    # For patent filings
    patent_category = models.CharField(max_length=200, blank=True)
    patent_id = models.CharField(max_length=100, blank=True)
    
    # For earnings keywords
    keyword = models.CharField(max_length=100, blank=True)
    keyword_count = models.IntegerField(default=0)
    quarter = models.CharField(max_length=10, blank=True, help_text='e.g., Q1 2025')
    
    # For pricing changes
    diff_summary = models.TextField(blank=True)
    old_snapshot = models.TextField(blank=True)
    new_snapshot = models.TextField(blank=True)
    
    # Scoring
    strength = models.FloatField(default=0.5, help_text='0-1 signal strength')
    velocity = models.FloatField(default=0.0, help_text='Rate of change')
    anomaly_score = models.FloatField(default=0.0, help_text='How far from baseline')
    
    metadata = models.JSONField(default=dict, blank=True)
    captured_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-captured_at']
        indexes = [
            models.Index(fields=['company', 'signal_type']),
            models.Index(fields=['company', 'captured_at']),
        ]
    
    def __str__(self):
        return f"[{self.signal_type}] {self.company.name}: {self.title[:60]}"


class CompoundSignal(models.Model):
    """
    Multiple weak signals that co-occur temporally to form a strong compound signal.
    E.g., VP of Sales hire + pricing page change + new enterprise tier review.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='compound_signals')
    title = models.CharField(max_length=500)
    hypothesis = models.TextField(help_text='Strategic intent inference in plain language')
    contributing_signals = models.ManyToManyField(Signal, related_name='compound_signals')
    contributing_datapoints = models.ManyToManyField(DataPoint, related_name='compound_signals', blank=True)
    signal_count = models.IntegerField(default=0)
    confidence = models.FloatField(default=0.5, help_text='Confidence based on independent signal count')
    severity = models.CharField(max_length=20, choices=[('low','Low'),('medium','Medium'),('high','High'),('critical','Critical')], default='medium')
    time_window_days = models.IntegerField(default=30, help_text='Window within which signals co-occurred')
    detected_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-detected_at']
    
    def __str__(self):
        return f"Compound: {self.title[:60]}"


class PricingSnapshot(models.Model):
    """Weekly snapshot of a competitor's pricing page for diff tracking."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='pricing_snapshots')
    url = models.URLField(max_length=1000)
    content_text = models.TextField(help_text='Cleaned text of pricing page')
    content_html = models.TextField(blank=True, help_text='Raw HTML')
    content_hash = models.CharField(max_length=64, help_text='SHA256 hash for change detection')
    has_changed = models.BooleanField(default=False)
    diff_from_previous = models.TextField(blank=True, help_text='Diff from previous snapshot')
    plan_names = models.JSONField(default=list, blank=True)
    prices = models.JSONField(default=list, blank=True)
    captured_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-captured_at']
    
    def __str__(self):
        return f"Pricing: {self.company.name} ({self.captured_at.strftime('%Y-%m-%d')})"


class Battlecard(models.Model):
    """Auto-updating competitive battlecard."""
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='battlecard')
    
    # Positioning
    strengths = models.JSONField(default=list)
    weaknesses = models.JSONField(default=list)
    recent_moves = models.JSONField(default=list, help_text='Last 5 strategic moves')
    
    # Competitive positioning
    pricing_position = models.CharField(max_length=50, blank=True, help_text='premium/mid/budget')
    target_market = models.CharField(max_length=200, blank=True)
    key_differentiators = models.JSONField(default=list)
    
    # Sales intelligence
    win_themes = models.JSONField(default=list, help_text='Why customers choose them')
    loss_themes = models.JSONField(default=list, help_text='Why customers leave them')
    objection_handlers = models.JSONField(default=list)
    
    # Auto-updated fields
    current_trajectory = models.CharField(max_length=50, blank=True, help_text='growing/stable/declining')
    threat_assessment = models.TextField(blank=True)
    signal_summary = models.TextField(blank=True, help_text='Auto-generated from latest signals')
    
    last_updated = models.DateTimeField(auto_now=True)
    auto_update_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-last_updated']
    
    def __str__(self):
        return f"Battlecard: {self.company.name}"


class DeadReckoning(models.Model):
    """
    Forward projection: given current position + trajectory + resources,
    project where a competitor will be in N months.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='dead_reckonings')
    
    # Current state (inputs)
    current_headcount = models.IntegerField(default=0)
    current_arr = models.FloatField(default=0, help_text='Estimated ARR in millions')
    current_market_share = models.FloatField(default=0, help_text='Estimated market share %')
    current_product_count = models.IntegerField(default=0)
    current_geo_markets = models.IntegerField(default=1)
    
    # Observed velocity (calculated from signals)
    hiring_velocity = models.FloatField(default=0, help_text='Jobs per month')
    product_velocity = models.FloatField(default=0, help_text='Launches per quarter')
    funding_total = models.FloatField(default=0, help_text='Total known funding in millions')
    expansion_velocity = models.FloatField(default=0, help_text='New markets per year')
    
    # Projections (outputs) — 6 and 12 month
    projected_headcount_6m = models.IntegerField(default=0)
    projected_headcount_12m = models.IntegerField(default=0)
    projected_arr_6m = models.FloatField(default=0)
    projected_arr_12m = models.FloatField(default=0)
    projected_products_6m = models.IntegerField(default=0)
    projected_products_12m = models.IntegerField(default=0)
    projected_markets_6m = models.IntegerField(default=0)
    projected_markets_12m = models.IntegerField(default=0)
    
    # Confidence & narrative
    confidence = models.FloatField(default=0.5)
    projection_narrative = models.TextField(blank=True, help_text='Plain language projection')
    key_assumptions = models.JSONField(default=list)
    risk_factors = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Dead Reckoning: {self.company.name} ({self.created_at.strftime('%Y-%m-%d')})"


class Pattern(models.Model):
    """A detected pattern in competitor behavior."""
    
    PATTERN_TYPE_CHOICES = [
        ('trend', 'Trend'),
        ('cycle', 'Cycle'),
        ('anomaly', 'Anomaly'),
        ('correlation', 'Correlation'),
        ('strategy_shift', 'Strategy Shift'),
        ('velocity_alert', 'Velocity Alert'),
        ('compound', 'Compound Signal'),
        ('pre_launch', 'Pre-Launch Pattern'),
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
