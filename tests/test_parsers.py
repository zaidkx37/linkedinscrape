"""Tests for the parser module — using synthetic Voyager API-like entities."""

from __future__ import annotations

from linkedinscrape._parsers import (
    ProfileParser,
    _extract_names_from_insight,
    _parse_date,
    extract_member_id_from_top_card,
)
from linkedinscrape.models import DateInfo

# ── _parse_date ──────────────────────────────────────────────────────────────


class TestParseDate:
    def test_full_date(self):
        d = _parse_date({"year": 2024, "month": 6, "day": 15})
        assert isinstance(d, DateInfo)
        assert d.year == 2024
        assert d.month == 6
        assert d.day == 15

    def test_year_month(self):
        d = _parse_date({"year": 2024, "month": 3})
        assert d.year == 2024
        assert d.month == 3
        assert d.day is None

    def test_year_only(self):
        d = _parse_date({"year": 2020})
        assert d.year == 2020

    def test_none_input(self):
        assert _parse_date(None) is None

    def test_empty_dict(self):
        assert _parse_date({}) is None

    def test_no_year_no_month(self):
        assert _parse_date({"day": 5}) is None

    def test_not_a_dict(self):
        assert _parse_date("2024") is None


# ── extract_member_id_from_top_card ──────────────────────────────────────────


class TestExtractMemberId:
    def test_extracts_from_profile_entity(self):
        top_card = [
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
                "entityUrn": "urn:li:fsd_profile:ACoAAEXCrYoB123",
                "headline": "Developer",
            }
        ]
        assert extract_member_id_from_top_card(top_card) == "ACoAAEXCrYoB123"

    def test_fallback_profile_urn(self):
        top_card = [
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
                "entityUrn": "urn:li:fsd_profile:ACoAAFallback",
            }
        ]
        assert extract_member_id_from_top_card(top_card) == "ACoAAFallback"

    def test_none_when_empty(self):
        assert extract_member_id_from_top_card([]) is None

    def test_none_when_no_profile(self):
        top_card = [
            {
                "$type": "com.linkedin.voyager.dash.identity.Something",
                "entityUrn": "urn:li:other:123",
            }
        ]
        assert extract_member_id_from_top_card(top_card) is None


# ── _extract_names_from_insight ──────────────────────────────────────────────


class TestExtractNamesFromInsight:
    def test_names_with_others(self):
        text = "Ali Khan, Sara Ahmed, and 5 other mutual connections"
        names = _extract_names_from_insight(text)
        assert names == ["Ali Khan", "Sara Ahmed"]

    def test_single_name(self):
        text = "Ali Khan, and 3 other mutual connections"
        names = _extract_names_from_insight(text)
        assert names == ["Ali Khan"]

    def test_no_match(self):
        names = _extract_names_from_insight("Something else entirely")
        assert names == []


# ── ProfileParser with synthetic entities ────────────────────────────────────


