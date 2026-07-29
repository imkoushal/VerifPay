"""
VerifPay — URL Checker Service

Checks URLs against PhishTank API and Google Safe Browsing API in parallel.
Returns phishing status, threat type, and source for each URL found.
All checks have 5-second timeouts with graceful fallback.
"""

import re
import logging
import asyncio
from typing import Optional

import aiohttp

from app.config import settings
from app.models.schemas import URLCheckResult

logger = logging.getLogger(__name__)

# Regex patterns to extract URLs from text
_HTTP_URL = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)
_WWW_URL = re.compile(r'www\.[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)
_SUSPICIOUS_TLD_URL = re.compile(
    r'[a-zA-Z0-9][-a-zA-Z0-9]*\.(?:tk|xyz|ml|ga|cf|gq|top|buzz|club|info|online|site|work|click|link|win|download|stream|racing|review|accountant|date|trade|loan|bid|cricket)(?:/[^\s]*)?',
    re.IGNORECASE,
)

# Known suspicious TLDs commonly used in phishing
SUSPICIOUS_TLDS = {
    ".tk", ".xyz", ".ml", ".ga", ".cf", ".gq", ".top", ".buzz",
    ".club", ".info", ".online", ".site", ".work", ".click",
    ".link", ".win", ".download", ".stream", ".racing",
}

# Timeout for all URL checks
URL_CHECK_TIMEOUT = 5  # seconds

# ─── Shared aiohttp session management ─────────────────────────
_session: aiohttp.ClientSession | None = None


async def get_session() -> aiohttp.ClientSession:
    """Get or create the shared aiohttp session."""
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


async def close_session():
    """Close the shared aiohttp session (call on app shutdown)."""
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None


def extract_urls(text: str) -> list[str]:
    """Extract all URLs from text using regex."""
    found = set()

    # Match http/https URLs
    for m in _HTTP_URL.finditer(text):
        found.add(m.group(0).rstrip(".,;:!?)"))

    # Match www. URLs
    for m in _WWW_URL.finditer(text):
        found.add("http://" + m.group(0).rstrip(".,;:!?)"))

    # Match suspicious TLD domains (no protocol)
    for m in _SUSPICIOUS_TLD_URL.finditer(text):
        raw = m.group(0).rstrip(".,;:!?)")
        if not raw.startswith(("http://", "https://")):
            raw = "http://" + raw
        found.add(raw)

    return list(found)


async def check_phishtank(url: str, session: aiohttp.ClientSession) -> Optional[URLCheckResult]:
    """
    Check URL against PhishTank API.
    Returns URLCheckResult if the URL is in PhishTank's database.
    """
    api_key = settings.PHISHTANK_API_KEY
    if not api_key:
        logger.debug("PhishTank API key not configured — skipping")
        return None

    try:
        payload = {
            "url": url,
            "format": "json",
            "app_key": api_key,
        }
        timeout = aiohttp.ClientTimeout(total=URL_CHECK_TIMEOUT)
        async with session.post(
            "https://checkurl.phishtank.com/checkurl/",
            data=payload,
            timeout=timeout,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                results = data.get("results", {})
                is_phishing = results.get("in_database", False) and results.get("valid", False)
                return URLCheckResult(
                    url=url,
                    is_phishing=is_phishing,
                    source="phishtank",
                    threat_type="phishing" if is_phishing else "none",
                )
    except asyncio.TimeoutError:
        logger.warning(f"PhishTank timeout for {url}")
    except Exception as e:
        logger.error(f"PhishTank check failed for {url}: {e}")

    return None


async def check_google_safe_browsing(url: str, session: aiohttp.ClientSession) -> Optional[URLCheckResult]:
    """
    Check URL against Google Safe Browsing API v4.
    Returns URLCheckResult if threats are found.
    """
    api_key = settings.GOOGLE_SAFE_BROWSING_API_KEY
    if not api_key:
        logger.debug("Google Safe Browsing API key not configured — skipping")
        return None

    try:
        payload = {
            "client": {
                "clientId": "verifpay",
                "clientVersion": "1.0.0",
            },
            "threatInfo": {
                "threatTypes": [
                    "MALWARE",
                    "SOCIAL_ENGINEERING",
                    "UNWANTED_SOFTWARE",
                    "POTENTIALLY_HARMFUL_APPLICATION",
                ],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url}],
            },
        }
        # NOTE: Google Safe Browsing v4 API requires the key as a URL query parameter.
        # There is no header-based alternative. This means the key may appear in proxy logs.
        api_url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}"
        timeout = aiohttp.ClientTimeout(total=URL_CHECK_TIMEOUT)

        async with session.post(api_url, json=payload, timeout=timeout) as resp:
            if resp.status == 200:
                data = await resp.json()
                matches = data.get("matches", [])
                if matches:
                    threat_type = matches[0].get("threatType", "UNKNOWN").lower()
                    return URLCheckResult(
                        url=url,
                        is_phishing=True,
                        source="google_safe_browsing",
                        threat_type=threat_type,
                    )
                else:
                    return URLCheckResult(
                        url=url,
                        is_phishing=False,
                        source="google_safe_browsing",
                        threat_type="none",
                    )
    except asyncio.TimeoutError:
        logger.warning(f"Google Safe Browsing timeout for {url}")
    except Exception as e:
        logger.error(f"Google Safe Browsing check failed for {url}: {e}")

    return None


