"""
Simple scraper using requests + BeautifulSoup.
Used as a fallback when Scrapy's Twisted reactor conflicts with Django.
"""
import logging
from . import http as requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def scrape_company_news(company_name, company_domain=''):
    """Scrape news about a company from multiple sources."""
    results = []

    successful_sources = 0
    # 1. Bing News RSS
    try:
        results.extend(_scrape_bing_news(company_name))
        successful_sources += 1
    except Exception as e:
        logger.warning(f"Bing news scrape failed for {company_name}: {e}")

    # 2. Google News RSS
    try:
        results.extend(_scrape_google_news_rss(company_name))
        successful_sources += 1
    except Exception as e:
        logger.warning(f"Google news scrape failed for {company_name}: {e}")

    # 3. If domain provided, scrape their blog/news
    if company_domain:
        try:
            results.extend(_scrape_company_blog(company_domain))
        except Exception as e:
            logger.warning(f"Blog scrape failed for {company_domain}: {e}")

    if successful_sources == 0 and not results:
        raise RuntimeError('All news sources failed; no records collected.')
    return results


def _is_relevant(title, content, company_name):
    """Check if a scraped article is actually about the target company.

    Filters out:
    - Articles about people who share the company name (obituaries, bios)
    - Garbage HTML artifacts ('Skip to content', nav text)
    - Common-word false positives ('cut some slack', 'the notion of')
    - Articles where the company name appears only as a surname
    """
    import re
    combined = title + ' ' + content
    combined_lower = combined.lower()
    name_lower = company_name.lower().strip()
    title_lower = title.lower().strip()

    # ── Reject garbage HTML artifacts ───────────────────────────────
    GARBAGE_TITLES = [
        'skip to content', 'skip to main', 'news', 'blog', 'home', 'about',
        'menu', 'navigation', 'search', 'sign in', 'log in', 'subscribe',
        'cookie', 'privacy policy', 'terms of service',
    ]
    if title_lower in GARBAGE_TITLES or len(title.strip()) < 15:
        return False

    # ── Must mention the company name in the first 300 chars ───────
    if name_lower not in combined_lower[:300]:
        return False

    # ── Reject obituaries, funeral notices, and personal profiles ──
    PERSON_INDICATORS = [
        'obituary', 'obituaries', 'funeral', 'memorial', 'passed away',
        'survived by', 'beloved', 'in loving memory', 'rest in peace', 'rip',
        'funeral home', 'funeral parlor', 'cemetery', 'burial',
        'condolences', 'visitation', 'wake',
    ]
    if any(ind in combined_lower for ind in PERSON_INDICATORS):
        return False

    # ── Special handling for common-word company names ─────────────
    COMMON_WORD_COMPANIES = {
        'Slack': {
            # False positive phrases where "slack" is a common word
            'false_phrases': [
                r'cut\s+.*\s*slack', r'some\s+slack', r'pick\s+up\s+the\s+slack',
                r'slack\s+off', r'slack\s+jaw', r'slack\s+safety',
                r'slack\s+measures', r'slack\s+season', r'slack\s+water',
                r'slack\s+tide', r'slack\s+randoms',
            ],
            # Must include one of these business context words to be relevant
            'require_context': [
                'messaging', 'salesforce', 'workplace', 'collaboration',
                'enterprise', 'channel', 'workspace', 'integration',
                'slack connect', 'slack ai', 'huddle', 'app',
                'platform', 'communication', 'team', 'saas', 'software',
                'workflow', 'productivity', 'api', 'bot',
            ],
        },
        'Notion': {
            'false_phrases': [
                r'notion\s+of\b', r'notion\s+that\b', r'the\s+notion\b',
                r'preconceived\s+notion', r'no\s+notion', r'any\s+notion',
                r'common\s+notion', r'romantic\s+notion', r'very\s+notion',
            ],
            'require_context': [
                'productivity', 'workspace', 'template', 'database',
                'wiki', 'note', 'project management', 'collaboration',
                'notion ai', 'notion.so', 'app', 'saas', 'software',
                'platform', 'tool', 'startup', 'valuation',
            ],
        },
        'Stripe': {
            'false_phrases': [
                r'racing\s+stripe', r'pin\s*stripe', r'tiger\s+stripe',
                r'stripe\s+pattern', r'earn\s+.*\s*stripe',
            ],
            'require_context': [
                'payment', 'fintech', 'checkout', 'billing', 'merchant',
                'transaction', 'stripe.com', 'ipo', 'api', 'saas',
                'software', 'platform', 'startup', 'valuation', 'revenue',
            ],
        },
    }

    if company_name in COMMON_WORD_COMPANIES:
        config = COMMON_WORD_COMPANIES[company_name]

        # Check for false positive phrases
        for pat in config['false_phrases']:
            if re.search(pat, combined_lower):
                return False

        # Require case-sensitive match (proper noun)
        if not re.search(r'\b' + re.escape(company_name) + r'\b', combined):
            return False

        # For single-word names, also check for person-name patterns
        # "FirstName Slack" or "Slack, FirstName" patterns = likely a person
        person_patterns = [
            # "Stephano Slack", "Karen Slack", "Paul D. Slack"
            r'[A-Z][a-z]+\s+(?:[A-Z]\.\s+)?' + re.escape(company_name) + r'\b',
            # "Slack, Stephano"
            re.escape(company_name) + r',\s+[A-Z][a-z]+',
        ]
        person_matches = sum(1 for p in person_patterns if re.search(p, combined))
        company_context = sum(1 for kw in config['require_context'] if kw in combined_lower)

        # If it looks like a person's name and has no business context, reject
        if person_matches > 0 and company_context == 0:
            return False

        # If there's zero business context at all, it's probably not about the company
        if company_context == 0:
            return False

    return True


