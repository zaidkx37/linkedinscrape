"""LinkedIn profile scraper SDK — main client."""

from __future__ import annotations

import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from . import _endpoints as ep
from ._http import HTTPClient
from ._parsers import ProfileParser, extract_member_id_from_top_card
from .exceptions import AuthenticationError, CookieExpiredError, ProfileNotFoundError
from .models import LinkedInProfile

# Entity types that are scoped to a specific profile and can leak viewer data.
_PROFILE_SCOPED_TYPES = (
    "Position", "Education", "Skill", "Certification", "Project",
    "Language", "VolunteerExperience", "Honor", "Publication", "Course",
    "Patent", "TestScore", "Organization",
)


def _filter_entities_by_owner(
    entities: list[dict[str, Any]], profile_urn: str
) -> list[dict[str, Any]]:
    """Keep only entities that belong to *profile_urn*, plus shared/unscoped ones.

    LinkedIn API responses mix entities from the viewed profile AND the
    logged-in viewer.  Section entities (positions, educations, …) reference
    their owner via ``profileUrn``, ``*profile``, or their ``entityUrn``
    contains the member-id.  Entities without any owner reference (e.g.
    Company, School, Geo) are kept since they're shared lookups.
    """
    member_id = profile_urn.split("fsd_profile:")[-1] if "fsd_profile:" in profile_urn else ""
    result: list[dict[str, Any]] = []
    for e in entities:
        etype = e.get("$type", "")
        # Check if this is a profile-scoped entity type
        is_scoped = any(t in etype for t in _PROFILE_SCOPED_TYPES)
        if not is_scoped:
            result.append(e)
            continue
        # Keep if owner matches the target profile
        owner = (
            e.get("profileUrn")
            or e.get("*profile")
            or e.get("*profileUrn")
            or ""
        )
        entity_urn = e.get("entityUrn", "")
        if owner and member_id and member_id in owner:
            result.append(e)
        elif not owner and member_id and member_id in entity_urn:
            # Some entities embed the profile id in their own URN
            result.append(e)
        elif not owner and not member_id:
            result.append(e)
        elif not owner:
            # No owner reference — keep it (can't tell, better to include)
            result.append(e)
    return result

logger = logging.getLogger(__name__)


