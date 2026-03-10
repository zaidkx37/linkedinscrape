"""Tests for endpoint URL builders and stealth config."""

from __future__ import annotations

import json

from linkedinscrape._endpoints import (
    BASE_URL,
    DECORATION_IDS,
    SECTION_NAMES,
    SECTION_TEMPLATES,
    _local_timezone,
    build_basic_profile_url,
    build_cookies,
    build_headers,
    build_section_url,
    build_top_card_url,
)


class TestBuildTopCardUrl:
    def test_contains_vanity_name(self):
        url = build_top_card_url("testuser")
        assert "vanityName:testuser" in url

    def test_starts_with_graphql(self):
        url = build_top_card_url("testuser")
        assert url.startswith(BASE_URL.replace("/voyager/api", ""))

    def test_includes_query_id(self):
        url = build_top_card_url("testuser")
        assert "queryId=" in url


class TestBuildSectionUrl:
    def test_positions_url(self):
        url = build_section_url("positions", "ACoAATest123")
        assert "profilePositions" in url
        assert "ACoAATest123" in url
        assert url.startswith(BASE_URL)

    def test_skills_url(self):
        url = build_section_url("skills", "ACoAATest123")
        assert "profileSkills" in url

    def test_profile_url_with_decoration(self):
        url = build_section_url("profile", "ACoAATest123", DECORATION_IDS[0])
        assert "decorationId=" in url
        assert "FullProfileWithEntities" in url

    def test_urn_is_encoded(self):
        url = build_section_url("positions", "ACoAATest123")
        # The colon in urn:li:fsd_profile: should be percent-encoded
        assert "urn%3Ali%3Afsd_profile%3AACoAATest123" in url

    def test_all_sections_buildable(self):
        for section in SECTION_TEMPLATES:
            url = build_section_url(section, "ACoAATest123")
            assert url.startswith(BASE_URL)


class TestBuildBasicProfileUrl:
    def test_basic_url(self):
        url = build_basic_profile_url("ACoAATest123")
        assert "memberIdentity=ACoAATest123" in url
        assert "decorationId" not in url


class TestBuildHeaders:
    def test_has_csrf_token(self):
        headers = build_headers("ajax:123456")
        assert headers["csrf-token"] == "ajax:123456"

    def test_has_user_agent(self):
        headers = build_headers("ajax:123456")
        ua = headers["user-agent"]
        assert "Mozilla" in ua
        assert "Chrome" in ua

    def test_has_li_track(self):
        headers = build_headers("ajax:123456")
        track = json.loads(headers["x-li-track"])
        assert "timezoneOffset" in track
        assert "timezone" in track
        assert "displayWidth" in track
        assert "displayHeight" in track
        assert "displayDensity" in track
        assert track["deviceFormFactor"] == "DESKTOP"

    def test_timezone_is_integer(self):
        headers = build_headers("ajax:123456")
        track = json.loads(headers["x-li-track"])
        assert isinstance(track["timezoneOffset"], int)

    def test_sec_fetch_headers(self):
        headers = build_headers("ajax:123456")
        assert headers["sec-fetch-dest"] == "empty"
        assert headers["sec-fetch-mode"] == "cors"
        assert headers["sec-fetch-site"] == "same-origin"


class TestBuildCookies:
    def test_li_at(self):
        cookies = build_cookies("my_token", "ajax:123")
        assert cookies["li_at"] == "my_token"

    def test_jsessionid_quoted(self):
        cookies = build_cookies("my_token", "ajax:123")
        assert cookies["JSESSIONID"] == '"ajax:123"'

    def test_lang(self):
        cookies = build_cookies("my_token", "ajax:123")
        assert "lang" in cookies


class TestSectionNames:
    def test_profile_excluded(self):
        assert "profile" not in SECTION_NAMES

    def test_expected_sections(self):
        expected = {
            "positions", "educations", "skills", "certifications",
            "projects", "languages", "volunteers", "honors",
            "publications", "courses",
        }
        assert expected == set(SECTION_NAMES)


class TestDecorationIds:
    def test_three_versions(self):
        assert len(DECORATION_IDS) == 3

    def test_ordered_newest_first(self):
        # 93 > 91 > 35
        assert "93" in DECORATION_IDS[0]
        assert "91" in DECORATION_IDS[1]
        assert "35" in DECORATION_IDS[2]


class TestLocalTimezone:
    def test_returns_tuple(self):
        tz_name, offset = _local_timezone()
        assert isinstance(tz_name, str)
        assert isinstance(offset, int)
        assert len(tz_name) > 0

    def test_offset_reasonable(self):
        _, offset = _local_timezone()
        assert -12 <= offset <= 14
