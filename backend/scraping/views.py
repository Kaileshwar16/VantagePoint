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

    from .jobs import execute_scrape
    return execute_scrape(company, request.data.get('spider', 'news'))


@api_view(['GET'])
def scrape_status(request, job_id):
    """Check scrape job status."""
    try:
        job = ScrapeJob.objects.get(id=job_id)
    except ScrapeJob.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)

    return Response(ScrapeJobSerializer(job).data)