class LinkedIn:
    """
    LinkedIn profile scraper.

    Credentials are resolved automatically: explicit arguments take priority,
    then environment variables ``LI_AT`` / ``CSRF_TOKEN`` (a ``.env`` file is
    loaded automatically).  Cookies are validated on creation so you get an
    immediate error instead of a cryptic failure mid-scrape.

    Usage::

        from linkedinscrape import LinkedIn

        with LinkedIn() as li:
            profile = li.scrape("username")
            print(profile.full_name)

        # or without context manager
        li = LinkedIn()
        profile = li.scrape("username")
        li.close()

        # with proxy rotation
        li = LinkedIn(proxies=["http://p1:8080", "http://p2:8080"])

        # explicit credentials override env
        li = LinkedIn(li_at="...", csrf_token="...")
    """

    def __init__(
        self,
        li_at: str | None = None,
        csrf_token: str | None = None,
        *,
        delay: float = 1.5,
        timeout: float = 30.0,
        max_retries: int = 3,
        proxy: str | None = None,
        proxies: list[str] | None = None,
        proxy_file: str | Path | None = None,
        validate: bool = True,
        dotenv_path: str | Path | None = None,
    ) -> None:
        load_dotenv(dotenv_path)

        li_at = (li_at or os.getenv("LI_AT") or "").strip()
        csrf_token = (csrf_token or os.getenv("CSRF_TOKEN") or "").strip()

        if not li_at:
            raise AuthenticationError(
                "LI_AT cookie is required. Set it in your .env file or pass "
                "li_at='...' to the constructor."
            )
        if not csrf_token:
            raise AuthenticationError(
                "CSRF_TOKEN is required. Set it in your .env file or pass "
                "csrf_token='...' to the constructor. "
                "(Value of the JSESSIONID cookie without surrounding quotes.)"
            )

        # Resolve proxy list (explicit args > env var > none)
        env_proxy = os.getenv("PROXY", "").strip() or None
        resolved_proxies = self._resolve_proxies(
            proxy or env_proxy, proxies, proxy_file
        )

        self._delay = delay
        self._http = HTTPClient(
            li_at=li_at,
            csrf_token=csrf_token,
            timeout=timeout,
            max_retries=max_retries,
            delay=delay,
            proxies=resolved_proxies or None,
        )

        if validate:
            self._http.check_cookies()

    @staticmethod
    def _normalize_proxy(raw: str) -> str:
        """Convert ``host:port:user:pass`` to a URL if needed.

        If the value already looks like a URL (starts with ``http``/``socks``),
        it is returned as-is.  Otherwise the ``host:port:user:pass`` format
        used by SmartProxy / Decodo is converted to
        ``http://user:pass@host:port``.
        """
        raw = raw.strip()
        if raw.startswith(("http://", "https://", "socks")):
            return raw
        parts = raw.split(":")
        if len(parts) == 4:
            host, port, user, passwd = parts
            return f"http://{user}:{passwd}@{host}:{port}"
        if len(parts) == 2:
            return f"http://{parts[0]}:{parts[1]}"
        return f"http://{raw}"

    @classmethod
    def _resolve_proxies(
        cls,
        proxy: str | None,
        proxies: list[str] | str | None,
        proxy_file: str | Path | None,
    ) -> list[str]:
        """Build a flat proxy list from the various input sources."""
        # If a string was passed as `proxies`, treat it as a file path
        if isinstance(proxies, str):
            proxy_file = proxies
            proxies = None

        if proxies:
            return [cls._normalize_proxy(p) for p in proxies]

        if proxy_file:
            path = Path(proxy_file)
            if not path.exists():
                raise FileNotFoundError(f"Proxy file not found: {path}")
            lines = path.read_text(encoding="utf-8").splitlines()
            result = [
                cls._normalize_proxy(ln)
                for ln in lines
                if ln.strip() and not ln.strip().startswith("#")
            ]
            if not result:
                raise ValueError(f"Proxy file is empty: {path}")
            return result

        if proxy:
            return [cls._normalize_proxy(proxy)]

        return []

    # ── Scraping ─────────────────────────────────────────────────────────

    def scrape(self, username: str) -> LinkedInProfile:
        """
        Scrape a full LinkedIn profile by vanity name (the part after ``/in/``).

        Returns a :class:`LinkedInProfile` with all available sections populated.
        """
        logger.info("Scraping %s ...", username)
        raw_data = self._fetch_full_profile(username)
        parser = ProfileParser(raw_data.get("top_card"))
        return parser.parse_full(raw_data)

    def scrape_batch(
        self,
        usernames: list[str],
        *,
        delay: float | None = None,
    ) -> list[LinkedInProfile]:
        """
        Scrape multiple profiles.

        *delay* overrides the per-profile pause (defaults to the client's delay).
        Lines starting with ``#`` and blank lines are skipped.
        """
        clean = [u.strip() for u in usernames if u.strip() and not u.startswith("#")]
        profiles: list[LinkedInProfile] = []
        pause = delay if delay is not None else self._delay

        for i, username in enumerate(clean, 1):
            try:
                logger.info("[%d/%d] %s", i, len(clean), username)
                profiles.append(self.scrape(username))
            except Exception as exc:
                logger.error("Failed '%s': %s", username, exc)

            if i < len(clean) and pause > 0:
                time.sleep(pause * random.uniform(0.7, 1.4))

        return profiles

    @staticmethod
    def parse_local(file_path: str | Path) -> LinkedInProfile:
        """
        Parse a previously saved JSON response file.

        Accepts either a flat JSON array of entities or a response dict
        with an ``"included"`` key.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        raw = json.loads(path.read_text(encoding="utf-8"))

        if isinstance(raw, dict) and "included" in raw:
            raw = raw["included"]
        if not isinstance(raw, list):
            raise ValueError(
                "Expected a JSON array of entities or a response with 'included' key"
            )

        parser = ProfileParser()
        return parser.parse_local(raw)

    # ── Lifecycle ────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._http.close()

    def __enter__(self) -> LinkedIn:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ── Internal orchestration ───────────────────────────────────────────

    def _fetch_full_profile(self, vanity_name: str) -> dict[str, Any]:
        """Orchestrate all API calls for a single profile."""
        # Step 1 — Top card (gets member_id from the response structure)
        top_card, member_id = self._fetch_top_card(vanity_name)
        if not member_id:
            raise ProfileNotFoundError(vanity_name)

        result: dict[str, Any] = {
            "top_card": top_card,
            "member_id": member_id,
            "dash_profile": [],
            "sections": {},
        }

        # Step 2 — Dash profile with decoration fallback
        result["dash_profile"] = self._fetch_dash_profile(member_id)

        # Step 3 — Section endpoints
        profile_urn = f"urn:li:fsd_profile:{member_id}"
        for section in ep.SECTION_NAMES:
            url = ep.build_section_url(section, member_id)
            try:
                data = self._http.safe_get(url, section)
            except CookieExpiredError:
                logger.debug("  %s redirected, skipping", section)
                data = None
            entities = data.get("included", []) if data else []
            entities = _filter_entities_by_owner(entities, profile_urn)
            result["sections"][section] = entities
            if entities:
                logger.info("  %s: %d entities", section, len(entities))

        return result

    def _fetch_top_card(
        self, vanity_name: str
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Fetch the GraphQL top card and return (included_entities, member_id).

        The member_id is extracted from the response's ``*elements`` list,
        which reliably identifies the *target* profile — unlike scanning
        ``included`` which mixes the target with the viewer and mutual
        connections.
        """
        url = ep.build_top_card_url(vanity_name)
        data = self._http.get(url, f"top-card/{vanity_name}")
        included = data.get("included", [])
        if not included:
            raise ProfileNotFoundError(vanity_name)
        logger.info("  top-card: %d entities", len(included))

        # Extract target URN from the GraphQL response structure
        member_id: str | None = None
        try:
            elements = (
                data["data"]["data"]
                ["identityDashProfilesByMemberIdentity"]["*elements"]
            )
            if elements:
                # URN like "urn:li:fsd_profile:ACoAA..."
                member_id = elements[0].split("fsd_profile:")[-1]
        except (KeyError, IndexError, TypeError):
            pass

        # Fallback to scanning included entities
        if not member_id:
            member_id = extract_member_id_from_top_card(included)

        return included, member_id

    def _fetch_dash_profile(self, member_id: str) -> list[dict[str, Any]]:
        """Fetch decorated profile, trying multiple decoration versions."""
        profile_urn = f"urn:li:fsd_profile:{member_id}"
        entities: list[dict[str, Any]] = []

        for decoration in ep.DECORATION_IDS:
            url = ep.build_section_url("profile", member_id, decoration)
            try:
                data = self._http.safe_get(url, f"dash-profile/{member_id[:12]}")
            except CookieExpiredError:
                # A redirect here likely means this decoration version is
                # invalid, not that cookies expired (top card already worked).
                logger.debug("  decoration %s redirected, trying next", decoration)
                continue
            if data:
                entities = data.get("included", [])
                if entities:
                    break

        logger.info("  dash-profile: %d entities", len(entities))

        # Merge basic profile fields (email, birthday, address)
        basic_url = ep.build_basic_profile_url(member_id)
        basic = self._http.safe_get(basic_url, f"dash-profile-basic/{member_id[:12]}")
        if basic:
            basic_entities = basic.get("included", [])
            # Find the target profile entity, not the viewer's
            basic_profile = next(
                (e for e in basic_entities if e.get("entityUrn") == profile_urn),
                next(
                    (e for e in basic_entities
                     if e.get("$type", "").endswith("Profile")
                     and member_id in e.get("entityUrn", "")),
                    None,
                ),
            )
            if basic_profile:
                for e in entities:
                    if (
                        e.get("$type", "").endswith("Profile")
                        and member_id in e.get("entityUrn", "")
                    ):
                        for key in basic_profile:
                            if key not in e or e[key] is None:
                                e[key] = basic_profile[key]
                        break

        return entities
