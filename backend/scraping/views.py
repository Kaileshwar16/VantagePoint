"""Scraping views."""
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from api.models import Company, ScrapeJob
from api.serializers import ScrapeJobSerializer
from .tasks import run_scrape_for_company


@api_view(['POST'])
def trigger_scrape(request, company_id):
    """Trigger scraping for a company."""
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
    
    spider = request.data.get('spider', 'news')
    
    job = ScrapeJob.objects.create(
        company=company,
        spider_name=spider,
        status='running',
        started_at=timezone.now(),
    )
    
    try:
        items_count = run_scrape_for_company(company.id, spider)
        job.status = 'completed'
        job.items_scraped = items_count or 0
        job.completed_at = timezone.now()
        job.save()
    except Exception as e:
        job.status = 'failed'
        job.errors = str(e)
        job.completed_at = timezone.now()
        job.save()
    
    return Response(ScrapeJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
def scrape_status(request, job_id):
    """Check scrape job status."""
    try:
        job = ScrapeJob.objects.get(id=job_id)
    except ScrapeJob.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response(ScrapeJobSerializer(job).data)
