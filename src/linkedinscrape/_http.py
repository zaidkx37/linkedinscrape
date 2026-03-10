"""HTTP transport layer with TLS fingerprint spoofing, rate limiting, and proxy rotation."""

from __future__ import annotations

import logging
import random
import time
from typing import Any

from curl_cffi.requests import Session

from . import _endpoints as ep
from .exceptions import CookieExpiredError, RateLimitError, RequestError

logger = logging.getLogger(__name__)

# Lightweight LinkedIn endpoint — used to validate cookies.
_COOKIE_CHECK_URL = "https://www.linkedin.com/voyager/api/me"

# Browser to impersonate for TLS fingerprinting (JA3/JA4).
_IMPERSONATE = "chrome136"  # type: ignore[assignment]


class HTTPClient:
    """
    Low-level HTTP client for the LinkedIn Voyager API.

    Uses ``curl_cffi`` with Chrome TLS impersonation so that the TLS
    fingerprint matches a real browser.  Plain ``requests`` gets detected
    and redirected to the login page.
    """

    def __init__(
        self,
        li_at: str,
        csrf_token: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        delay: float = 1.5,
        proxies: list[str] | None = None,
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._delay = delay
        self._last_request_time: float = 0

        # Proxy rotation state — guard against a bare string being passed
        self._proxy_list: list[str] = (
            [proxies] if isinstance(proxies, str)
            else list(proxies) if proxies
            else []
        )
        self._proxy_index = 0

        self._headers = ep.build_headers(csrf_token)
        self._cookies = ep.build_cookies(li_at, csrf_token)
        self._session = self._build_session()

    def _build_session(self) -> Session:
        session: Session = Session(impersonate=_IMPERSONATE)  # type: ignore[arg-type]
        session.headers.update(self._headers)
        for name, value in self._cookies.items():
            session.cookies.set(name, value, domain=".linkedin.com")
        return session

    # ── Proxy rotation ───────────────────────────────────────────────────

    @property
    def _current_proxy(self) -> str | None:
        if not self._proxy_list:
            return None
        return self._proxy_list[self._proxy_index % len(self._proxy_list)]

    def _rotate_proxy(self) -> None:
        if self._proxy_list:
            self._proxy_index = (self._proxy_index + 1) % len(self._proxy_list)
            logger.debug(
                "Rotated to proxy %d/%d", self._proxy_index + 1, len(self._proxy_list)
            )

    # ── Cookie validation ────────────────────────────────────────────────

    def check_cookies(self) -> bool:
        """
        Verify that the session cookies are still valid.

        Makes a lightweight call to the ``/me`` endpoint. Returns ``True`` if
        the cookies are accepted, raises :class:`CookieExpiredError` otherwise.
        """
        logger.debug("Validating session cookies ...")
        try:
            resp = self._session.get(
                _COOKIE_CHECK_URL,
                timeout=self._timeout,
                proxy=self._current_proxy,
                allow_redirects=False,
            )
        except Exception as exc:
            logger.warning("Cookie check request failed: %s", exc)
            raise CookieExpiredError(
                "Could not reach LinkedIn to validate cookies. Check your network "
                "connection and proxy settings."
            ) from exc

        if resp.status_code in (301, 302, 303, 307, 308):
            raise CookieExpiredError(
                "LinkedIn is redirecting (likely to login). Your cookies are expired. "
                "Log in to LinkedIn in your browser and copy fresh values."
            )
        if resp.status_code in (401, 403):
            raise CookieExpiredError(
                f"Session cookies are invalid or expired (HTTP {resp.status_code}). "
                "Log in to LinkedIn in your browser and copy fresh LI_AT and "
                "CSRF_TOKEN values."
            )
        if resp.status_code == 429:
            raise RateLimitError(
                "Rate limited during cookie check (HTTP 429). Try again later."
            )
        if resp.status_code >= 400:
            logger.warning("Unexpected status %d during cookie check", resp.status_code)
            return True  # Don't block on unexpected codes — let real requests fail

        logger.debug("Cookies are valid")
        return True

    # ── Rate limiting ────────────────────────────────────────────────────

    def _respect_rate_limit(self) -> None:
        """Wait with human-like jitter so requests aren't perfectly spaced."""
        elapsed = time.time() - self._last_request_time
        jittered_delay = self._delay * random.uniform(0.7, 1.3)
        if elapsed < jittered_delay:
            time.sleep(jittered_delay - elapsed)

    # ── Requests ─────────────────────────────────────────────────────────

    def get(self, url: str, label: str = "") -> dict[str, Any]:
        """Perform a GET request with rate limiting, proxy, and error handling."""
        self._respect_rate_limit()
        logger.debug("GET %s", label or url[:80])

        for attempt in range(1, self._max_retries + 1):
            try:
                resp = self._session.get(
                    url,
                    timeout=self._timeout,
                    proxy=self._current_proxy,
                    allow_redirects=False,
                )
                break
            except Exception as exc:
                if attempt < self._max_retries:
                    wait = 2 ** attempt + random.random()
                    logger.warning(
                        "  %s attempt %d failed (%s), retrying in %.1fs",
                        label, attempt, exc, wait,
                    )
                    time.sleep(wait)
                    continue
                raise RequestError(
                    0, f"Request failed after {self._max_retries} retries: {exc}"
                ) from exc

        self._last_request_time = time.time()

        if resp.status_code in (301, 302, 303, 307, 308):
            raise CookieExpiredError(
                f"LinkedIn redirected the API request (HTTP {resp.status_code}). "
                "This means your cookies are expired or invalid. Log in to "
                "LinkedIn in your browser and copy fresh values."
            )
        if resp.status_code == 401:
            raise CookieExpiredError(
                "Authentication failed (HTTP 401). Your li_at cookie has expired. "
                "Log in to LinkedIn in your browser and copy fresh values."
            )
        if resp.status_code == 403:
            raise CookieExpiredError(
                "Access denied (HTTP 403). Your cookies have expired or the CSRF "
                "token is invalid. Refresh your credentials."
            )
        if resp.status_code == 429:
            self._rotate_proxy()
            raise RateLimitError(
                "Rate limited by LinkedIn (HTTP 429). Increase the delay between "
                "requests or add proxies."
            )
        if resp.status_code >= 400:
            raise RequestError(resp.status_code, resp.text[:200])
        return resp.json()

    def safe_get(self, url: str, label: str) -> dict[str, Any] | None:
        """GET that returns None on failure instead of raising."""
        try:
            return self.get(url, label)
        except (CookieExpiredError, RateLimitError):
            raise
        except RequestError:
            logger.warning("  %s failed (request error)", label)
            return None
        except Exception as exc:
            logger.warning("  %s failed: %s", label, exc)
            return None

    def close(self) -> None:
        self._session.close()
