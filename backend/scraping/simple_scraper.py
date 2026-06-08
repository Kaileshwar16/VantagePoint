"""
Simple scraper using requests + BeautifulSoup.
Used as a fallback when Scrapy's Twisted reactor conflicts with Django.
"""
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def scrape_company_news(company_name, company_domain=''):
    """Scrape news about a company from multiple sources."""
    results = []
    
    # 1. Bing News RSS
    try:
        results.extend(_scrape_bing_news(company_name))
    except Exception as e:
        logger.warning(f"Bing news scrape failed for {company_name}: {e}")
    
    # 2. Google News RSS
    try:
        results.extend(_scrape_google_news_rss(company_name))
    except Exception as e:
        logger.warning(f"Google news scrape failed for {company_name}: {e}")
    
    # 3. If domain provided, scrape their blog/news
    if company_domain:
        try:
            results.extend(_scrape_company_blog(company_domain))
        except Exception as e:
            logger.warning(f"Blog scrape failed for {company_domain}: {e}")
    
    return results


def _scrape_bing_news(company_name):
    """Scrape Bing News RSS feed."""
    items = []
    encoded = quote_plus(company_name)
    url = f'https://www.bing.com/news/search?q={encoded}&format=RSS'
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            for item in soup.find_all('item'):
                title = item.find('title')
                desc = item.find('description')
                link = item.find('link')
                pub_date = item.find('pubdate')
                source = item.find('source')
                
                if title:
                    items.append({
                        'title': title.get_text(strip=True),
                        'content': desc.get_text(strip=True) if desc else '',
                        'source_url': link.get_text(strip=True) if link else '',
                        'source_name': source.get_text(strip=True) if source else 'Bing News',
                        'published_at': pub_date.get_text(strip=True) if pub_date else '',
                        'category': _classify_text(title.get_text()),
                        'sentiment': _simple_sentiment(title.get_text() + ' ' + (desc.get_text() if desc else '')),
                        'impact': 'medium',
                        'confidence': 0.7,
                    })
    except Exception as e:
        logger.error(f"Bing news error: {e}")
    
    return items


def _scrape_google_news_rss(company_name):
    """Scrape Google News RSS feed."""
    items = []
    encoded = quote_plus(company_name)
    url = f'https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en'
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            for item in soup.find_all('item')[:15]:
                title = item.find('title')
                desc = item.find('description')
                link = item.find('link')
                pub_date = item.find('pubdate')
                source = item.find('source')
                
                if title:
                    items.append({
                        'title': title.get_text(strip=True),
                        'content': desc.get_text(strip=True) if desc else '',
                        'source_url': link.get_text(strip=True) if link else '',
                        'source_name': source.get_text(strip=True) if source else 'Google News',
                        'published_at': pub_date.get_text(strip=True) if pub_date else '',
                        'category': _classify_text(title.get_text()),
                        'sentiment': _simple_sentiment(title.get_text() + ' ' + (desc.get_text() if desc else '')),
                        'impact': 'medium',
                        'confidence': 0.7,
                    })
    except Exception as e:
        logger.error(f"Google news error: {e}")
    
    return items


def scrape_company_website(domain):
    """Scrape a company's website for key pages."""
    results = []
    if not domain:
        return results
    
    base_url = domain.rstrip('/')
    if not base_url.startswith('http'):
        base_url = f'https://{base_url}'
    
    pages = {
        '': 'home',
        '/pricing': 'pricing',
        '/products': 'products',
        '/about': 'about',
        '/blog': 'blog',
        '/careers': 'careers',
    }
    
    for path, page_type in pages.items():
        url = f'{base_url}{path}'
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                title = soup.find('title')
                title_text = title.get_text(strip=True) if title else ''
                
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                meta_text = meta_desc.get('content', '') if meta_desc else ''
                
                # Get main content
                for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                
                body = soup.find('body')
                text = body.get_text(separator=' ', strip=True)[:3000] if body else ''
                
                results.append({
                    'title': f'{title_text} ({page_type})',
                    'content': text or meta_text,
                    'source_url': url,
                    'source_name': f'Company Website',
                    'category': _page_to_category(page_type),
                    'sentiment': 'neutral',
                    'impact': 'low',
                    'confidence': 0.8,
                })
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")
    
    return results


