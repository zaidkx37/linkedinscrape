"""LinkedIn Voyager API endpoint configuration and URL builders."""

from __future__ import annotations

import json
import time
from urllib.parse import quote

BASE_URL = "https://www.linkedin.com/voyager/api"
GRAPHQL_URL = f"{BASE_URL}/graphql"

TOP_CARD_QUERY_ID = "voyagerIdentityDashProfiles.a1a483e719b20537a256b6853cdca711"

# Tried in order; fall back on failure.
DECORATION_IDS = (
    "com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-93",
    "com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-91",
    "com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-35",
)

SECTION_TEMPLATES: dict[str, str] = {
    "profile": (
        "/identity/dash/profiles"
        "?q=memberIdentity&memberIdentity={member_id}&decorationId={decoration}"
    ),
    "positions": "/identity/dash/profilePositions?q=viewee&profileUrn={urn}&count=50",
    "educations": "/identity/dash/profileEducations?q=viewee&profileUrn={urn}&count=50",
    "skills": "/identity/dash/profileSkills?q=viewee&profileUrn={urn}&count=50",
    "certifications": "/identity/dash/profileCertifications?q=viewee&profileUrn={urn}&count=50",
    "projects": "/identity/dash/profileProjects?q=viewee&profileUrn={urn}&count=50",
    "languages": "/identity/dash/profileLanguages?q=viewee&profileUrn={urn}&count=50",
    "volunteers": "/identity/dash/profileVolunteerExperiences?q=viewee&profileUrn={urn}&count=50",
    "honors": "/identity/dash/profileHonors?q=viewee&profileUrn={urn}&count=50",
    "publications": "/identity/dash/profilePublications?q=viewee&profileUrn={urn}&count=50",
    "courses": "/identity/dash/profileCourses?q=viewee&profileUrn={urn}&count=50",
}

SECTION_NAMES = [s for s in SECTION_TEMPLATES if s != "profile"]

# Static device fingerprint — matches the most common LinkedIn traffic pattern:
# Windows 10 + Chrome + 1080p @ 1.25x scaling.  Stays consistent across all
# requests for the entire cookie lifetime, just like a real browser.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)
_DISPLAY = {"displayDensity": 1.25, "displayWidth": 1920, "displayHeight": 1080}


def _local_timezone() -> tuple[str, int]:
    """Return (IANA timezone name, UTC offset in hours) for the local machine."""
    try:
        from datetime import datetime, timezone

        local_offset_s = datetime.now(timezone.utc).astimezone().utcoffset()
        offset_h = int(local_offset_s.total_seconds() // 3600) if local_offset_s else 0  # type: ignore[union-attr]

        # Try to get the IANA name
        try:

            local_tz = datetime.now().astimezone().tzinfo
            tz_name = str(local_tz) if local_tz else "UTC"
            # Python may return an abbreviation like 'PKT'; try to map back
            if "/" not in tz_name:
                tz_name = time.tzname[0] if time.tzname[0] else "UTC"
                # Still not IANA? Fall back to Etc/GMT style
                if "/" not in tz_name:
                    sign = "-" if offset_h >= 0 else "+"  # Etc/GMT signs are inverted
                    tz_name = f"Etc/GMT{sign}{abs(offset_h)}" if offset_h else "Etc/GMT"
        except Exception:
            sign = "-" if offset_h >= 0 else "+"
            tz_name = f"Etc/GMT{sign}{abs(offset_h)}" if offset_h else "Etc/GMT"

        return tz_name, offset_h
    except Exception:
        return "UTC", 0


def build_headers(csrf_token: str) -> dict[str, str]:
    """Build request headers that mimic a real browser session.

    Uses a static device fingerprint (UA + display) that stays consistent
    across all requests for the entire cookie lifetime.
    """
    tz_name, tz_offset = _local_timezone()

    li_track = {
        "clientVersion": "1.13.40976",
        "mpVersion": "1.13.40976",
        "osName": "web",
        "timezoneOffset": tz_offset,
        "timezone": tz_name,
        "deviceFormFactor": "DESKTOP",
        "mpName": "voyager-web",
        **_DISPLAY,
    }

    return {
        "accept": "application/vnd.linkedin.normalized+json+2.1",
        "accept-language": "en-US,en;q=0.9",
        "csrf-token": csrf_token,
        "x-li-lang": "en_US",
        "x-restli-protocol-version": "2.0.0",
        "x-li-track": json.dumps(li_track),
        "user-agent": _USER_AGENT,
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }


def build_cookies(li_at: str, csrf_token: str) -> dict[str, str]:
    return {
        "li_at": li_at,
        "JSESSIONID": f'"{csrf_token}"',
        "lang": "v=2&lang=en-us",
    }


def build_top_card_url(vanity_name: str) -> str:
    return (
        f"{GRAPHQL_URL}"
        f"?includeWebMetadata=true"
        f"&variables=(vanityName:{vanity_name})"
        f"&queryId={TOP_CARD_QUERY_ID}"
    )


def build_section_url(
    section: str,
    member_id: str,
    decoration: str = DECORATION_IDS[0],
) -> str:
    urn_encoded = quote(f"urn:li:fsd_profile:{member_id}", safe="")
    template = SECTION_TEMPLATES[section]
    return BASE_URL + template.format(
        member_id=member_id,
        urn=urn_encoded,
        decoration=decoration,
    )


def build_basic_profile_url(member_id: str) -> str:
    return f"{BASE_URL}/identity/dash/profiles?q=memberIdentity&memberIdentity={member_id}"
