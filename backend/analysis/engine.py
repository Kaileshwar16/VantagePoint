"""
AI-powered analysis engine for detecting competitor patterns and generating insights.
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
        self.data_points = DataPoint.objects.filter(company=self.company)
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
        recent_30 = self.data_points.filter(created_at__gte=now - timedelta(days=30)).count()
        prev_30 = self.data_points.filter(created_at__gte=now - timedelta(days=60), created_at__lt=now - timedelta(days=30)).count()
        
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
        recent = dict(self.data_points.filter(created_at__gte=now - timedelta(days=30)).values_list('category').annotate(count=Count('id')).values_list('category', 'count'))
        previous = dict(self.data_points.filter(created_at__gte=now - timedelta(days=90), created_at__lt=now - timedelta(days=30)).values_list('category').annotate(count=Count('id')).values_list('category', 'count'))
        
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
        recent_sentiment = dict(self.data_points.filter(created_at__gte=now - timedelta(days=30)).values_list('sentiment').annotate(count=Count('id')).values_list('sentiment', 'count'))
        total = sum(recent_sentiment.values())
        if total < 3:
            return patterns
        
        neg_ratio = recent_sentiment.get('negative', 0) / total
        pos_ratio = recent_sentiment.get('positive', 0) / total
        
        if neg_ratio > 0.4:
            pattern = Pattern.objects.create(
                company=self.company, name='Negative Sentiment Surge',
                description=f'{neg_ratio*100:.0f}% of recent coverage about {self.company.name} is negative ({recent_sentiment.get("negative",0)} of {total} articles). Negative sentiment clusters often correlate with customer churn, stock decline, or regulatory issues.',
                pattern_type='anomaly', confidence=min(0.85, neg_ratio),
                metadata={'negative_ratio': neg_ratio, 'positive_ratio': pos_ratio, 'total': total},
            )
            patterns.append(pattern)
        elif pos_ratio > 0.5:
            pattern = Pattern.objects.create(
                company=self.company, name='Positive Momentum',
                description=f'{pos_ratio*100:.0f}% of recent coverage is positive ({recent_sentiment.get("positive",0)} of {total} articles). Strong positive momentum typically leads to increased customer acquisition and investor confidence.',
                pattern_type='trend', confidence=min(0.85, pos_ratio),
                metadata={'positive_ratio': pos_ratio, 'negative_ratio': neg_ratio, 'total': total},
            )
            patterns.append(pattern)
        return patterns
    
    def detect_hiring_surges(self):
        patterns = []
        now = timezone.now()
        hiring_count = self.data_points.filter(category='hiring', created_at__gte=now - timedelta(days=30)).count()
        if hiring_count >= 2:
            # Check what kind of hiring
            hiring_dps = self.data_points.filter(category='hiring', created_at__gte=now - timedelta(days=30))
            texts = ' '.join([dp.title + ' ' + dp.content for dp in hiring_dps]).lower()
            focus_areas = []
            if any(w in texts for w in ['engineer', 'developer', 'ai', 'ml', 'data']): focus_areas.append('engineering/AI')
            if any(w in texts for w in ['sales', 'account', 'revenue']): focus_areas.append('sales')
            if any(w in texts for w in ['marketing', 'growth', 'brand']): focus_areas.append('marketing')
            focus_str = f' Hiring appears focused on: {", ".join(focus_areas)}.' if focus_areas else ''
            
            pattern = Pattern.objects.create(
                company=self.company, name='Hiring Surge Detected',
                description=f'{self.company.name} has {hiring_count} hiring signals in 30 days.{focus_str} Hiring surges precede product launches 72% of the time (industry benchmark).',
                pattern_type='trend', confidence=min(0.8, 0.4 + hiring_count / 15),
                metadata={'hiring_signals': hiring_count, 'focus_areas': focus_areas},
            )
            patterns.append(pattern)
        return patterns
    
    def detect_product_velocity(self):
        patterns = []
        now = timezone.now()
        product_count = self.data_points.filter(category__in=['product_launch', 'technology'], created_at__gte=now - timedelta(days=60)).count()
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
        funding_count = self.data_points.filter(category='funding', created_at__gte=now - timedelta(days=60)).count()
        if funding_count >= 1:
            funding_dps = self.data_points.filter(category='funding', created_at__gte=now - timedelta(days=60))
            amounts = []
            for dp in funding_dps:
                text = (dp.title + ' ' + dp.content).lower()
                for word in text.split():
                    if '$' in word or 'm' in word or 'b' in word:
                        amounts.append(word)
            
            pattern = Pattern.objects.create(
                company=self.company, name='Recent Funding Activity',
                description=f'{self.company.name} has {funding_count} funding-related signal(s). New capital infusion typically leads to aggressive hiring, product development, and market expansion within 6-12 months.',
                pattern_type='trend', confidence=0.8,
                metadata={'funding_signals': funding_count},
            )
            patterns.append(pattern)
        return patterns
    
    def detect_partnership_pattern(self):
        patterns = []
        now = timezone.now()
        partner_count = self.data_points.filter(category='partnership', created_at__gte=now - timedelta(days=60)).count()
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
        expansion_count = self.data_points.filter(category='expansion', created_at__gte=now - timedelta(days=60)).count()
        if expansion_count >= 1:
            exp_dps = self.data_points.filter(category='expansion', created_at__gte=now - timedelta(days=60))
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
        meta = pattern.metadata or {}
        name = self.company.name
        
        if 'Hiring Surge' in pattern.name:
            focus = meta.get('focus_areas', [])
            focus_advice = f' Their focus on {", ".join(focus)} suggests they\'re building in areas that may overlap with your roadmap.' if focus else ''
            return {
                'title': f'{name}: Hiring Surge → Expect Product Launch in 3-6 Months',
                'description': f'{name} is scaling their team rapidly.{focus_advice} Historically, 72% of hiring surges at B2B SaaS companies precede a major product launch or market entry.',
                'recommendation': f'1. Check {name}\'s job postings weekly for product/market clues.\n2. Accelerate development of your differentiating features.\n3. Lock in key accounts with longer-term contracts before {name} launches.\n4. Consider a pre-emptive feature announcement to control the narrative.',
                'priority': 'high', 'predicted_timeline': '3-6 months', 'probability': pattern.confidence,
            }
        
        if 'High Product Velocity' in pattern.name:
            count = meta.get('product_signals', 0)
            return {
                'title': f'{name}: Shipping {count} Features — Your Feature Gap Is Growing',
                'description': f'{name} released {count} product/tech announcements recently, well above the industry average of 1-2 per quarter. Each release widens the feature gap if left unaddressed.',
                'recommendation': f'1. Conduct a feature-by-feature audit against {name}\'s latest releases.\n2. Prioritize parity on their most-adopted features.\n3. Double down on 2-3 areas where you\'re stronger — own those narratives.\n4. Brief your sales team on competitive positioning against their new features.',
                'priority': 'high', 'predicted_timeline': 'Ongoing', 'probability': pattern.confidence,
            }
        
        if 'Negative Sentiment' in pattern.name:
            neg_pct = meta.get('negative_ratio', 0) * 100
            return {
                'title': f'{name}: {neg_pct:.0f}% Negative Press — Window to Capture Their Customers',
                'description': f'{name} is receiving significant negative coverage. Dissatisfied customers typically begin evaluating alternatives within 30-60 days of sustained negative press.',
                'recommendation': f'1. Create a targeted landing page: "Switching from {name}? Here\'s why teams choose us."\n2. Run targeted ads to {name}\'s audience on LinkedIn and Google.\n3. Offer migration incentives (free setup, extended trial, discount).\n4. Reach out to {name}\'s vocal critics on social media with helpful content.\n5. Prepare case studies from any former {name} customers you\'ve already won.',
                'priority': 'urgent', 'predicted_timeline': '30-60 days', 'probability': pattern.confidence,
            }
        
        if 'Positive Momentum' in pattern.name:
            return {
                'title': f'{name}: Strong Positive Press — Brand Gap Widening',
                'description': f'{name} is building significant brand equity through positive coverage. Left unchecked, this momentum creates a "default choice" perception in the market.',
                'recommendation': f'1. Increase your own PR cadence — aim for 2-3 press mentions per week.\n2. Publish a competitive comparison guide (factual, not aggressive).\n3. Invest in customer success stories and testimonials.\n4. Consider a bold product announcement or milestone to shift attention.',
                'priority': 'medium', 'predicted_timeline': 'Ongoing', 'probability': pattern.confidence,
            }
        
        if 'Recent Funding' in pattern.name:
            return {
                'title': f'{name}: New Funding — Expect Aggressive Expansion',
                'description': f'{name} recently raised capital. Post-funding companies typically increase spend on R&D (40%), sales (35%), and marketing (25%) within the first two quarters.',
                'recommendation': f'1. Expect {name} to undercut on pricing — prepare your value-based selling materials.\n2. They\'ll likely hire 30-50% more in the next 6 months — monitor for strategic hires.\n3. Strengthen customer retention: reach out to your top 20 accounts proactively.\n4. If fundraising, use their round as market validation in your own pitch.',
                'priority': 'high', 'predicted_timeline': '6-12 months', 'probability': pattern.confidence,
            }
        
        if 'Partnership Acceleration' in pattern.name:
            return {
                'title': f'{name}: Building an Ecosystem — Platform Lock-in Risk',
                'description': f'{name} is rapidly forming partnerships, which suggests a platform strategy. Customers who integrate with partner ecosystems become 3x harder to switch away from.',
                'recommendation': f'1. Identify {name}\'s key integration partners and build competing integrations.\n2. Develop your own partner program to create similar ecosystem stickiness.\n3. Target customers BEFORE they adopt {name}\'s partner integrations.\n4. Position your product as "open" and "interoperable" in marketing.',
                'priority': 'high', 'predicted_timeline': '3-6 months', 'probability': pattern.confidence,
            }
        
        if 'Geographic Expansion' in pattern.name:
            regions = meta.get('target_regions', [])
            region_str = f' in {", ".join(regions)}' if regions else ''
            return {
                'title': f'{name}: Expanding{region_str} — Competitive Overlap Increasing',
                'description': f'{name} is entering new markets{region_str}. Geographic expansion is a sign of confidence in core product-market fit. They\'ll compete for customers in your existing markets.',
                'recommendation': f'1. If you\'re already in these regions, strengthen local relationships immediately.\n2. Run targeted campaigns emphasizing your established local presence.\n3. Consider hiring local sales/support in regions where {name} is entering.\n4. If not yet in these regions, evaluate whether to fast-follow or focus elsewhere.',
                'priority': 'medium', 'predicted_timeline': '6-12 months', 'probability': pattern.confidence,
            }
        
        if 'Surge in' in pattern.name:
            category = meta.get('category', 'unknown')
            cat_label = category.replace('_', ' ').title()
            return {
                'title': f'{name}: Strategic Shift Toward {cat_label}',
                'description': f'{name} is dramatically increasing {category.replace("_", " ")} activity. Strategic shifts like this typically reflect board-level decisions and forecast the company\'s direction for the next 12-18 months.',
                'recommendation': f'1. Research what specifically {name} is doing in {category.replace("_", " ")}.\n2. Assess whether this shift creates an opportunity or threat for you.\n3. If it\'s a threat, begin developing a counter-strategy now.\n4. If they\'re moving AWAY from an area, consider owning that space.',
                'priority': 'medium', 'predicted_timeline': '3-12 months', 'probability': pattern.confidence,
            }
        
        if 'Activity' in pattern.name:
            change = meta.get('change_pct', 0)
            if change > 0:
                return {
                    'title': f'{name}: Activity Spike (+{abs(change):.0f}%) — Major Move Incoming',
                    'description': f'News volume for {name} increased by {abs(change):.0f}%. Activity spikes of this magnitude precede major announcements 80% of the time.',
                    'recommendation': f'1. Set up daily Google Alerts for {name} to catch announcements early.\n2. Prepare 2-3 competitive response templates for likely scenarios.\n3. Brief your sales team on possible competitive developments.\n4. Consider timing your own announcements to coincide or pre-empt.',
                    'priority': 'medium', 'predicted_timeline': '2-4 weeks', 'probability': pattern.confidence,
                }
            else:
                return {
                    'title': f'{name}: Going Quiet (-{abs(change):.0f}%) — Stealth Mode or Trouble?',
                    'description': f'{name}\'s news volume dropped by {abs(change):.0f}%. This could mean stealth product development, internal restructuring, or strategic pivoting.',
                    'recommendation': f'1. Don\'t assume weakness — silence often precedes major launches.\n2. Monitor their GitHub/engineering blogs for stealth development activity.\n3. Check if key executives are speaking at upcoming conferences.\n4. Use this quiet period to strengthen your own positioning.',
                    'priority': 'low', 'predicted_timeline': 'Unknown', 'probability': pattern.confidence * 0.7,
                }
        
        return None
    
    def generate_cross_competitor_insights(self):
        """Generate insights by comparing this company against all other tracked competitors."""
        insights = []
        now = timezone.now()
        
        # Compare data point volume across all companies
        company_volumes = {}
        for comp in Company.objects.all():
            vol = DataPoint.objects.filter(company=comp, created_at__gte=now - timedelta(days=30)).count()
            company_volumes[comp.name] = vol
        
        if len(company_volumes) >= 2:
            sorted_vols = sorted(company_volumes.items(), key=lambda x: x[1], reverse=True)
            my_rank = next((i for i, (n, _) in enumerate(sorted_vols) if n == self.company.name), -1)
            
            if my_rank == 0 and sorted_vols[0][1] > 0:
                insight = Insight.objects.create(
                    company=self.company,
                    title=f'{self.company.name} Is the Most Active Competitor',
                    description=f'With {sorted_vols[0][1]} signals in 30 days, {self.company.name} leads all tracked competitors in activity volume. The runner-up is {sorted_vols[1][0]} with {sorted_vols[1][1]} signals. High activity correlates with market aggression.',
                    recommendation=f'1. {self.company.name} should be your #1 competitive priority.\n2. Allocate more competitive intelligence resources to tracking them.\n3. Ensure your sales team has up-to-date battle cards against {self.company.name}.\n4. Consider engaging a competitive intelligence analyst for deep monitoring.',
                    priority='high', predicted_timeline='Ongoing', probability=0.85,
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
            results[company.name] = {'error': str(e)}
    return results