async def check_suspicious_tld(url: str) -> URLCheckResult:
    """
    Heuristic check: flag URLs with known suspicious TLDs.
    This runs locally with no API call — always available as a fallback.
    """
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        domain = domain.lower()

        for tld in SUSPICIOUS_TLDS:
            if domain.endswith(tld):
                return URLCheckResult(
                    url=url,
                    is_phishing=True,
                    source="tld_heuristic",
                    threat_type=f"suspicious_tld ({tld})",
                )

        # Check for brand impersonation patterns
        suspicious_brands = ["sbi", "hdfc", "icici", "axis", "paytm", "phonepe", "gpay",
                             "amazon", "flipkart", "google", "netflix", "whatsapp",
                             "aadhaar", "incometax", "rbi", "npci", "fastag", "irctc"]
        for brand in suspicious_brands:
            # Flag if brand name appears in a domain with a non-official TLD
            official_tlds = (".com", ".in", ".co.in", ".org", ".gov.in", ".net.in", ".org.in", ".ac.in")
            if brand in domain and not domain.endswith(official_tlds):
                return URLCheckResult(
                    url=url,
                    is_phishing=True,
                    source="brand_impersonation_heuristic",
                    threat_type=f"suspected_brand_impersonation ({brand})",
                )

    except Exception as e:
        logger.error(f"TLD heuristic check failed: {e}")

    return URLCheckResult(
        url=url,
        is_phishing=False,
        source="tld_heuristic",
        threat_type="none",
    )


async def check_url(url: str) -> URLCheckResult:
    """
    Check a single URL against all available services in parallel.
    Returns the most informative result. Uses 5-second timeout per service.

    Priority: PhishTank > Google Safe Browsing > TLD Heuristic
    """
    session = await get_session()
    # Run all checks in parallel
    results = await asyncio.gather(
        check_phishtank(url, session),
        check_google_safe_browsing(url, session),
        check_suspicious_tld(url),
        return_exceptions=True,
    )

    # Filter out exceptions and None results
    valid_results = [r for r in results if isinstance(r, URLCheckResult)]

    # If any service flagged it as phishing, it's phishing
    for result in valid_results:
        if result.is_phishing:
            logger.info(f"URL flagged: {url} — {result.source}: {result.threat_type}")
            return result

    # If no service flagged it, return the best available clean result
    if valid_results:
        return valid_results[0]

    # Absolute fallback
    return URLCheckResult(
        url=url,
        is_phishing=False,
        source="fallback",
        threat_type="check_unavailable",
    )


async def check_urls(urls: list[str]) -> list[URLCheckResult]:
    """Check multiple URLs in parallel."""
    if not urls:
        return []

    tasks = [check_url(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return [r for r in results if isinstance(r, URLCheckResult)]