def _scrape_bing_news(company_name):
    """Scrape Bing News RSS feed."""
    items = []
    # Use quoted company name to get exact matches
    encoded = quote_plus(f'"{company_name}" company')
    url = f'https://www.bing.com/news/search?q={encoded}&format=RSS'

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'xml')
            for item in soup.find_all('item'):
                title = item.find('title')
                desc = item.find('description')
                link = item.find('link')
                pub_date = item.find('pubDate') or item.find('pubdate')
                source = item.find('source')

                if title:
                    title_text = title.get_text(strip=True)
                    raw_desc = desc.get_text(strip=True) if desc else ''
                    desc_text = BeautifulSoup(raw_desc, 'html.parser').get_text(separator=' ', strip=True) if raw_desc else ''

                    # Skip irrelevant results
                    if not _is_relevant(title_text, desc_text, company_name):
                        continue

                    items.append({
                        'title': title_text,
                        'content': desc_text,
                        'source_url': link.get_text(strip=True) if link else '',
                        'source_name': source.get_text(strip=True) if source else 'Bing News',
                        'published_at': pub_date.get_text(strip=True) if pub_date else '',
                        'category': _classify_text(title_text),
                        'sentiment': _simple_sentiment(title_text + ' ' + desc_text),
                        'impact': 'medium',
                        'confidence': 0.7,
                    })
    except Exception as e:
        logger.error(f"Bing news error: {e}")
        raise

    return items


