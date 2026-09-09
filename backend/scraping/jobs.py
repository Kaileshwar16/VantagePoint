import logging
from django.utils import timezone
from rest_framework.response import Response
from api.models import ScrapeJob
from api.serializers import ScrapeJobSerializer
from .tasks import run_scrape_for_company

logger = logging.getLogger(__name__)


def execute_scrape(company, spider):
    if spider not in ('news', 'website'):
        return Response({'error': 'Supported spiders: news, website'}, status=400)
    job = ScrapeJob.objects.create(company=company, spider_name=spider, status='running', started_at=timezone.now())
    try:
        job.items_scraped = run_scrape_for_company(company.id, spider) or 0
        job.status = 'completed'
    except Exception:
        logger.exception('Collection failed for company %s', company.id)
        job.status = 'failed'
        job.errors = 'Collection failed. Check server logs and source availability.'
    job.completed_at = timezone.now()
    job.save()
    return Response(ScrapeJobSerializer(job).data, status=502 if job.status == 'failed' else 200)
