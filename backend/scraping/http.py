"""Bounded public-web fetches with DNS pinning and redirect validation."""
import ipaddress
import socket
import time
from urllib.parse import urlsplit, urljoin
import requests
import urllib3

MAX_BYTES = 2 * 1024 * 1024


def resolve_public_url(url):
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Only public HTTP(S) URLs without credentials are allowed.')
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        if port not in (80, 443):
            raise ValueError('Only web ports 80 and 443 are allowed.')
        addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
        ips = {entry[4][0] for entry in addresses}
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise ValueError('Private, loopback, reserved and link-local destinations are blocked.')
        return parsed, port, sorted(ips)[0]
    except (OSError, ValueError) as exc:
        raise ValueError('URL must resolve exclusively to public web addresses.') from exc


def get(url, headers=None, timeout=15, allow_redirects=True):
    deadline = time.monotonic() + timeout
    for _ in range(6):
        parsed, port, address = resolve_public_url(url)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise requests.Timeout('Collection time limit exceeded')
        kwargs = {'host': address, 'port': port, 'timeout': urllib3.Timeout(total=remaining), 'maxsize': 1}
        if parsed.scheme == 'https':
            pool = urllib3.HTTPSConnectionPool(**kwargs, assert_hostname=parsed.hostname, server_hostname=parsed.hostname, cert_reqs='CERT_REQUIRED')
        else:
            pool = urllib3.HTTPConnectionPool(**kwargs)
        response = None
        try:
            request_headers = dict(headers or {})
            request_headers['Host'] = parsed.netloc
            target = (parsed.path or '/') + ('?' + parsed.query if parsed.query else '')
            response = pool.urlopen('GET', target,
                                    headers=request_headers, redirect=False, retries=False, preload_content=False)
            if response.status in (301, 302, 303, 307, 308) and allow_redirects:
                location = response.headers.get('Location')
                if not location:
                    raise requests.RequestException('Redirect has no destination')
                url = urljoin(url, location)
                continue
            body = bytearray()
            for chunk in response.stream(65536, decode_content=True):
                body.extend(chunk)
                if len(body) > MAX_BYTES or time.monotonic() > deadline:
                    raise requests.RequestException('Source exceeds collection size or time limit')
            result = requests.Response()
            result.status_code = response.status
            result.headers.update(response.headers)
            result._content = bytes(body)
            result.url = url
            result.encoding = requests.utils.get_encoding_from_headers(result.headers) or 'utf-8'
            return result
        finally:
            if response is not None:
                response.close()
            pool.close()
    raise requests.TooManyRedirects('Too many redirects')
