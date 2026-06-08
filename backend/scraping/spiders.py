"""
Scrapy spiders for VantagePoint competitive intelligence.
These spiders crawl various online sources to gather data about companies.
"""
import scrapy
import json
from datetime import datetime
from urllib.parse import quote_plus


class CompanyNewsSpider(scrapy.Spider):
    """Spider to crawl news articles about a company."""
    
    name = 'company_news'
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1,
        'ROBOTSTXT_OBEY': True,
        'USER_AGENT': 'VantagePoint Bot/1.0 (+https://vantagepoint.ai)',
        'FEEDS': {},  # We pipe directly to Django
        'LOG_LEVEL': 'INFO',
    }
    
    def __init__(self, company_name=None, company_domain=None, company_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_name = company_name or 'Unknown'
        self.company_domain = company_domain or ''
        self.company_id = company_id
    
    def start_requests(self):
        """Generate search URLs for the company."""
        search_queries = [
            f'{self.company_name} news',
            f'{self.company_name} announcement',
            f'{self.company_name} product launch',
            f'{self.company_name} funding',
        ]
        
        for query in search_queries:
            encoded = quote_plus(query)
            # Using Bing news search (more scrape-friendly)
            url = f'https://www.bing.com/news/search?q={encoded}&format=RSS'
            yield scrapy.Request(
                url=url,
                callback=self.parse_news_feed,
                meta={'query': query},
                errback=self.handle_error,
            )
    
    def parse_news_feed(self, response):
        """Parse RSS news feed results."""
        try:
            # Parse RSS/XML response
            items = response.xpath('//item')
            for item in items:
                title = item.xpath('title/text()').get('').strip()
                description = item.xpath('description/text()').get('').strip()
                link = item.xpath('link/text()').get('')
                pub_date = item.xpath('pubDate/text()').get('')
                source = item.xpath('source/text()').get('')
                
                if title:
                    yield {
                        'company_id': self.company_id,
                        'company_name': self.company_name,
                        'title': title,
                        'content': description,
                        'source_url': link,
                        'source_name': source or 'Bing News',
                        'published_at': pub_date,
                        'category': self._classify_category(title + ' ' + description),
                        'sentiment': 'neutral',
                        'spider': self.name,
                    }
        except Exception as e:
            self.logger.error(f"Error parsing news feed: {e}")
    
    def handle_error(self, failure):
        self.logger.error(f"Request failed: {failure}")
    
    def _classify_category(self, text):
        """Simple keyword-based classification."""
        text_lower = text.lower()
        categories = {
            'product_launch': ['launch', 'release', 'introduce', 'unveil', 'new product', 'announce'],
            'pricing_change': ['price', 'pricing', 'cost', 'subscription', 'fee'],
            'hiring': ['hire', 'hiring', 'job', 'recruit', 'talent', 'team'],
            'partnership': ['partner', 'collaboration', 'alliance', 'integrate', 'joint'],
            'funding': ['fund', 'invest', 'raise', 'series', 'valuation', 'ipo'],
            'acquisition': ['acquire', 'acquisition', 'merge', 'buyout', 'takeover'],
            'expansion': ['expand', 'growth', 'market', 'enter', 'global', 'international'],
            'leadership': ['ceo', 'cto', 'executive', 'appoint', 'resign', 'leadership'],
            'technology': ['ai', 'machine learning', 'cloud', 'platform', 'technology', 'innovation'],
            'marketing': ['campaign', 'brand', 'marketing', 'advertis'],
            'legal': ['lawsuit', 'regulation', 'compliance', 'legal', 'patent'],
        }
        
        for category, keywords in categories.items():
            if any(kw in text_lower for kw in keywords):
                return category
        return 'news'


class CompanyWebsiteSpider(scrapy.Spider):
    """Spider to crawl a company's website for product/pricing info."""
    
    name = 'company_website'
    
    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS': 1,
        'ROBOTSTXT_OBEY': True,
        'DEPTH_LIMIT': 2,
        'USER_AGENT': 'VantagePoint Bot/1.0 (+https://vantagepoint.ai)',
        'LOG_LEVEL': 'INFO',
    }
    
    def __init__(self, company_name=None, company_domain=None, company_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_name = company_name or 'Unknown'
        self.company_domain = company_domain or ''
        self.company_id = company_id
    
    def start_requests(self):
        if self.company_domain:
            domain = self.company_domain.rstrip('/')
            if not domain.startswith('http'):
                domain = f'https://{domain}'
            
            # Key pages to check
            paths = ['', '/pricing', '/products', '/about', '/blog', '/careers']
            for path in paths:
                url = f'{domain}{path}'
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_page,
                    meta={'page_type': path.strip('/') or 'home'},
                    errback=self.handle_error,
                )
    
    def parse_page(self, response):
        page_type = response.meta.get('page_type', 'unknown')
        
        # Extract page title
        title = response.xpath('//title/text()').get('').strip()
        
        # Extract meta description
        meta_desc = response.xpath('//meta[@name="description"]/@content').get('')
        
        # Extract main content text
        paragraphs = response.xpath('//main//p/text() | //article//p/text() | //div[@class]//p/text()').getall()
        content = ' '.join(p.strip() for p in paragraphs if p.strip())[:2000]
        
        # Extract pricing info if on pricing page
        pricing_elements = []
        if page_type == 'pricing':
            pricing_elements = response.xpath(
                '//div[contains(@class, "price") or contains(@class, "plan")]//text()'
            ).getall()
        
        if title or content:
            yield {
                'company_id': self.company_id,
                'company_name': self.company_name,
                'title': f'{self.company_name} - {page_type.title()} Page',
                'content': content or meta_desc or title,
                'source_url': response.url,
                'source_name': f'{self.company_name} Website',
                'page_type': page_type,
                'pricing_data': pricing_elements,
                'category': self._page_to_category(page_type),
                'sentiment': 'neutral',
                'spider': self.name,
            }
    
    def handle_error(self, failure):
        self.logger.error(f"Request failed: {failure}")
    
    def _page_to_category(self, page_type):
        mapping = {
            'pricing': 'pricing_change',
            'products': 'product_launch',
            'careers': 'hiring',
            'blog': 'news',
            'about': 'news',
            'home': 'news',
        }
        return mapping.get(page_type, 'news')


