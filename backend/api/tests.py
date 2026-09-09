from unittest.mock import patch
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Company, DataPoint, Insight, DeadReckoning, ScrapeJob


@override_settings(SECURE_SSL_REDIRECT=False)
class APITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user('reviewer', password='a-secure-test-password', is_staff=True)
        self.company = Company.objects.create(name='Example')

    def authorize(self):
        self.client.force_authenticate(self.staff)

    def test_anonymous_cannot_read_or_modify(self):
        for path in ['/api/companies/', '/api/dashboard/', '/api/data-quality/', '/api/signals/']:
            self.assertEqual(self.client.get(path).status_code, 403)
        self.assertEqual(self.client.post('/api/companies/', {'name': 'Intruder'}).status_code, 403)

    def test_nonstaff_cannot_read(self):
        self.client.force_authenticate(User.objects.create_user('outsider'))
        self.assertEqual(self.client.get('/api/companies/').status_code, 403)

    def test_csrf_login_logout(self):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get('/api/session/').json()['csrfToken']
        credentials = {'username': 'reviewer', 'password': 'a-secure-test-password'}
        self.assertEqual(client.post('/api/session/', credentials, format='json').status_code, 403)
        response = client.post('/api/session/', credentials, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertTrue(response.json()['authenticated'])
        self.assertEqual(client.get('/api/companies/').status_code, 200)
        self.assertEqual(client.delete('/api/session/', HTTP_X_CSRFTOKEN=response.json()['csrfToken']).status_code, 200)
        self.assertEqual(client.get('/api/companies/').status_code, 403)

    def test_invalid_session_payload(self):
        self.assertEqual(self.client.post('/api/session/', [], format='json').status_code, 400)

    def test_days_validation(self):
        self.authorize()
        for days in ['oops', '-1', '999999999']:
            self.assertEqual(self.client.get(f'/api/companies/{self.company.id}/timeline/?days={days}').status_code, 400)

    def test_overlay_validation(self):
        self.authorize()
        for data in [{'company_ids': 'xx'}, {'company_ids': [1, {}]}, {'company_ids': [1, 1]}, {'company_ids': [999, 1000]}, {'company_ids': [1, 2], 'days': 'x'}]:
            self.assertEqual(self.client.post('/api/timeline-overlay/', data, format='json').status_code, 400)

    def test_pagination_does_not_ignore_page_size(self):
        self.authorize()
        Company.objects.bulk_create([Company(name=f'Company {n}') for n in range(25)])
        response = self.client.get('/api/companies/?page_size=25').json()
        self.assertEqual(len(response['results']), 25)
        self.assertIsNotNone(response['next'])

    def test_verified_record_needs_source(self):
        self.authorize()
        dp = DataPoint.objects.create(company=self.company, title='Source needed', content='Text')
        response = self.client.patch(f'/api/datapoints/{dp.id}/', {'is_verified': True}, format='json')
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(f'/api/datapoints/{dp.id}/', {'confidence_score': 3}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_future_record_cannot_be_verified(self):
        self.authorize()
        dp = DataPoint.objects.create(company=self.company, title='Future', content='Text', source_url='https://example.com/report', published_at=timezone.now()+timedelta(days=1))
        self.assertEqual(self.client.patch(f'/api/datapoints/{dp.id}/', {'is_verified': True}, format='json').status_code, 400)

    def test_quality_counts(self):
        self.authorize()
        DataPoint.objects.create(company=self.company, title='Unknown', content='Text')
        data = self.client.get('/api/data-quality/').json()
        self.assertEqual(data['missing_sources'], 1)
        self.assertEqual(data['verified_records'], 0)
        self.assertEqual(data['unknown_publication_dates'], 1)

    def test_priority_sort_is_semantic(self):
        self.authorize()
        for priority in ['low', 'medium', 'urgent', 'high']:
            Insight.objects.create(company=self.company, title=priority, priority=priority)
        priorities = [i['priority'] for i in self.client.get('/api/dashboard/').json()['top_insights']]
        self.assertEqual(priorities, ['urgent', 'high', 'medium', 'low'])

    def test_legacy_forecast_hidden(self):
        self.authorize()
        dr = DeadReckoning.objects.create(company=self.company, current_arr=999, projected_arr_12m=2000)
        data = self.client.get(f'/api/dead-reckonings/{dr.id}/').json()
        self.assertIsNone(data['current_arr'])
        self.assertIsNone(data['projected_arr_12m'])
        self.assertIsNone(data['confidence'])
        self.assertEqual(self.client.post('/api/dead-reckonings/', {'company': self.company.id}).status_code, 405)

    @patch('scraping.jobs.run_scrape_for_company', return_value=3)
    def test_scrape_records_result(self, scrape):
        self.authorize()
        response = self.client.post(f'/api/companies/{self.company.id}/scrape/', {'spider': 'news'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['items_scraped'], 3)
        self.assertIsNotNone(response.data['completed_at'])

    @patch('scraping.jobs.run_scrape_for_company', side_effect=RuntimeError('secret internal error'))
    def test_scrape_failure_not_success(self, scrape):
        self.authorize()
        response = self.client.post(f'/api/companies/{self.company.id}/scrape/')
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('secret', response.data['errors'])
        self.assertEqual(ScrapeJob.objects.get().status, 'failed')

    def test_invalid_spider_creates_no_job(self):
        self.authorize()
        response = self.client.post(f'/api/companies/{self.company.id}/scrape/', {'spider': 'invalid'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ScrapeJob.objects.count(), 0)

    def test_authenticated_read_endpoints(self):
        self.authorize()
        for path in ['companies', 'datapoints', 'patterns', 'insights', 'scrape-jobs', 'signals', 'compound-signals', 'pricing-snapshots', 'battlecards', 'dead-reckonings', 'dashboard', 'data-quality']:
            self.assertEqual(self.client.get(f'/api/{path}/').status_code, 200, path)

    def test_analysis_workflows(self):
        self.authorize()
        for n in range(6):
            DataPoint.objects.create(company=self.company, title=f'Hiring engineer {n}', category='hiring', is_verified=True, source_url=f'https://example.com/{n}', published_at=timezone.now())
        self.assertEqual(self.client.post(f'/api/analysis/run/{self.company.id}/').status_code, 200)
        response = self.client.post(f'/api/companies/{self.company.id}/advanced-analysis/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['results']['errors'], {})
        self.assertEqual(self.client.post('/api/analysis/run-all/').status_code, 200)

    def test_edit_invalidates_review_and_records_reviewer(self):
        self.authorize()
        dp = DataPoint.objects.create(company=self.company, title='Reviewed', content='Original', is_verified=True, source_url='https://example.com')
        response = self.client.patch(f'/api/datapoints/{dp.id}/', {'content': 'Changed'}, format='json')
        self.assertEqual(response.status_code, 200)
        dp.refresh_from_db()
        self.assertFalse(dp.is_verified)
        self.assertEqual(dp.raw_data['review']['reviewer_id'], self.staff.id)
