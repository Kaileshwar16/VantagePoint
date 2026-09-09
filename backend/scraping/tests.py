from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase
from .http import resolve_public_url, get
from .tasks import _parse_date
from .signal_capture import _detect_quarter


class CollectionTests(SimpleTestCase):
    def test_unknown_dates_stay_unknown(self):
        self.assertIsNone(_parse_date(None))
        self.assertIsNone(_parse_date('not a date'))
        self.assertIsNotNone(_parse_date('2025-01-02'))
        self.assertEqual(_detect_quarter('earnings report'), '')
        self.assertEqual(_detect_quarter('Q2 2025 earnings'), 'Q2 2025')

    def test_non_web_targets_blocked(self):
        for url in ['file:///etc/passwd', 'http://user:password@example.com', 'http://example.com:8080']:
            with self.assertRaises(ValueError):
                resolve_public_url(url)

    @patch('scraping.http.socket.getaddrinfo')
    def test_private_addresses_blocked(self, dns):
        for ip in ['127.0.0.1', '10.0.0.1', '169.254.169.254', '::1', '192.168.1.1']:
            dns.return_value = [(2, 1, 6, '', (ip, 80))]
            with self.assertRaises(ValueError): resolve_public_url('https://example.com')

    @patch('scraping.http.socket.getaddrinfo')
    def test_mixed_public_private_dns_blocked(self, dns):
        dns.return_value = [(2, 1, 6, '', ('8.8.8.8', 443)), (2, 1, 6, '', ('127.0.0.1', 443))]
        with self.assertRaises(ValueError): resolve_public_url('https://example.com')

    @patch('scraping.http.urllib3.HTTPSConnectionPool')
    @patch('scraping.http.socket.getaddrinfo')
    def test_connection_pinned_and_tls_hostname_preserved(self, dns, pool):
        dns.return_value = [(2, 1, 6, '', ('8.8.8.8', 443))]
        response = pool.return_value.urlopen.return_value
        response.status = 200
        response.headers = {}
        response.stream.return_value = [b'hello']
        self.assertEqual(get('https://example.com/report').text, 'hello')
        self.assertEqual(pool.call_args.kwargs['host'], '8.8.8.8')
        self.assertEqual(pool.call_args.kwargs['server_hostname'], 'example.com')

    @patch('scraping.http.urllib3.HTTPSConnectionPool')
    @patch('scraping.http.socket.getaddrinfo')
    def test_redirect_to_internal_address_blocked(self, dns, pool):
        dns.side_effect = [[(2, 1, 6, '', ('8.8.8.8', 443))], [(2, 1, 6, '', ('127.0.0.1', 80))]]
        response = pool.return_value.urlopen.return_value
        response.status = 302
        response.headers = {'Location': 'http://localhost/secret'}
        with self.assertRaises(ValueError): get('https://example.com')

    @patch('scraping.http.MAX_BYTES', 3)
    @patch('scraping.http.urllib3.HTTPSConnectionPool')
    @patch('scraping.http.socket.getaddrinfo')
    def test_large_response_blocked(self, dns, pool):
        import requests
        dns.return_value = [(2, 1, 6, '', ('8.8.8.8', 443))]
        response = pool.return_value.urlopen.return_value
        response.status = 200
        response.headers = {}
        response.stream.return_value = [b'too big']
        with self.assertRaises(requests.RequestException): get('https://example.com')

    @patch('scraping.simple_scraper.requests.get')
    def test_rss_preserves_publication_date(self, fetch):
        from .simple_scraper import _scrape_google_news_rss
        response = fetch.return_value
        response.status_code = 200
        response.content = b'<rss><channel><item><title>Example launches a new product</title><description>Example company announcement</description><link>https://example.com/news</link><pubDate>Tue, 02 Sep 2025 12:00:00 GMT</pubDate></item></channel></rss>'
        items = _scrape_google_news_rss('Example')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['published_at'], 'Tue, 02 Sep 2025 12:00:00 GMT')

    @patch('scraping.simple_scraper._scrape_bing_news', side_effect=RuntimeError('offline'))
    @patch('scraping.simple_scraper._scrape_google_news_rss', side_effect=RuntimeError('offline'))
    def test_all_news_sources_failing_is_not_success(self, google, bing):
        from .simple_scraper import scrape_company_news
        with self.assertRaises(RuntimeError): scrape_company_news('Example')
