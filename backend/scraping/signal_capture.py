"""
Signal capture modules for real-time competitive intelligence.
Each module scrapes actual data from public sources.
"""
import hashlib
import logging
import re
from datetime import timedelta
from difflib import unified_diff
from urllib.parse import quote_plus

from . import http as requests
from bs4 import BeautifulSoup
from django.utils import timezone

from api.models import Company, Signal, PricingSnapshot, DataPoint

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


# ========================================================================
# 1. JOB POSTING TRACKER
# ========================================================================

ROLE_KEYWORDS = {
    'engineering': ['engineer', 'developer', 'sre', 'devops', 'architect', 'coder', 'programmer', 'backend', 'frontend', 'fullstack', 'full-stack', 'infrastructure', 'platform'],
    'ai_ml': ['machine learning', 'ai ', 'artificial intelligence', 'data scientist', 'nlp', 'deep learning', 'llm', 'ml engineer', 'computer vision'],
    'sales': ['sales', 'account executive', 'business development', 'bdr', 'sdr', 'revenue', 'deal', 'quota'],
    'marketing': ['marketing', 'growth', 'brand', 'content', 'seo', 'demand gen', 'pr ', 'communications'],
    'product': ['product manager', 'product design', 'ux', 'ui ', 'product lead', 'product director'],
    'data': ['data engineer', 'data analyst', 'analytics', 'business intelligence', 'data platform'],
    'security': ['security', 'infosec', 'compliance', 'privacy', 'gdpr', 'soc'],
    'support': ['customer success', 'support', 'solutions engineer', 'implementation'],
    'executive': ['vice president', 'vp ', 'c-suite', 'chief', 'director', 'head of', 'svp', 'evp'],
}

SENIORITY_KEYWORDS = {
    'c_level': ['ceo', 'cto', 'cfo', 'coo', 'ciso', 'cro', 'chief'],
    'vp': ['vice president', 'vp ', 'svp', 'evp'],
    'director': ['director', 'head of'],
    'senior': ['senior', 'sr.', 'sr ', 'lead', 'principal', 'staff'],
    'mid': ['manager', 'mid-level'],
    'entry': ['junior', 'jr.', 'jr ', 'associate', 'intern', 'entry'],
}