class TestProfileParserSynthetic:
    """Test the parser with hand-crafted Voyager API entities."""

    def _make_entities(self) -> list[dict]:
        return [
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
                "entityUrn": "urn:li:fsd_profile:ACoAATest123",
                "publicIdentifier": "testuser",
                "firstName": "Test",
                "lastName": "User",
                "headline": "Software Engineer",
                "location": {"countryCode": "us"},
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Position",
                "entityUrn": "urn:li:fsd_profilePosition:pos1",
                "title": "Senior Developer",
                "companyName": "Acme Corp",
                "description": "Building things",
                "locationName": "Remote",
                "employmentType": "FULL_TIME",
                "dateRange": {
                    "start": {"year": 2022, "month": 1},
                },
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Position",
                "entityUrn": "urn:li:fsd_profilePosition:pos2",
                "title": "Junior Developer",
                "companyName": "Startup Inc",
                "dateRange": {
                    "start": {"year": 2020, "month": 6},
                    "end": {"year": 2021, "month": 12},
                },
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Education",
                "entityUrn": "urn:li:fsd_profileEducation:edu1",
                "schoolName": "MIT",
                "degreeName": "BS",
                "fieldOfStudy": "Computer Science",
                "grade": "4.0",
                "dateRange": {
                    "start": {"year": 2016},
                    "end": {"year": 2020},
                },
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Skill",
                "entityUrn": "urn:li:fsd_skill:s1",
                "name": "Python",
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Skill",
                "entityUrn": "urn:li:fsd_skill:s2",
                "name": "Go",
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Skill",
                "entityUrn": "urn:li:fsd_skill:s1",
                "name": "Python",  # duplicate — should be deduped
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Certification",
                "entityUrn": "urn:li:fsd_cert:c1",
                "name": "AWS Cert",
                "authority": "Amazon",
                "licenseNumber": "123",
                "url": "https://aws.amazon.com/cert/123",
                "dateRange": {"start": {"year": 2023}},
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Language",
                "name": "English",
                "proficiency": "NATIVE",
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Language",
                "name": "Urdu",
                "proficiency": "FULL_PROFESSIONAL",
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Course",
                "entityUrn": "urn:li:fsd_course:cr1",
                "name": "Algorithms",
                "number": "CS201",
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Project",
                "entityUrn": "urn:li:fsd_project:p1",
                "title": "My Project",
                "description": "A cool project",
                "url": "https://github.com/test/project",
                "dateRange": {
                    "start": {"year": 2023, "month": 1},
                    "end": {"year": 2023, "month": 6},
                },
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.VolunteerExperience",
                "entityUrn": "urn:li:fsd_vol:v1",
                "role": "Mentor",
                "companyName": "Code.org",
                "cause": "Education",
                "dateRange": {"start": {"year": 2021}},
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Honor",
                "entityUrn": "urn:li:fsd_honor:h1",
                "title": "Best Paper Award",
                "issuer": "IEEE",
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Publication",
                "entityUrn": "urn:li:fsd_pub:pub1",
                "name": "Research Paper",
                "publisher": "ACM",
                "url": "https://acm.org/paper/1",
            },
        ]

    def test_parse_local_identity(self):
        parser = ProfileParser()
        profile = parser.parse_local(self._make_entities())

        assert profile.first_name == "Test"
        assert profile.last_name == "User"
        assert profile.public_identifier == "testuser"
        assert profile.headline == "Software Engineer"
        assert profile.member_id == "ACoAATest123"

    def test_parse_local_profile_url(self):
        parser = ProfileParser()
        profile = parser.parse_local(self._make_entities())
        assert profile.profile_url == "https://www.linkedin.com/in/testuser"

    def test_parse_local_location(self):
        parser = ProfileParser()
        profile = parser.parse_local(self._make_entities())
        assert profile.location is not None
        assert profile.location.country_code == "us"

    def test_parse_local_positions(self):
        parser = ProfileParser()
        profile = parser.parse_local(self._make_entities())

        assert len(profile.positions) == 2
        senior = next(p for p in profile.positions if p.title == "Senior Developer")
        assert senior.company_name == "Acme Corp"
        assert senior.is_current is True
        assert senior.start_date is not None
        assert senior.start_date.year == 2022

        junior = next(p for p in profile.positions if p.title == "Junior Developer")
        assert junior.is_current is False
        assert junior.end_date is not None
        assert junior.end_date.year == 2021

    def test_parse_local_educations(self):
        parser = ProfileParser()
        profile = parser.parse_local(self._make_entities())

        assert len(profile.educations) == 1
        edu = profile.educations[0]
        assert edu.school_name == "MIT"
        assert edu.degree_name == "BS"
        assert edu.field_of_study == "Computer Science"
        assert edu.grade == "4.0"

    def test_parse_local_skills_deduped(self):
        parser = ProfileParser()
        profile = parser.parse_local(self._make_entities())

        names = [s.name for s in profile.skills]
        assert names == ["Python", "Go"]  # duplicate Python removed

    def test_parse_local_certifications(self):
        parser = ProfileParser()
        profile = parser.parse_local(self._make_entities())

        assert len(profile.certifications) == 1
        cert = profile.certifications[0]
        assert cert.name == "AWS Cert"
        assert cert.authority == "Amazon"
        assert cert.license_number == "123"

    def test_parse_local_languages(self):
        parser = ProfileParser()
        profile = parser.parse_local(self._make_entities())

        assert len(profile.languages) == 2
        eng = next(ln for ln in profile.languages if ln.name == "English")
        assert eng.proficiency == "NATIVE"

    def test_parse_local_courses(self):
        parser = ProfileParser()
        profile = parser.parse_local(self._make_entities())

        assert len(profile.courses) == 1
        assert profile.courses[0].name == "Algorithms"
        assert profile.courses[0].number == "CS201"

    def test_parse_local_projects(self):
        parser = ProfileParser()
        profile = parser.parse_local(self._make_entities())

        assert len(profile.projects) == 1
        proj = profile.projects[0]
        assert proj.title == "My Project"
        assert proj.url == "https://github.com/test/project"

    def test_parse_local_volunteers(self):
        parser = ProfileParser()
        profile = parser.parse_local(self._make_entities())

        assert len(profile.volunteer_experiences) == 1
        vol = profile.volunteer_experiences[0]
        assert vol.role == "Mentor"
        assert vol.organization_name == "Code.org"

    def test_parse_local_honors(self):
        parser = ProfileParser()
        profile = parser.parse_local(self._make_entities())

        assert len(profile.honors_awards) == 1
        assert profile.honors_awards[0].title == "Best Paper Award"
        assert profile.honors_awards[0].issuer == "IEEE"

    def test_parse_local_publications(self):
        parser = ProfileParser()
        profile = parser.parse_local(self._make_entities())

        assert len(profile.publications) == 1
        assert profile.publications[0].name == "Research Paper"
        assert profile.publications[0].publisher == "ACM"

    def test_to_dict_roundtrip(self):
        """Parser → model → to_dict should produce valid JSON."""
        import json

        parser = ProfileParser()
        profile = parser.parse_local(self._make_entities())
        data = profile.to_dict()
        result = json.dumps(data, indent=2)
        assert '"Test User"' in result
        assert '"Senior Developer"' in result
        assert '"Python"' in result
        assert '"Algorithms"' in result
