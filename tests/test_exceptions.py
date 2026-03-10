"""Tests for exception hierarchy."""

from __future__ import annotations

from linkedinscrape.exceptions import (
    AuthenticationError,
    CookieExpiredError,
    LinkedInError,
    ParsingError,
    ProfileNotFoundError,
    RateLimitError,
    RequestError,
)


class TestExceptionHierarchy:
    def test_all_inherit_from_base(self):
        assert issubclass(AuthenticationError, LinkedInError)
        assert issubclass(CookieExpiredError, LinkedInError)
        assert issubclass(ProfileNotFoundError, LinkedInError)
        assert issubclass(RateLimitError, LinkedInError)
        assert issubclass(RequestError, LinkedInError)
        assert issubclass(ParsingError, LinkedInError)

    def test_base_is_exception(self):
        assert issubclass(LinkedInError, Exception)

    def test_profile_not_found_has_username(self):
        exc = ProfileNotFoundError("testuser")
        assert exc.username == "testuser"
        assert "testuser" in str(exc)

    def test_request_error_has_status_code(self):
        exc = RequestError(404, "Not Found")
        assert exc.status_code == 404
        assert "404" in str(exc)
        assert "Not Found" in str(exc)

    def test_request_error_no_message(self):
        exc = RequestError(500)
        assert "500" in str(exc)

    def test_catchable_as_base(self):
        try:
            raise ProfileNotFoundError("x")
        except LinkedInError as e:
            assert isinstance(e, ProfileNotFoundError)

    def test_cookie_expired_not_auth_error(self):
        """CookieExpiredError and AuthenticationError are siblings, not parent-child."""
        assert not issubclass(CookieExpiredError, AuthenticationError)
        assert not issubclass(AuthenticationError, CookieExpiredError)