def track_job_postings(company):
    """Scrape job postings for a company from Google Jobs via news search."""
    signals = []
    name = company.name

    # Search for job postings via Bing News
    queries = [
        f'{name} hiring jobs',
        f'{name} careers job openings',
        f'{name} job posting',
    ]

    all_job_titles = []

    for query in queries[:2]:
        try:
            encoded = quote_plus(query)
            url = f'https://www.bing.com/news/search?q={encoded}&format=RSS'
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                for item in soup.find_all('item')[:10]:
                    title = item.find('title')
                    desc = item.find('description')
                    link = item.find('link')
                    if title:
                        title_text = title.get_text(strip=True)
                        desc_text = desc.get_text(strip=True) if desc else ''
                        combined = (title_text + ' ' + desc_text).lower()

                        # Classify role type
                        role_type = _classify_role(combined)
                        seniority = _classify_seniority(combined)

                        all_job_titles.append({
                            'title': title_text,
                            'role_type': role_type,
                            'seniority': seniority,
                            'url': link.get_text(strip=True) if link else '',
                        })
        except Exception as e:
            logger.warning(f"Job tracking search failed for {name}: {e}")

    # Also try to scrape the company's careers page directly
    if company.domain:
        domain = company.domain.rstrip('/')
        if not domain.startswith('http'):
            domain = f'https://{domain}'

        for path in ['/careers', '/jobs', '/careers/open-positions', '/about/careers']:
            try:
                resp = requests.get(f'{domain}{path}', headers=HEADERS, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    # Look for job listing elements
                    job_elements = soup.find_all(['a', 'div', 'li'], string=re.compile(r'(engineer|manager|director|analyst|designer|specialist)', re.I))
                    for el in job_elements[:15]:
                        text = el.get_text(strip=True)
                        if len(text) > 5 and len(text) < 200:
                            all_job_titles.append({
                                'title': text,
                                'role_type': _classify_role(text.lower()),
                                'seniority': _classify_seniority(text.lower()),
                                'url': f'{domain}{path}',
                            })
                    break
            except Exception:
                continue

    # Deduplicate and create signals
    seen = set()
    for job in all_job_titles:
        key = job['title'][:80].lower().strip()
        if key in seen or len(key) < 5:
            continue
        seen.add(key)

        # Check for duplicates in DB
        exists = Signal.objects.filter(
            company=company,
            signal_type='job_posting',
            title__iexact=job['title'][:500],
        ).exists()

        if not exists:
            signal = Signal.objects.create(
                company=company,
                signal_type='job_posting',
                title=job['title'][:500],
                role_type=job['role_type'],
                seniority_level=job['seniority'],
                source_url=job.get('url', ''),
                strength=0.6 if job['seniority'] in ['c_level', 'vp', 'director'] else 0.4,
            )
            signals.append(signal)

    # Calculate velocity - compare with previous period
    now = timezone.now()
    recent = Signal.objects.filter(company=company, signal_type='job_posting', captured_at__gte=now - timedelta(days=30)).count()
    previous = Signal.objects.filter(company=company, signal_type='job_posting', captured_at__gte=now - timedelta(days=60), captured_at__lt=now - timedelta(days=30)).count()

    velocity = 0
    if previous > 0:
        velocity = (recent - previous) / previous
    elif recent > 0:
        velocity = 1.0

    # Update velocity on recent signals
    Signal.objects.filter(company=company, signal_type='job_posting', captured_at__gte=now - timedelta(days=7)).update(velocity=velocity)

    return signals


# ========================================================================
# 2. PATENT FILING MONITOR
# ========================================================================

def track_patent_filings(company):
    """Search for recent patent filings via Google Patents / news."""
    signals = []
    name = company.name

    # Search for patent news
    queries = [
        f'{name} patent filing',
        f'{name} patent application',
        f'{name} invention patent',
    ]

    for query in queries[:2]:
        try:
            encoded = quote_plus(query)
            url = f'https://www.bing.com/news/search?q={encoded}&format=RSS'
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                for item in soup.find_all('item')[:8]:
                    title = item.find('title')
                    desc = item.find('description')
                    link = item.find('link')
                    if title:
                        title_text = title.get_text(strip=True)
                        desc_text = desc.get_text(strip=True) if desc else ''
                        combined = (title_text + ' ' + desc_text).lower()

                        # Only include if actually patent-related
                        if any(kw in combined for kw in ['patent', 'filing', 'invention', 'intellectual property', 'ip ']):
                            # Classify patent category
                            cat = _classify_patent_category(combined)

                            exists = Signal.objects.filter(
                                company=company,
                                signal_type='patent_filing',
                                title__iexact=title_text[:500],
                            ).exists()

                            if not exists:
                                signal = Signal.objects.create(
                                    company=company,
                                    signal_type='patent_filing',
                                    title=title_text[:500],
                                    description=desc_text[:1000],
                                    patent_category=cat,
                                    source_url=link.get_text(strip=True) if link else '',
                                    strength=0.7,
                                )
                                signals.append(signal)
        except Exception as e:
            logger.warning(f"Patent search failed for {name}: {e}")

    return signals


# ========================================================================
# 3. EARNINGS CALL NLP — KEYWORD FREQUENCY TRACKING
# ========================================================================

TRACKED_KEYWORDS = [
    'ai', 'artificial intelligence', 'machine learning', 'enterprise',
    'international', 'global', 'expansion', 'growth', 'platform',
    'partnership', 'acquisition', 'innovation', 'cloud', 'security',
    'automation', 'agent', 'revenue', 'margin', 'profitability',
    'customer', 'retention', 'churn', 'competitive', 'market share',
]


def track_earnings_keywords(company):
    """Search for earnings call transcripts and track keyword frequency."""
    signals = []
    name = company.name

    # Search for earnings transcripts
    queries = [
        f'{name} earnings call transcript',
        f'{name} quarterly results earnings',
        f'{name} investor call Q',
    ]

    for query in queries[:2]:
        try:
            encoded = quote_plus(query)
            url = f'https://www.bing.com/news/search?q={encoded}&format=RSS'
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                for item in soup.find_all('item')[:5]:
                    title = item.find('title')
                    desc = item.find('description')
                    link = item.find('link')
                    if title:
                        title_text = title.get_text(strip=True)
                        desc_text = desc.get_text(strip=True) if desc else ''
                        combined = (title_text + ' ' + desc_text).lower()

                        if any(kw in combined for kw in ['earnings', 'quarterly', 'fiscal', 'revenue', 'results']):
                            # Count keyword mentions
                            keyword_counts = {}
                            for kw in TRACKED_KEYWORDS:
                                count = combined.count(kw)
                                if count > 0:
                                    keyword_counts[kw] = count

                            # Determine quarter
                            quarter = _detect_quarter(combined)

                            if keyword_counts:
                                # Create a signal for each notable keyword
                                top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]

                                for kw, count in top_keywords:
                                    exists = Signal.objects.filter(
                                        company=company,
                                        signal_type='earnings_keyword',
                                        keyword=kw,
                                        quarter=quarter,
                                    ).exists()

                                    if not exists:
                                        signal = Signal.objects.create(
                                            company=company,
                                            signal_type='earnings_keyword',
                                            title=f'{name} earnings: "{kw}" mentioned {count}x',
                                            description=f'In the {quarter} earnings discussion, "{kw}" appeared {count} time(s). Source: {title_text}',
                                            keyword=kw,
                                            keyword_count=count,
                                            quarter=quarter,
                                            source_url=link.get_text(strip=True) if link else '',
                                            strength=min(0.9, 0.3 + count * 0.1),
                                        )
                                        signals.append(signal)
        except Exception as e:
            logger.warning(f"Earnings search failed for {name}: {e}")

    return signals


