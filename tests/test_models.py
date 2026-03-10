"""Tests for data models — loading saved JSON into model objects."""

from __future__ import annotations

import json

from linkedinscrape.models import (
    ContactInfo,
    Course,
    DateInfo,
    LinkedInProfile,
    Location,
    Organization,
    Patent,
    Position,
    Skill,
    TestScore,
)

# ── DateInfo ─────────────────────────────────────────────────────────────────


class TestDateInfo:
    def test_str_full(self):
        d = DateInfo(year=2024, month=3, day=15)
        assert str(d) == "2024-03-15"

    def test_str_year_month(self):
        d = DateInfo(year=2025, month=2)
        assert str(d) == "2025-02"

    def test_str_year_only(self):
        d = DateInfo(year=2020)
        assert str(d) == "2020"

    def test_str_empty(self):
        d = DateInfo()
        assert str(d) == ""

    def test_to_date(self):
        d = DateInfo(year=2024, month=6, day=20)
        result = d.to_date()
        assert result is not None
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 20

    def test_to_date_defaults_month_day(self):
        d = DateInfo(year=2024)
        result = d.to_date()
        assert result is not None
        assert result.month == 1
        assert result.day == 1

    def test_to_date_none_when_no_year(self):
        d = DateInfo(month=3)
        assert d.to_date() is None

    def test_to_dict(self):
        d = DateInfo(year=2024, month=3)
        assert d.to_dict() == {"year": 2024, "month": 3}

    def test_to_dict_empty(self):
        d = DateInfo()
        assert d.to_dict() == {}


# ── Location ─────────────────────────────────────────────────────────────────


class TestLocation:
    def test_display_name_geo(self):
        loc = Location(geo_location_name="Peshawar, KPK, Pakistan")
        assert loc.display_name == "Peshawar, KPK, Pakistan"

    def test_display_name_country_fallback(self):
        loc = Location(country_code="pk")
        assert loc.display_name == "PK"

    def test_display_name_empty(self):
        loc = Location()
        assert loc.display_name == ""


# ── Position ─────────────────────────────────────────────────────────────────


class TestPosition:
    def test_is_current_no_end_date(self):
        pos = Position(title="Engineer", end_date=None)
        assert pos.is_current is True

    def test_is_current_empty_end_date(self):
        pos = Position(title="Engineer", end_date=DateInfo())
        assert pos.is_current is True

    def test_not_current(self):
        pos = Position(title="Intern", end_date=DateInfo(year=2023, month=6))
        assert pos.is_current is False

    def test_to_dict(self):
        pos = Position(
            title="Python Engineer",
            company_name="Upwork",
            start_date=DateInfo(year=2025, month=2),
        )
        d = pos.to_dict()
        assert d["title"] == "Python Engineer"
        assert d["company_name"] == "Upwork"
        assert d["start_date"] == "2025-02"
        assert d["end_date"] is None
        assert d["is_current"] is True


# ── Skill ────────────────────────────────────────────────────────────────────


class TestSkill:
    def test_to_dict_no_endorsement(self):
        s = Skill(name="Python")
        d = s.to_dict()
        assert d == {"name": "Python"}
        assert "endorsement_count" not in d

    def test_to_dict_with_endorsement(self):
        s = Skill(name="Python", endorsement_count=5)
        d = s.to_dict()
        assert d == {"name": "Python", "endorsement_count": 5}


# ── Course / Patent / TestScore / Organization ───────────────────────────────


class TestNewModels:
    def test_course(self):
        c = Course(name="CS50", number="CS50x")
        d = c.to_dict()
        assert d["name"] == "CS50"
        assert d["number"] == "CS50x"

    def test_patent(self):
        p = Patent(title="Widget", patent_number="US123")
        d = p.to_dict()
        assert d["title"] == "Widget"
        assert d["patent_number"] == "US123"

    def test_test_score(self):
        t = TestScore(name="GRE", score="320")
        d = t.to_dict()
        assert d["name"] == "GRE"
        assert d["score"] == "320"

    def test_organization(self):
        o = Organization(name="ACM", position="Member")
        d = o.to_dict()
        assert d["name"] == "ACM"
        assert d["position"] == "Member"


# ── LinkedInProfile ──────────────────────────────────────────────────────────


class TestLinkedInProfile:
    def test_full_name(self):
        p = LinkedInProfile(first_name="Muhammad", last_name="Zaid")
        assert p.full_name == "Muhammad Zaid"

    def test_full_name_first_only(self):
        p = LinkedInProfile(first_name="Zaid")
        assert p.full_name == "Zaid"

    def test_current_position(self):
        p = LinkedInProfile(
            positions=[
                Position(title="Past", end_date=DateInfo(year=2020)),
                Position(title="Current", end_date=None),
            ]
        )
        assert p.current_position is not None
        assert p.current_position.title == "Current"

    def test_current_position_fallback(self):
        p = LinkedInProfile(
            positions=[Position(title="Only", end_date=DateInfo(year=2023))]
        )
        assert p.current_position is not None
        assert p.current_position.title == "Only"

    def test_current_position_empty(self):
        p = LinkedInProfile()
        assert p.current_position is None
        assert p.current_company is None
        assert p.current_title is None

    def test_to_dict_structure(self):
        p = LinkedInProfile(
            first_name="Test",
            last_name="User",
            headline="Developer",
            positions=[Position(title="Dev", company_name="Corp")],
            skills=[Skill(name="Python")],
        )
        d = p.to_dict()
        assert d["full_name"] == "Test User"
        assert d["headline"] == "Developer"
        assert len(d["positions"]) == 1
        assert d["positions"][0]["title"] == "Dev"
        assert len(d["skills"]) == 1
        assert d["skills"][0]["name"] == "Python"

    def test_to_dict_has_new_sections(self):
        p = LinkedInProfile(
            courses=[Course(name="CS50")],
            patents=[Patent(title="Widget")],
            test_scores=[TestScore(name="GRE")],
            organizations=[Organization(name="ACM")],
        )
        d = p.to_dict()
        assert len(d["courses"]) == 1
        assert len(d["patents"]) == 1
        assert len(d["test_scores"]) == 1
        assert len(d["organizations"]) == 1

    def test_to_flat_dict(self):
        p = LinkedInProfile(
            first_name="Test",
            last_name="User",
            public_identifier="testuser",
            skills=[Skill(name="A"), Skill(name="B")],
        )
        flat = p.to_flat_dict()
        assert flat["full_name"] == "Test User"
        assert flat["skills_count"] == 2
        assert "A" in flat["skills"]
        assert "B" in flat["skills"]

    def test_to_dict_json_serializable(self):
        p = LinkedInProfile(
            first_name="Test",
            last_name="User",
            location=Location(country_code="pk"),
            contact_info=ContactInfo(email_address="test@example.com"),
        )
        # Must not raise
        result = json.dumps(p.to_dict(), indent=2)
        assert '"Test User"' in result
