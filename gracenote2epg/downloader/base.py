"""
gracenote2epg.downloader.base - HTTP download engine

Handles low-level HTTP downloads with WAF protection, adaptive delays, connection reuse,
and intelligent retry logic. This is the core HTTP engine used by specialized downloaders.
"""

import json
import logging
import random
import time
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3


class OptimizedDownloader:
    """HTTP download engine with WAF protection and adaptive delays"""

    def __init__(self, base_delay: float = 1.0, min_delay: float = 0.5):
        self.session: Optional[requests.Session] = None
        self.user_agents = [
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ]
        self.last_request_time = 0
        self.base_delay = base_delay
        self.min_delay = min_delay
        self.current_delay = base_delay
        self.consecutive_failures = 0
        self.waf_blocks = 0
        self.total_requests = 0
        self.current_ua_index = 0

        # Initialize session
        self.init_session()

    def init_session(self):
        """Initialize optimized session with forced connection reuse"""
        if self.session:
            self.session.close()

        self.session = requests.Session()

        # Realistic headers with forced Keep-Alive
        base_headers = {
            "Accept": "application/json, text/html, application/xhtml+xml, */*",
            "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Keep-Alive": "timeout=60, max=100",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        self.session.headers.update(base_headers)

        # Optimized configuration for connection reuse
        retry_strategy = Retry(total=0, backoff_factor=0, status_forcelist=[])  # Don't auto-retry

        # Optimized adapter with minimal connection pool
        adapter = HTTPAdapter(
            pool_connections=1,  # Single connection pool
            pool_maxsize=1,  # Single connection in pool
            max_retries=retry_strategy,
            pool_block=True,  # Block if pool full to force reuse
        )

        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Configure urllib3 for persistence
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Set initial User-Agent
        self.rotate_user_agent()
        logging.debug("HTTP engine initialized with persistent connections")

    def rotate_user_agent(self):
        """Rotate User-Agent intelligently"""
        self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
        new_ua = self.user_agents[self.current_ua_index]
        self.session.headers.update({"User-Agent": new_ua})
        logging.debug("  User-Agent rotated: %s", new_ua[:50] + "...")

    def adaptive_delay(self):
        """Apply adaptive delay between requests"""
        # Calculate adaptive delay
        if self.consecutive_failures > 2:
            self.current_delay = min(self.base_delay * (1.5**self.consecutive_failures), 15.0)
        elif self.consecutive_failures == 0:
            self.current_delay = max(self.min_delay, self.current_delay * 0.95)

        # Add random variation
        delay = self.current_delay + random.uniform(-0.2, 0.5)
        delay = max(self.min_delay, delay)

        # Respect delay since last request
        elapsed = time.time() - self.last_request_time
        if elapsed < delay:
            sleep_time = delay - elapsed
            logging.debug(
                "  Adaptive delay: %.2fs (failures: %d)", sleep_time, self.consecutive_failures
            )
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def is_waf_blocked(self, response_text: str) -> bool:
        """Detect WAF blocking"""
        waf_indicators = [
            "Human Verification",
            "captcha-container",
            "AwsWafIntegration",
            "403 Forbidden",
            "Access Denied",
            "challenge.js",
        ]
        return any(indicator in response_text for indicator in waf_indicators)

    def handle_waf_block(self, extra_delay_range: tuple = (3, 8)):
        """Handle WAF blocking with appropriate backoff"""
        self.waf_blocks += 1
        self.consecutive_failures += 1
        extra_delay = random.uniform(*extra_delay_range)
        logging.warning("  WAF block detected, backing off %.1fs...", extra_delay)
        time.sleep(extra_delay)
        if self.total_requests % 10 == 0:  # Rotate occasionally after blocks
            self.rotate_user_agent()

    def download_with_retry_urllib(
        self,
        url: str,
        data: Optional[bytes] = None,
        max_retries: int = 3,
        timeout: Optional[int] = None,
    ) -> Optional[bytes]:
        """Download using urllib (for series details) with intelligent retry and WAF handling"""
        self.total_requests += 1

        # Adaptive timeouts based on history
        if timeout is None:
            if self.consecutive_failures == 0:
                timeout = 6  # Fast if everything is OK
            elif self.consecutive_failures == 1:
                timeout = 10  # Medium after 1 failure
            else:
                timeout = 15  # Longer if repeated problems

        # Periodic User-Agent rotation
        if self.total_requests % 25 == 0:
            self.rotate_user_agent()

        for attempt in range(max_retries):
            self.adaptive_delay()

            current_timeout = timeout + (attempt * 2)  # Increase timeout on each retry
            current_ua = self.user_agents[self.current_ua_index]

            # Build display URL with parameters
            if data:
                display_url = f'{url}?{data.decode("utf-8") if isinstance(data, bytes) else data}'
            else:
                display_url = url

            logging.debug(
                "  Attempt %d/%d: %s (timeout: %ds)",
                attempt + 1,
                max_retries,
                display_url[:100] + "..." if len(display_url) > 100 else display_url,
                current_timeout,
            )

            try:
                # Use urllib exactly like the original working version
                url_request = urllib.request.Request(
                    url, data=data, headers={"User-Agent": current_ua}
                )
                json_content = urllib.request.urlopen(url_request, timeout=current_timeout).read()

                if json_content and len(json_content) > 10:
                    # Check that it's valid JSON
                    try:
                        json.loads(json_content)
                        self.consecutive_failures = max(0, self.consecutive_failures - 1)
                        logging.debug("  Success: %d bytes received", len(json_content))
                        return json_content
                    except json.JSONDecodeError:
                        logging.warning("  Invalid JSON received on attempt %d", attempt + 1)
                        self.consecutive_failures += 1
                else:
                    logging.warning(
                        "  Empty/small response on attempt %d: %d bytes",
                        attempt + 1,
                        len(json_content) if json_content else 0,
                    )
                    self.consecutive_failures += 1

            except urllib.error.HTTPError as e:
                if e.code == 403:
                    self.handle_waf_block()
                    continue
                logging.warning("  HTTP Error %d on attempt %d: %s", e.code, attempt + 1, e.reason)
                if e.code in [404, 410]:
                    break  # Don't retry for permanent errors
                self.consecutive_failures += 1

            except urllib.error.URLError as e:
                logging.warning("  URL Error on attempt %d: %s", attempt + 1, str(e.reason))
                self.consecutive_failures += 1

            except Exception as e:
                logging.warning("  Unexpected error on attempt %d: %s", attempt + 1, str(e))
                self.consecutive_failures += 1

            # Wait before retry
            if attempt < max_retries - 1:
                retry_delay = random.uniform(1, 3)
                time.sleep(retry_delay)

        # All retries failed
        logging.warning("  All %d attempts failed", max_retries)
        return None

    def download_with_retry(
        self,
        url: str,
        method: str = "GET",
        data: Optional[str] = None,
        max_retries: int = 3,
        timeout: Optional[int] = None,
    ) -> Optional[bytes]:
        """Download with intelligent retry, adaptive timeouts and WAF handling (for guide)"""
        self.total_requests += 1

        # Adaptive timeouts based on history
        if timeout is None:
            if self.consecutive_failures == 0:
                timeout = 6  # Fast if everything is OK
            elif self.consecutive_failures == 1:
                timeout = 10  # Medium after 1 failure
            else:
                timeout = 15  # Longer if repeated problems

        # Periodic User-Agent rotation
        if self.total_requests % 25 == 0:
            self.rotate_user_agent()

        for attempt in range(max_retries):
            self.adaptive_delay()

            current_timeout = timeout + (attempt * 2)  # Increase timeout on each retry

            # Build display URL with parameters for POST
            if method.upper() == "POST" and data:
                display_url = f"{url}?{data}"
            else:
                display_url = url

            logging.debug(
                "  Attempt %d/%d: %s (timeout: %ds)",
                attempt + 1,
                max_retries,
                display_url[:100] + "..." if len(display_url) > 100 else display_url,
                current_timeout,
            )

            try:
                if method.upper() == "POST":
                    response = self.session.post(
                        url, data=data, timeout=current_timeout, allow_redirects=False
                    )
                else:
                    response = self.session.get(url, timeout=current_timeout, allow_redirects=False)

                # Check WAF blocking
                if response.status_code == 403:
                    self.handle_waf_block()
                    continue

                if self.is_waf_blocked(response.text):
                    self.handle_waf_block((5, 12))  # Longer delay for CAPTCHA
                    continue

                # Check response status
                if response.status_code == 200:
                    self.consecutive_failures = max(0, self.consecutive_failures - 1)
                    logging.debug("  Success: %d bytes received", len(response.content))
                    return response.content
                else:
                    logging.warning("  HTTP %d received", response.status_code)
                    if response.status_code in [404, 410]:
                        break  # Don't retry for permanent errors
                    self.consecutive_failures += 1

            except requests.exceptions.Timeout:
                logging.warning("  Timeout (%ds) on attempt %d", current_timeout, attempt + 1)
                self.consecutive_failures += 1

            except requests.exceptions.ConnectionError as e:
                logging.warning("  Connection error on attempt %d: %s", attempt + 1, str(e))
                self.consecutive_failures += 1
                # Force reconnection on connection errors
                self.session.close()
                self.init_session()

            except requests.exceptions.RequestException as e:
                logging.warning("  Request error on attempt %d: %s", attempt + 1, str(e))
                self.consecutive_failures += 1

            # Wait before retry
            if attempt < max_retries - 1:
                retry_delay = random.uniform(1, 3)
                time.sleep(retry_delay)

        # All retries failed
        logging.warning("  All %d attempts failed", max_retries)
        return None

    def close(self):
        """Clean shutdown"""
        if self.session:
            self.session.close()
            self.session = None
            logging.debug("HTTP engine closed")

    def get_statistics(self) -> Dict[str, Any]:
        """Get download statistics"""
        return {
            "total_requests": self.total_requests,
            "waf_blocks": self.waf_blocks,
            "consecutive_failures": self.consecutive_failures,
            "current_delay": self.current_delay,
        }

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