# ========================================================================
# 4. PRICING PAGE DIFF TRACKER
# ========================================================================

def track_pricing_page(company):
    """Take a snapshot of a company's pricing page and detect changes."""
    if not company.domain:
        return None

    domain = company.domain.rstrip('/')
    if not domain.startswith('http'):
        domain = f'https://{domain}'

    pricing_url = f'{domain}/pricing'

    try:
        resp = requests.get(pricing_url, headers=HEADERS, timeout=15, allow_redirects=True)
        if resp.status_code != 200:
            # Try alternate paths
            for alt in ['/plans', '/pricing-plans', '/price']:
                resp = requests.get(f'{domain}{alt}', headers=HEADERS, timeout=10, allow_redirects=True)
                if resp.status_code == 200:
                    pricing_url = f'{domain}{alt}'
                    break

        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.content, 'html.parser')

        # Remove scripts, styles, nav, footer
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'noscript']):
            tag.decompose()

        body = soup.find('body')
        text_content = body.get_text(separator='\n', strip=True) if body else ''
        # Clean up excessive whitespace
        text_content = re.sub(r'\n{3,}', '\n\n', text_content)

        # Extract pricing signals
        plan_names = _extract_plan_names(text_content)
        prices = _extract_prices(text_content)

        content_hash = hashlib.sha256(text_content.encode()).hexdigest()

        # Get previous snapshot
        prev_snapshot = PricingSnapshot.objects.filter(company=company).first()

        has_changed = False
        diff_text = ''

        if prev_snapshot:
            if prev_snapshot.content_hash != content_hash:
                has_changed = True
                # Generate diff
                old_lines = prev_snapshot.content_text.splitlines()
                new_lines = text_content.splitlines()
                diff_lines = list(unified_diff(old_lines, new_lines, lineterm='', n=2))
                diff_text = '\n'.join(diff_lines[:200])  # Limit diff size

                # Create a signal for the pricing change
                Signal.objects.create(
                    company=company,
                    signal_type='pricing_change',
                    title=f'{company.name} pricing page changed',
                    description=f'Detected changes on {company.name}\'s pricing page. Plans: {", ".join(plan_names[:5])}. Changes detected in page content.',
                    diff_summary=diff_text[:2000],
                    old_snapshot=prev_snapshot.content_text[:3000],
                    new_snapshot=text_content[:3000],
                    source_url=pricing_url,
                    strength=0.8,
                    metadata={
                        'old_plans': prev_snapshot.plan_names,
                        'new_plans': plan_names,
                        'old_prices': prev_snapshot.prices,
                        'new_prices': prices,
                    },
                )

        # Save snapshot
        snapshot = PricingSnapshot.objects.create(
            company=company,
            url=pricing_url,
            content_text=text_content[:10000],
            content_html=str(resp.content[:20000]),
            content_hash=content_hash,
            has_changed=has_changed,
            diff_from_previous=diff_text[:5000],
            plan_names=plan_names,
            prices=prices,
        )

        return snapshot

    except Exception as e:
        logger.error(f"Pricing page tracking failed for {company.name}: {e}")
        return None


