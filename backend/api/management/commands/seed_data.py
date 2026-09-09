"""
Management command to seed the database with demo data.
"""
import random
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from api.models import Company, DataPoint, Pattern, Insight, CompetitorRelationship


class Command(BaseCommand):
    help = 'Seed database with demo competitive intelligence data'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Demo seeding is disabled outside development.')
        if Company.objects.exists():
            raise CommandError('Seed only an empty development database to avoid mixing demo and real records.')
        self.stdout.write('Seeding DEMO database; all generated records are fictional and unverified.')

        # Create companies
        companies_data = [
            {
                'name': 'DEMO Stripe',
                'domain': 'https://stripe.com',
                'industry': 'finance',
                'description': 'Online payment processing platform for internet businesses',
                'headquarters': 'San Francisco, CA',
                'employee_count': '8000+',
                'revenue_range': '$14B+',
                'founded_year': 2010,
            },
            {
                'name': 'DEMO Shopify',
                'domain': 'https://shopify.com',
                'industry': 'tech',
                'description': 'E-commerce platform for online stores and retail point-of-sale systems',
                'headquarters': 'Ottawa, Canada',
                'employee_count': '11000+',
                'revenue_range': '$5.6B',
                'founded_year': 2006,
            },
            {
                'name': 'DEMO HubSpot',
                'domain': 'https://hubspot.com',
                'industry': 'tech',
                'description': 'CRM platform with marketing, sales, and service software',
                'headquarters': 'Cambridge, MA',
                'employee_count': '7000+',
                'revenue_range': '$2.2B',
                'founded_year': 2006,
            },
            {
                'name': 'DEMO Datadog',
                'domain': 'https://datadoghq.com',
                'industry': 'tech',
                'description': 'Cloud monitoring and security platform',
                'headquarters': 'New York, NY',
                'employee_count': '5500+',
                'revenue_range': '$2.1B',
                'founded_year': 2010,
            },
            {
                'name': 'DEMO Twilio',
                'domain': 'https://twilio.com',
                'industry': 'tech',
                'description': 'Cloud communications platform as a service',
                'headquarters': 'San Francisco, CA',
                'employee_count': '5000+',
                'revenue_range': '$4B',
                'founded_year': 2008,
            },
            {
                'name': 'Notion',
                'domain': 'https://notion.so',
                'industry': 'tech',
                'description': 'All-in-one workspace for notes, tasks, and collaboration',
                'headquarters': 'San Francisco, CA',
                'employee_count': '1000+',
                'revenue_range': '$250M+',
                'founded_year': 2013,
            },
        ]

        companies = []
        for data in companies_data:
            company, created = Company.objects.get_or_create(
                name=data['name'],
                defaults=data,
            )
            companies.append(company)
            if created:
                self.stdout.write(f'  Created company: {company.name}')

        # Create competitor relationships
        for i, c1 in enumerate(companies):
            for c2 in companies[i+1:]:
                if random.random() > 0.4:
                    CompetitorRelationship.objects.get_or_create(
                        company=c1, competitor=c2,
                        defaults={'overlap_score': random.uniform(20, 85)}
                    )

        # Create data points
        categories = ['product_launch', 'pricing_change', 'hiring', 'partnership',
                       'funding', 'acquisition', 'expansion', 'leadership',
                       'technology', 'marketing', 'news']
        sentiments = ['positive', 'neutral', 'negative']
        impacts = ['low', 'medium', 'high', 'critical']

        data_point_templates = [
            ('product_launch', '{company} Launches New AI-Powered Feature Suite', 'The company unveiled a comprehensive AI integration across its platform, promising 3x efficiency gains for enterprise customers.'),
            ('product_launch', '{company} Releases Major Platform Update v4.0', 'New version includes redesigned dashboard, API improvements, and enhanced security features.'),
            ('pricing_change', '{company} Adjusts Enterprise Pricing Structure', 'The company has restructured its enterprise tier pricing, introducing a new usage-based model.'),
            ('pricing_change', '{company} Introduces Free Tier for Startups', 'A new free tier aimed at early-stage startups has been launched with generous usage limits.'),
            ('hiring', '{company} Plans to Hire 500 Engineers in AI Division', 'Aggressive hiring push signals major investment in artificial intelligence capabilities.'),
            ('hiring', '{company} Opens New Engineering Hub in Bangalore', 'The company expands its global engineering presence with a new 200-person office.'),
            ('partnership', '{company} Partners with AWS for Deep Integration', 'Strategic partnership will bring native integration with Amazon Web Services.'),
            ('partnership', '{company} and Salesforce Announce Integration Partnership', 'Joint solution will provide seamless CRM-to-platform connectivity.'),
            ('funding', '{company} Raises $200M Series F at $10B Valuation', 'New funding round led by Sequoia Capital will fuel international expansion.'),
            ('expansion', '{company} Expands into European Market', 'New London office and GDPR-compliant infrastructure announced.'),
            ('expansion', '{company} Enters Asia-Pacific Market with Tokyo Office', 'The company sets up operations in Japan to serve growing APAC demand.'),
            ('leadership', '{company} Appoints New CTO from Google', 'Former Google VP of Engineering joins as Chief Technology Officer.'),
            ('technology', '{company} Open Sources Machine Learning Framework', 'New open-source ML toolkit released to the developer community.'),
            ('technology', '{company} Achieves SOC 2 Type II Certification', 'Security compliance milestone demonstrates enterprise readiness.'),
            ('marketing', '{company} Launches Global Brand Campaign', 'Multi-channel marketing campaign targets mid-market B2B buyers.'),
            ('acquisition', '{company} Acquires AI Startup for $50M', 'Acquisition of startup specialized in NLP will strengthen AI capabilities.'),
            ('news', '{company} Named Leader in Gartner Magic Quadrant', 'Analyst recognition as industry leader in latest market analysis report.'),
            ('news', '{company} Reports 45% YoY Revenue Growth', 'Strong quarterly results driven by enterprise customer expansion.'),
            ('legal', '{company} Faces Regulatory Scrutiny in EU', 'European regulators investigate data handling practices.'),
            ('news', '{company} Hosts Annual Developer Conference', 'Thousands attend annual conference, several major announcements made.'),
        ]

        now = timezone.now()
        dp_count = 0
        for company in companies:
            # Create 15-25 data points per company spread over last 90 days
            num_points = random.randint(15, 25)
            selected = random.sample(data_point_templates, min(num_points, len(data_point_templates)))

            for i, (category, title_template, content) in enumerate(selected):
                days_ago = random.randint(0, 90)
                hours_ago = random.randint(0, 23)

                sentiment = random.choices(sentiments, weights=[0.4, 0.4, 0.2])[0]
                impact = random.choices(impacts, weights=[0.2, 0.4, 0.3, 0.1])[0]

                dp, created = DataPoint.objects.get_or_create(
                    company=company,
                    title=title_template.format(company=company.name),
                    defaults={
                        'content': content,
                        'category': category,
                        'sentiment': sentiment,
                        'impact': impact,
                        'source_url': '',
                        'source_name': 'DEMO — fictional record',
                        'raw_data': {'is_demo': True},
                        'published_at': now - timedelta(days=days_ago, hours=hours_ago),
                        'confidence_score': random.uniform(0.6, 0.95),
                    }
                )
                if created:
                    dp_count += 1

        self.stdout.write(f'  Created {dp_count} data points')

        # Create patterns
        pattern_count = 0
        for company in companies:
            patterns_data = [
                {
                    'name': f'High Product Velocity',
                    'description': f'{company.name} has released multiple product updates in the last 60 days, indicating accelerated development.',
                    'pattern_type': 'trend',
                    'confidence': random.uniform(0.6, 0.9),
                },
                {
                    'name': f'Hiring Surge Detected',
                    'description': f'{company.name} is aggressively hiring, especially in engineering and AI roles.',
                    'pattern_type': 'trend',
                    'confidence': random.uniform(0.55, 0.85),
                },
                {
                    'name': f'Market Expansion Pattern',
                    'description': f'{company.name} is systematically entering new geographic markets.',
                    'pattern_type': 'strategy_shift',
                    'confidence': random.uniform(0.5, 0.8),
                },
            ]

            selected_patterns = random.sample(patterns_data, random.randint(1, 3))
            for pd in selected_patterns:
                pattern, created = Pattern.objects.get_or_create(
                    company=company,
                    name=pd['name'],
                    defaults=pd,
                )
                if created:
                    pattern_count += 1
                    # Link some data points
                    dps = DataPoint.objects.filter(company=company).order_by('?')[:3]
                    pattern.supporting_data.set(dps)

        self.stdout.write(f'  Created {pattern_count} patterns')

        # Create insights
        insight_count = 0
        insight_templates = [
            {
                'title': '🚀 {company} Is Shipping Fast — Competitive Threat Rising',
                'description': '{company} is releasing features at an elevated rate, signaling strong investment.',
                'recommendation': 'Focus on differentiation. Identify gaps they haven\'t addressed.',
                'priority': 'high',
                'predicted_timeline': 'Ongoing',
                'probability': 0.78,
            },
            {
                'title': '⚡ {company} Scaling Up — Expect New Moves',
                'description': '{company} hiring activity suggests major product launch within 3-6 months.',
                'recommendation': 'Accelerate your roadmap. Monitor their job postings for product clues.',
                'priority': 'high',
                'predicted_timeline': 'Within 3-6 months',
                'probability': 0.72,
            },
            {
                'title': '🌍 {company} Expanding Globally — New Market Competition',
                'description': '{company} is entering markets where you have presence.',
                'recommendation': 'Strengthen relationships with key accounts in overlapping regions.',
                'priority': 'medium',
                'predicted_timeline': 'Within 6 months',
                'probability': 0.65,
            },
            {
                'title': '💰 {company} Pricing Shift — Customer Churn Risk',
                'description': '{company} adjusted pricing which may attract your price-sensitive customers.',
                'recommendation': 'Review your pricing competitiveness. Consider targeted retention offers.',
                'priority': 'urgent',
                'predicted_timeline': 'Within 30 days',
                'probability': 0.8,
            },
            {
                'title': '🤖 {company} AI Investment — Technology Gap Risk',
                'description': '{company} is investing heavily in AI, which could create competitive advantage.',
                'recommendation': 'Evaluate your AI roadmap. Consider partnerships or acquisitions.',
                'priority': 'medium',
                'predicted_timeline': 'Within 12 months',
                'probability': 0.6,
            },
        ]

        for company in companies:
            selected_insights = random.sample(insight_templates, random.randint(2, 4))
            for it in selected_insights:
                data = {k: v.format(company=company.name) if isinstance(v, str) else v for k, v in it.items()}
                insight, created = Insight.objects.get_or_create(
                    company=company,
                    title=data['title'],
                    defaults=data,
                )
                if created:
                    insight_count += 1
                    patterns = Pattern.objects.filter(company=company).order_by('?')[:2]
                    insight.related_patterns.set(patterns)

        self.stdout.write(f'  Created {insight_count} insights')
        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))
