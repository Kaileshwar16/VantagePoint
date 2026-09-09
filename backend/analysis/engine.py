"""
Rule-based analysis engine for detecting competitor patterns and generating insights.
Enhanced with cross-competitor analysis, market context, and actionable recommendations.
"""
import logging
from collections import Counter, defaultdict
from datetime import timedelta

from django.db.models import Count, Q, Avg
from django.utils import timezone

from api.models import Company, DataPoint, Pattern, Insight

logger = logging.getLogger(__name__)


class CompetitorAnalyzer:
    """Analyzes competitor data to detect patterns and generate insights."""

    def __init__(self, company_id):
        self.company = Company.objects.get(id=company_id)
        self.data_points = DataPoint.objects.filter(company=self.company, is_verified=True).exclude(source_url='')
        self.all_companies = Company.objects.exclude(id=company_id)

    def run_full_analysis(self):
        """Run complete analysis pipeline."""
        patterns = []
        patterns.extend(self.detect_activity_trends())
        patterns.extend(self.detect_category_shifts())
        patterns.extend(self.detect_sentiment_changes())
        patterns.extend(self.detect_hiring_surges())
        patterns.extend(self.detect_product_velocity())
        patterns.extend(self.detect_funding_signals())
        patterns.extend(self.detect_partnership_pattern())
        patterns.extend(self.detect_market_expansion())

        insights = self.generate_insights(patterns)

        # Also generate cross-competitor insights
        cross_insights = self.generate_cross_competitor_insights()
        insights.extend(cross_insights)

        return {'patterns': len(patterns), 'insights': len(insights)}

    def detect_activity_trends(self):
        now = timezone.now()
        patterns = []
        recent_30 = self.data_points.filter(published_at__gte=now - timedelta(days=30)).count()
        prev_30 = self.data_points.filter(published_at__gte=now - timedelta(days=60), published_at__lt=now - timedelta(days=30)).count()

        if prev_30 > 0:
            change_pct = ((recent_30 - prev_30) / prev_30) * 100
        elif recent_30 > 0:
            change_pct = 100
        else:
            return patterns

        if abs(change_pct) > 30:
            direction = 'increasing' if change_pct > 0 else 'decreasing'
            pattern = Pattern.objects.create(
                company=self.company,
                name=f'Activity {direction.title()} ({abs(change_pct):.0f}%)',
                description=f'News volume for {self.company.name} has {direction} by {abs(change_pct):.0f}% over the last 30 days (from {prev_30} to {recent_30} signals). In competitive intelligence, sharp activity changes often precede major strategic moves.',
                pattern_type='trend',
                confidence=min(0.9, 0.5 + abs(change_pct) / 200),
                metadata={'change_pct': change_pct, 'recent': recent_30, 'previous': prev_30},
            )
            patterns.append(pattern)
        return patterns

    def detect_category_shifts(self):
        now = timezone.now()
        patterns = []
        recent = dict(self.data_points.filter(published_at__gte=now - timedelta(days=30)).values_list('category').annotate(count=Count('id')).values_list('category', 'count'))
        previous = dict(self.data_points.filter(published_at__gte=now - timedelta(days=90), published_at__lt=now - timedelta(days=30)).values_list('category').annotate(count=Count('id')).values_list('category', 'count'))

        for category, count in recent.items():
            prev_count = previous.get(category, 0)
            if count >= 3 and (prev_count == 0 or count / max(prev_count, 1) >= 2):
                cat_label = category.replace("_", " ").title()
                pattern = Pattern.objects.create(
                    company=self.company,
                    name=f'Surge in {cat_label} Activity',
                    description=f'{self.company.name} generated {count} {category.replace("_", " ")} signals recently vs. {prev_count} previously — a {("new focus area" if prev_count == 0 else f"{count/max(prev_count,1):.0f}x increase")}. This category shift suggests a deliberate strategic pivot.',
                    pattern_type='strategy_shift',
                    confidence=min(0.85, 0.5 + count / 20),
                    metadata={'category': category, 'recent': count, 'previous': prev_count},
                )
                patterns.append(pattern)
        return patterns

    def detect_sentiment_changes(self):
        now = timezone.now()
        patterns = []
        recent_sentiment = dict(self.data_points.filter(published_at__gte=now - timedelta(days=30)).values_list('sentiment').annotate(count=Count('id')).values_list('sentiment', 'count'))
        total = sum(recent_sentiment.values())
        if total < 3:
            return patterns

        neg_ratio = recent_sentiment.get('negative', 0) / total
        pos_ratio = recent_sentiment.get('positive', 0) / total

        if neg_ratio > 0.4:
            pattern = Pattern.objects.create(
                company=self.company, name='Negative Sentiment Surge',
                description=f'{neg_ratio*100:.0f}% of recent coverage about {self.company.name} is negative ({recent_sentiment.get("negative",0)} of {total} articles). Interpretation requires source review; no business outcome has been established.',
                pattern_type='anomaly', confidence=min(0.85, neg_ratio),
                metadata={'negative_ratio': neg_ratio, 'positive_ratio': pos_ratio, 'total': total},
            )
            patterns.append(pattern)
        elif pos_ratio > 0.5:
            pattern = Pattern.objects.create(
                company=self.company, name='Positive Momentum',
                description=f'{pos_ratio*100:.0f}% of recent coverage is positive ({recent_sentiment.get("positive",0)} of {total} articles). Interpretation requires source review; no business outcome has been established.',
                pattern_type='trend', confidence=min(0.85, pos_ratio),
                metadata={'positive_ratio': pos_ratio, 'negative_ratio': neg_ratio, 'total': total},
            )
            patterns.append(pattern)
        return patterns

    def detect_hiring_surges(self):
        patterns = []
        now = timezone.now()
        hiring_count = self.data_points.filter(category='hiring', published_at__gte=now - timedelta(days=30)).count()
        if hiring_count >= 2:
            # Check what kind of hiring
            hiring_dps = self.data_points.filter(category='hiring', published_at__gte=now - timedelta(days=30))
            texts = ' '.join([dp.title + ' ' + dp.content for dp in hiring_dps]).lower()
            focus_areas = []
            if any(w in texts for w in ['engineer', 'developer', 'ai', 'ml', 'data']): focus_areas.append('engineering/AI')
            if any(w in texts for w in ['sales', 'account', 'revenue']): focus_areas.append('sales')
            if any(w in texts for w in ['marketing', 'growth', 'brand']): focus_areas.append('marketing')
            focus_str = f' Hiring appears focused on: {", ".join(focus_areas)}.' if focus_areas else ''

            pattern = Pattern.objects.create(
                company=self.company, name='Hiring Surge Detected',
                description=f'{self.company.name} has {hiring_count} hiring signals in 30 days.{focus_str} Interpretation requires source review; no business outcome has been established.',
                pattern_type='trend', confidence=min(0.8, 0.4 + hiring_count / 15),
                metadata={'hiring_signals': hiring_count, 'focus_areas': focus_areas},
            )
            patterns.append(pattern)
        return patterns

    def detect_product_velocity(self):
        patterns = []
        now = timezone.now()
        product_count = self.data_points.filter(category__in=['product_launch', 'technology'], published_at__gte=now - timedelta(days=60)).count()
        if product_count >= 3:
            pattern = Pattern.objects.create(
                company=self.company, name='High Product Velocity',
                description=f'{self.company.name} made {product_count} product/tech announcements in 60 days. For context, the average competitor makes 1-2 per quarter. This pace suggests a well-funded, execution-focused team.',
                pattern_type='trend', confidence=min(0.85, 0.5 + product_count / 20),
                metadata={'product_signals': product_count},
            )
            patterns.append(pattern)
        return patterns

    def detect_funding_signals(self):
        patterns = []
        now = timezone.now()
        funding_count = self.data_points.filter(category='funding', published_at__gte=now - timedelta(days=60)).count()
        if funding_count >= 1:
            funding_dps = self.data_points.filter(category='funding', published_at__gte=now - timedelta(days=60))
            amounts = []
            for dp in funding_dps:
                text = (dp.title + ' ' + dp.content).lower()
                for word in text.split():
                    if '$' in word or 'm' in word or 'b' in word:
                        amounts.append(word)

            pattern = Pattern.objects.create(
                company=self.company, name='Recent Funding Activity',
                description=f'{self.company.name} has {funding_count} funding-related signal(s). Interpretation requires source review; no business outcome has been established.',
                pattern_type='trend', confidence=0.8,
                metadata={'funding_signals': funding_count},
            )
            patterns.append(pattern)
        return patterns

    def detect_partnership_pattern(self):
        patterns = []
        now = timezone.now()
        partner_count = self.data_points.filter(category='partnership', published_at__gte=now - timedelta(days=60)).count()
        if partner_count >= 2:
            pattern = Pattern.objects.create(
                company=self.company, name='Partnership Acceleration',
                description=f'{self.company.name} announced {partner_count} partnerships in 60 days. Multiple partnerships in a short period typically indicate a platform strategy — they may be building an ecosystem that increases switching costs for customers.',
                pattern_type='strategy_shift', confidence=min(0.8, 0.5 + partner_count / 10),
                metadata={'partnership_signals': partner_count},
            )
            patterns.append(pattern)
        return patterns

    def detect_market_expansion(self):
        patterns = []
        now = timezone.now()
        expansion_count = self.data_points.filter(category='expansion', published_at__gte=now - timedelta(days=60)).count()
        if expansion_count >= 1:
            exp_dps = self.data_points.filter(category='expansion', published_at__gte=now - timedelta(days=60))
            regions = set()
            for dp in exp_dps:
                text = (dp.title + ' ' + dp.content).lower()
                if any(w in text for w in ['europe', 'london', 'berlin', 'gdpr']): regions.add('Europe')
                if any(w in text for w in ['asia', 'japan', 'india', 'singapore', 'apac']): regions.add('Asia-Pacific')
                if any(w in text for w in ['latin america', 'brazil', 'mexico']): regions.add('Latin America')

            region_str = f' Target regions: {", ".join(regions)}.' if regions else ''
            pattern = Pattern.objects.create(
                company=self.company, name='Geographic Expansion',
                description=f'{self.company.name} has {expansion_count} market expansion signal(s).{region_str} Geographic expansion is a lagging indicator of product-market fit — they\'re confident enough in their core market to invest internationally.',
                pattern_type='strategy_shift', confidence=min(0.8, 0.5 + expansion_count / 5),
                metadata={'expansion_signals': expansion_count, 'target_regions': list(regions)},
            )
            patterns.append(pattern)
        return patterns

    def generate_insights(self, patterns):
        insights = []
        for pattern in patterns:
            insight_data = self._pattern_to_insight(pattern)
            if insight_data:
                insight = Insight.objects.create(company=self.company, **insight_data)
                insight.related_patterns.add(pattern)
                insights.append(insight)
        return insights

    def _pattern_to_insight(self, pattern):
        return {
            'title': f'Review: {pattern.name}',
            'description': pattern.description + ' This is a rule-based observation, not a forecast of business outcomes.',
            'recommendation': 'Review the underlying source records, distinguish repeated reporting from independent events, and confirm relevance before acting.',
            'priority': 'medium', 'predicted_timeline': 'Unknown',
            'probability': pattern.confidence,
            'metadata': {'methodology': 'review-v1', 'score_type': 'uncalibrated_heuristic'},
        }

    def generate_cross_competitor_insights(self):
        """Generate insights by comparing this company against all other tracked competitors."""
        insights = []
        now = timezone.now()

        # Compare data point volume across all companies
        company_volumes = {}
        for comp in Company.objects.all():
            vol = DataPoint.objects.filter(company=comp, is_verified=True, published_at__gte=now - timedelta(days=30)).count()
            company_volumes[comp.name] = vol

        if len(company_volumes) >= 2:
            sorted_vols = sorted(company_volumes.items(), key=lambda x: x[1], reverse=True)
            my_rank = next((i for i, (n, _) in enumerate(sorted_vols) if n == self.company.name), -1)

            if my_rank == 0 and sorted_vols[0][1] > 0:
                insight = Insight.objects.create(
                    company=self.company,
                    title=f'{self.company.name} Has the Most Reviewed Reports in This Workspace',
                    description=f'With {sorted_vols[0][1]} signals in 30 days, {self.company.name} leads all tracked competitors in activity volume. The runner-up is {sorted_vols[1][0]} with {sorted_vols[1][1]} signals. Collection coverage varies by company; report volume does not measure market aggression.',
                    recommendation='Review collection coverage and original reports before comparing companies.',
                    priority='medium', predicted_timeline='Unknown', probability=0.5,
                    metadata={'methodology': 'review-v1', 'score_type': 'uncalibrated_heuristic'},
                )
                insights.append(insight)

        return insights


def analyze_company(company_id):
    analyzer = CompetitorAnalyzer(company_id)
    return analyzer.run_full_analysis()


def analyze_all_companies():
    results = {}
    for company in Company.objects.filter(is_competitor=True):
        try:
            results[company.name] = analyze_company(company.id)
        except Exception as e:
            logger.error(f"Analysis failed for {company.name}: {e}")
            results[company.name] = {'error': 'Analysis failed; check server logs.'}
    return results