def _scrape_google_news_rss(company_name):
    """Scrape Google News RSS feed."""
    items = []
    # Use quoted company name to get exact matches
    encoded = quote_plus(f'"{company_name}"')
    url = f'https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en'

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'xml')
            for item in soup.find_all('item')[:15]:
                title = item.find('title')
                desc = item.find('description')
                link = item.find('link')
                pub_date = item.find('pubDate') or item.find('pubdate')
                source = item.find('source')

                if title:
                    title_text = title.get_text(strip=True)
                    raw_desc = desc.get_text(strip=True) if desc else ''
                    desc_text = BeautifulSoup(raw_desc, 'html.parser').get_text(separator=' ', strip=True) if raw_desc else ''

                    # Skip irrelevant results
                    if not _is_relevant(title_text, desc_text, company_name):
                        continue

                    items.append({
                        'title': title_text,
                        'content': desc_text,
                        'source_url': link.get_text(strip=True) if link else '',
                        'source_name': source.get_text(strip=True) if source else 'Google News',
                        'published_at': pub_date.get_text(strip=True) if pub_date else '',
                        'category': _classify_text(title_text),
                        'sentiment': _simple_sentiment(title_text + ' ' + desc_text),
                        'impact': 'medium',
                        'confidence': 0.7,
                    })
    except Exception as e:
        logger.error(f"Google news error: {e}")
        raise

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
                    'category': 'news',  # A page snapshot is not evidence of a business event.
                    'record_type': 'website_snapshot',
                    'sentiment': 'neutral',
                    'impact': 'low',
                    'confidence': 0.8,
                })
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")

    if not results:
        raise RuntimeError('No website pages could be collected.')
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
                        link = urljoin(url, link)

                    content = article.get_text(separator=' ', strip=True)[:500]

                    # Skip generic page titles or very short titles
                    if not title or len(title.strip()) < 15:
                        continue

                    results.append({
                        'title': title,
                        'content': content,
                        'source_url': link or url,
                        'source_name': 'Company Blog',
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
    """Keyword-based category classification with compound matching.

    Uses multi-word phrases as primary signals and rejects stock market noise
    from being misclassified as business events.
    """
    text_lower = text.lower()

    # ── First: detect stock/investment noise to avoid misclassification ──
    STOCK_NOISE_WORDS = [
        'stock price', 'share price', 'shares fall', 'shares rise', 'shares drop',
        'shares jump', 'shares sold', 'shares bought', 'stock plummets',
        'stock soars', 'stock rating', 'stock today', 'stock a good',
        'stock could', 'stock outlook', 'stock forecast',
        'what gf score', 'investors', 'wall street', 'trading',
        'analyst', 'reiterates', 'downgrades', 'upgrades',
        'market cap', 'valuation check', 'bull case', 'bear case',
        'losing streak', 'pullback', 'earnings multiple',
    ]
    is_stock_article = any(sw in text_lower for sw in STOCK_NOISE_WORDS)

    # Stock articles should be categorized as 'news' or 'earnings', not business events
    if is_stock_article:
        earnings_words = ['earnings', 'revenue', 'quarterly', 'fiscal', 'q1', 'q2', 'q3', 'q4',
                         'annual report', 'eps', 'guidance', 'forecast', 'outlook']
        if any(ew in text_lower for ew in earnings_words):
            return 'earnings'
        return 'news'

    # ── Category detection with compound keywords (order matters) ────
    # More specific categories first to avoid false positives
    categories = [
        ('acquisition', [
            'acquire', 'acquisition', 'acquires', 'acquired',
            'merge with', 'merger', 'buyout', 'takeover', 'take over',
            'to buy', 'has bought', 'purchasing',
        ]),
        ('funding', [
            'raises', 'raised', 'series a', 'series b', 'series c', 'series d',
            'series e', 'series f', 'funding round', 'seed round',
            'venture capital', 'ipo', 'initial public offering',
            'growth investment', 'capital raise',
        ]),
        ('product_launch', [
            'launches', 'launched', 'launch of', 'new product',
            'introduces', 'unveils', 'unveiled', 'release', 'released',
            'now available', 'rolls out', 'rolled out', 'general availability',
            'new feature', 'platform update', 'version',
        ]),
        ('partnership', [
            'partners with', 'partnership', 'collaboration with',
            'alliance', 'joint venture', 'integrates with', 'integration with',
            'teams up', 'teamed up',
        ]),
        ('expansion', [
            'expands into', 'expanding to', 'new market',
            'opens office', 'new headquarters', 'international expansion',
            'enters', 'entering', 'new region',
        ]),
        ('leadership', [
            'new ceo', 'new cto', 'new cfo', 'appoints', 'appointed',
            'names new', 'hires new', 'steps down', 'resigns',
            'executive', 'board of directors', 'chief',
        ]),
        ('pricing_change', [
            'new pricing', 'price increase', 'price cut', 'pricing change',
            'new plan', 'new tier', 'subscription change', 'pricing model',
            'raises prices', 'lowers prices', 'free tier',
        ]),
        ('hiring', [
            'hiring spree', 'hiring', 'job openings', 'job posting',
            'recruiting', 'talent acquisition', 'we are hiring',
            'open positions', 'career', 'headcount',
        ]),
        ('technology', [
            'ai', 'machine learning', 'artificial intelligence',
            'cloud', 'platform', 'innovation', 'patent', 'open source',
            'infrastructure', 'api', 'sdk', 'developer',
        ]),
        ('legal', [
            'lawsuit', 'sued', 'sues', 'antitrust', 'regulation',
            'compliance', 'fine', 'penalty', 'investigation',
            'data breach', 'privacy',
        ]),
        ('marketing', [
            'campaign', 'brand', 'rebrand', 'advertising',
            'conference', 'event', 'sponsorship',
        ]),
    ]

    for category, keywords in categories:
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
