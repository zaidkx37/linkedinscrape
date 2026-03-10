"""Exception hierarchy for linkedinscrape."""

from __future__ import annotations


class LinkedInError(Exception):
    """Base exception for all linkedinscrape errors."""


class AuthenticationError(LinkedInError):
    """Missing or invalid authentication cookies at startup."""


class CookieExpiredError(LinkedInError):
    """Session cookies expired mid-use (HTTP 401/403 from LinkedIn)."""


class ProfileNotFoundError(LinkedInError):
    """Profile does not exist or is inaccessible."""

    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"Profile not found or empty top card for '{username}'")


class RateLimitError(LinkedInError):
    """LinkedIn rate limit hit (HTTP 429)."""


class RequestError(LinkedInError):
    """HTTP request failed."""

    def __init__(self, status_code: int, message: str = "") -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}" if message else f"HTTP {status_code}")


class ParsingError(LinkedInError):
    """Failed to parse API response."""
