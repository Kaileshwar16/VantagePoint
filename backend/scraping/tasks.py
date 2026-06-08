"""
Scraping tasks and utilities for VantagePoint.
Integrates Scrapy spiders with Django models.
"""
import json
import logging
from datetime import datetime
from io import StringIO

from django.utils import timezone
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging

from api.models import Company, DataPoint, ScrapeJob

logger = logging.getLogger(__name__)


def run_scrape_for_company(company_id, spider_name='news'):
    """
    Run a scrape job for a given company.
    This is a synchronous version; in production, use Celery.
    """
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        logger.error(f"Company {company_id} not found")
        return
    
    logger.info(f"Starting scrape for {company.name} using {spider_name} spider")
    
    # For now, use requests + BeautifulSoup as a simpler alternative
    # that doesn't require Twisted event loop
    from scraping.simple_scraper import scrape_company_news, scrape_company_website
    
    if spider_name == 'news':
        results = scrape_company_news(company.name, company.domain)
    elif spider_name == 'website':
        results = scrape_company_website(company.domain)
    else:
        results = scrape_company_news(company.name, company.domain)
    
    # Save results to database
    items_count = 0
    for item in results:
        # Avoid duplicates based on title + company
        if not DataPoint.objects.filter(
            company=company,
            title=item.get('title', '')[:500]
        ).exists():
            DataPoint.objects.create(
                company=company,
                title=item.get('title', 'Untitled')[:500],
                content=item.get('content', ''),
                summary=item.get('summary', ''),
                category=item.get('category', 'news'),
                sentiment=item.get('sentiment', 'neutral'),
                impact=item.get('impact', 'medium'),
                source_url=item.get('source_url', '')[:1000],
                source_name=item.get('source_name', '')[:255],
                published_at=_parse_date(item.get('published_at')),
                confidence_score=item.get('confidence', 0.6),
                raw_data=item,
            )
            items_count += 1
    
    logger.info(f"Scraped {items_count} new items for {company.name}")
    return items_count


def _parse_date(date_str):
    """Try to parse various date formats."""
    if not date_str:
        return timezone.now()
    
    formats = [
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S%z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%a, %d %b %Y %H:%M:%S %z',
        '%Y-%m-%d',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                return timezone.make_aware(dt)
            return dt
        except (ValueError, AttributeError):
            continue
    
    return timezone.now()