class TechCrunchSpider(scrapy.Spider):
    """Spider to crawl TechCrunch for company news."""
    
    name = 'techcrunch'
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1,
        'ROBOTSTXT_OBEY': True,
        'USER_AGENT': 'VantagePoint Bot/1.0',
        'LOG_LEVEL': 'INFO',
    }
    
    def __init__(self, company_name=None, company_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_name = company_name or 'Unknown'
        self.company_id = company_id
    
    def start_requests(self):
        encoded = quote_plus(self.company_name)
        url = f'https://techcrunch.com/wp-json/tc/v1/magazine?search={encoded}&_embed=true'
        yield scrapy.Request(url=url, callback=self.parse_api, errback=self.handle_error)
    
    def parse_api(self, response):
        try:
            articles = json.loads(response.text)
            if isinstance(articles, list):
                for article in articles[:10]:
                    title = article.get('title', {})
                    if isinstance(title, dict):
                        title = title.get('rendered', '')
                    content = article.get('excerpt', {})
                    if isinstance(content, dict):
                        content = content.get('rendered', '')
                    
                    yield {
                        'company_id': self.company_id,
                        'company_name': self.company_name,
                        'title': title,
                        'content': content,
                        'source_url': article.get('link', ''),
                        'source_name': 'TechCrunch',
                        'published_at': article.get('date', ''),
                        'category': 'news',
                        'sentiment': 'neutral',
                        'spider': self.name,
                    }
        except (json.JSONDecodeError, Exception) as e:
            self.logger.error(f"Error parsing TechCrunch API: {e}")
    
    def handle_error(self, failure):
        self.logger.error(f"Request failed: {failure}")