def _scrape_company_blog(domain):
    """Try to scrape company blog."""
    results = []
    base_url = domain.rstrip('/')
    if not base_url.startswith('http'):
        base_url = f'https://{base_url}'
    
    blog_paths = ['/blog', '/news', '/insights', '/resources']
    
    for path in blog_paths:
        url = f'{base_url}{path}'
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                # Find article-like elements
                articles = soup.find_all(['article', 'div'], class_=lambda c: c and any(
                    x in str(c).lower() for x in ['post', 'article', 'blog', 'card']
                ))[:5]
                
                for article in articles:
                    title_el = article.find(['h2', 'h3', 'h1', 'a'])
                    title = title_el.get_text(strip=True) if title_el else ''
                    
                    link_el = article.find('a', href=True)
                    link = link_el['href'] if link_el else ''
                    if link and not link.startswith('http'):
                        link = f'{base_url}{link}'
                    
                    content = article.get_text(separator=' ', strip=True)[:500]
                    
                    if title:
                        results.append({
                            'title': title,
                            'content': content,
                            'source_url': link,
                            'source_name': f'Company Blog',
                            'category': _classify_text(title),
                            'sentiment': _simple_sentiment(title + ' ' + content),
                            'impact': 'medium',
                            'confidence': 0.75,
                        })
                break  # Found a working blog path
        except Exception:
            continue
    
    return results


def _classify_text(text):
    """Simple keyword-based category classification."""
    text_lower = text.lower()
    categories = {
        'product_launch': ['launch', 'release', 'introduce', 'unveil', 'new product', 'announce', 'update', 'feature'],
        'pricing_change': ['price', 'pricing', 'cost', 'subscription', 'fee', 'plan', 'tier'],
        'hiring': ['hire', 'hiring', 'job', 'recruit', 'talent', 'team', 'position'],
        'partnership': ['partner', 'collaboration', 'alliance', 'integrate', 'joint venture'],
        'funding': ['fund', 'invest', 'raise', 'series', 'valuation', 'ipo', 'capital'],
        'acquisition': ['acquire', 'acquisition', 'merge', 'buyout', 'takeover'],
        'expansion': ['expand', 'growth', 'market', 'enter', 'global', 'international', 'region'],
        'leadership': ['ceo', 'cto', 'executive', 'appoint', 'resign', 'leadership', 'board'],
        'technology': ['ai', 'machine learning', 'cloud', 'platform', 'innovation', 'patent'],
        'marketing': ['campaign', 'brand', 'marketing', 'advertis', 'event', 'conference'],
        'legal': ['lawsuit', 'regulation', 'compliance', 'legal', 'patent', 'antitrust'],
    }
    
    for category, keywords in categories.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return 'news'


def _simple_sentiment(text):
    """Simple keyword-based sentiment analysis."""
    text_lower = text.lower()
    
    positive_words = ['growth', 'success', 'launch', 'innovation', 'partnership', 'profit',
                      'revenue', 'expand', 'award', 'milestone', 'breakthrough', 'record',
                      'boost', 'improve', 'gain', 'win', 'achieve', 'strong']
    negative_words = ['layoff', 'decline', 'loss', 'lawsuit', 'controversy', 'failure',
                      'breach', 'fine', 'penalty', 'shutdown', 'closure', 'cut',
                      'drop', 'fall', 'crash', 'struggle', 'problem', 'crisis']
    
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)
    
    if pos_count > neg_count:
        return 'positive'
    elif neg_count > pos_count:
        return 'negative'
    return 'neutral'


def _page_to_category(page_type):
    """Map page type to data category."""
    mapping = {
        'pricing': 'pricing_change',
        'products': 'product_launch',
        'careers': 'hiring',
        'blog': 'news',
        'about': 'news',
        'home': 'news',
    }
    return mapping.get(page_type, 'news')