# ========================================================================
# HELPER FUNCTIONS
# ========================================================================

def _classify_role(text):
    """Classify a job title into a role category."""
    for role, keywords in ROLE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return role
    return 'other'


def _classify_seniority(text):
    """Classify seniority level from job title."""
    for level, keywords in SENIORITY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return level
    return 'mid'


def _classify_patent_category(text):
    """Classify patent into technology category."""
    categories = {
        'AI/ML': ['artificial intelligence', 'machine learning', 'neural network', 'deep learning', 'nlp', 'computer vision'],
        'Cloud/Infrastructure': ['cloud', 'server', 'infrastructure', 'distributed', 'container', 'kubernetes'],
        'Security': ['security', 'encryption', 'authentication', 'privacy', 'cybersec'],
        'Data/Analytics': ['data processing', 'analytics', 'database', 'data warehouse', 'etl'],
        'UI/UX': ['user interface', 'user experience', 'display', 'interaction'],
        'Blockchain': ['blockchain', 'distributed ledger', 'smart contract', 'crypto'],
        'IoT': ['internet of things', 'iot', 'sensor', 'edge computing'],
    }
    for cat, keywords in categories.items():
        if any(kw in text for kw in keywords):
            return cat
    return 'General Technology'


def _detect_quarter(text):
    """Detect which quarter is being discussed."""
    import re
    now = timezone.now()

    q_match = re.search(r'q([1-4])\s*(?:20)?(\d{2})', text, re.IGNORECASE)
    if q_match:
        q = q_match.group(1)
        year = q_match.group(2)
        return f'Q{q} 20{year}'

    return ''  # Unknown reporting quarter must stay unknown.


def _extract_plan_names(text):
    """Extract pricing plan names from page text."""
    plans = []
    common_plans = ['free', 'starter', 'basic', 'pro', 'professional', 'business',
                    'enterprise', 'team', 'premium', 'plus', 'growth', 'scale',
                    'standard', 'advanced', 'unlimited', 'individual']
    text_lower = text.lower()
    for plan in common_plans:
        if plan in text_lower:
            plans.append(plan.title())
    return plans


def _extract_prices(text):
    """Extract pricing values from page text."""
    prices = []
    # Match patterns like $9.99, $99/mo, $199/month, $49/user
    price_patterns = re.findall(r'\$[\d,]+(?:\.\d{2})?(?:\s*/\s*(?:mo|month|year|yr|user|seat))?', text, re.I)
    for p in price_patterns[:10]:
        if p not in prices:
            prices.append(p)
    return prices


# ========================================================================
# MAIN CAPTURE FUNCTION
# ========================================================================

def capture_all_signals(company_id):
    """Run all signal capture modules for a company."""
    company = Company.objects.get(id=company_id)
    results = {
        'job_postings': 0,
        'patent_filings': 0,
        'earnings_keywords': 0,
        'pricing_snapshot': False,
        'errors': {},
    }

    try:
        jobs = track_job_postings(company)
        results['job_postings'] = len(jobs)
    except Exception as e:
        logger.error(f"Job tracking failed for {company.name}: {e}")
        results['errors']['job_postings'] = 'Collection failed; check server logs.'

    try:
        patents = track_patent_filings(company)
        results['patent_filings'] = len(patents)
    except Exception as e:
        logger.error(f"Patent tracking failed for {company.name}: {e}")
        results['errors']['patent_filings'] = 'Collection failed; check server logs.'

    try:
        earnings = track_earnings_keywords(company)
        results['earnings_keywords'] = len(earnings)
    except Exception as e:
        logger.error(f"Earnings tracking failed for {company.name}: {e}")
        results['errors']['earnings_keywords'] = 'Collection failed; check server logs.'

    try:
        snapshot = track_pricing_page(company)
        results['pricing_snapshot'] = snapshot is not None
    except Exception as e:
        logger.error(f"Pricing tracking failed for {company.name}: {e}")
        results['errors']['pricing_snapshot'] = 'Collection failed; check server logs.'

    return results
