from django.test import TestCase
from django.utils import timezone
from api.models import Company, DataPoint
from api.serializers import DeadReckoningSerializer
from .advanced import run_dead_reckoning, _parse_funding_amount
from .engine import CompetitorAnalyzer


class ReliabilityTests(TestCase):
    def test_no_fabricated_business_metrics(self):
        company = Company.objects.create(name='Example', employee_count='1000', revenue_range='$1B')
        dr = run_dead_reckoning(company)
        data = DeadReckoningSerializer(dr).data
        self.assertIsNone(data['current_arr'])
        self.assertIsNone(data['current_geo_markets'])
        self.assertEqual(data['hiring_velocity'], 0)
        self.assertIsNone(data['confidence'])

    def test_unverified_reports_excluded(self):
        company = Company.objects.create(name='Example')
        DataPoint.objects.create(company=company, title='Fake launch', category='product_launch', published_at=timezone.now())
        self.assertEqual(run_dead_reckoning(company).product_velocity, 0)
        self.assertEqual(CompetitorAnalyzer(company.id).data_points.count(), 0)
        DataPoint.objects.create(company=company, title='Reviewed launch', category='product_launch', is_verified=True, source_url='https://example.com/report', published_at=timezone.now())
        self.assertEqual(run_dead_reckoning(company).product_velocity, 1)

    def test_dollars_not_millions(self):
        self.assertAlmostEqual(_parse_funding_amount('Raised $50'), 0.00005)
        self.assertEqual(_parse_funding_amount('Raised $50 million'), 50)
        self.assertEqual(_parse_funding_amount('Raised $1.2 billion'), 1200)
