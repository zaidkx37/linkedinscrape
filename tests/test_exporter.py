"""Tests for the Exporter — JSON, CSV, and console output."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from linkedinscrape.exporter import Exporter
from linkedinscrape.models import (
    Certification,
    ContactInfo,
    DateInfo,
    Education,
    LinkedInProfile,
    Location,
    Position,
    Skill,
)


def _make_profile(**overrides) -> LinkedInProfile:
    defaults = dict(
        first_name="Test",
        last_name="User",
        public_identifier="testuser",
        entity_urn="urn:li:fsd_profile:ABC123",
        member_id="ABC123",
        headline="Software Engineer",
        about="I write code.",
        industry_name="Technology",
        profile_url="https://www.linkedin.com/in/testuser",
        location=Location(country_code="us", geo_location_name="San Francisco, CA"),
        contact_info=ContactInfo(email_address="test@example.com"),
        positions=[
            Position(
                title="Engineer",
                company_name="Acme",
                start_date=DateInfo(year=2023, month=1),
            ),
        ],
        educations=[
            Education(school_name="MIT", degree_name="BS", field_of_study="CS"),
        ],
        skills=[Skill(name="Python"), Skill(name="Go")],
    )
    defaults.update(overrides)
    return LinkedInProfile(**defaults)


class TestExporterJson:
    def test_creates_json_file(self, output_dir):
        exporter = Exporter(output_dir)
        profile = _make_profile()
        path = exporter.to_json(profile)

        assert path.exists()
        assert path.suffix == ".json"
        assert path.name == "testuser.json"

    def test_json_content(self, output_dir):
        exporter = Exporter(output_dir)
        profile = _make_profile()
        path = exporter.to_json(profile)

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["first_name"] == "Test"
        assert data["last_name"] == "User"
        assert data["full_name"] == "Test User"
        assert data["headline"] == "Software Engineer"
        assert len(data["positions"]) == 1
        assert len(data["skills"]) == 2

    def test_custom_filename(self, output_dir):
        exporter = Exporter(output_dir)
        profile = _make_profile()
        path = exporter.to_json(profile, filename="custom.json")

        assert path.name == "custom.json"
        assert path.exists()

    def test_filename_from_member_id(self, output_dir):
        exporter = Exporter(output_dir)
        profile = _make_profile(public_identifier="")
        path = exporter.to_json(profile)

        assert path.name == "ABC123.json"

    def test_filename_fallback(self, output_dir):
        exporter = Exporter(output_dir)
        profile = _make_profile(public_identifier="", member_id="")
        path = exporter.to_json(profile)

        assert path.name == "profile.json"

    def test_unicode_content(self, output_dir):
        exporter = Exporter(output_dir)
        profile = _make_profile(first_name="محمد", last_name="زید")
        path = exporter.to_json(profile)

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["first_name"] == "محمد"
        assert data["full_name"] == "محمد زید"


class TestExporterJsonBatch:
    def test_batch_json(self, output_dir):
        exporter = Exporter(output_dir)
        profiles = [
            _make_profile(first_name="Alice", public_identifier="alice"),
            _make_profile(first_name="Bob", public_identifier="bob"),
        ]
        path = exporter.to_json_batch(profiles)

        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["first_name"] == "Alice"
        assert data[1]["first_name"] == "Bob"


class TestExporterCsv:
    def test_creates_csv(self, output_dir):
        exporter = Exporter(output_dir)
        profiles = [_make_profile()]
        path = exporter.to_csv(profiles)

        assert path.exists()
        assert path.suffix == ".csv"

    def test_csv_content(self, output_dir):
        exporter = Exporter(output_dir)
        profiles = [
            _make_profile(first_name="Alice", public_identifier="alice"),
            _make_profile(first_name="Bob", public_identifier="bob"),
        ]
        path = exporter.to_csv(profiles)

        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["first_name"] == "Alice"
        assert rows[1]["first_name"] == "Bob"
        assert rows[0]["skills_count"] == "2"

    def test_csv_empty_profiles(self, output_dir):
        exporter = Exporter(output_dir)
        path = exporter.to_csv([])
        # Should not crash, returns path even if empty
        assert isinstance(path, Path)

    def test_csv_has_all_columns(self, output_dir):
        exporter = Exporter(output_dir)
        profiles = [_make_profile()]
        path = exporter.to_csv(profiles)

        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        expected_cols = {
            "entity_urn", "member_id", "public_identifier",
            "first_name", "last_name", "full_name",
            "headline", "about", "industry", "profile_url",
            "email", "current_title", "current_company",
            "total_connections", "follower_count",
            "skills_count", "skills",
        }
        assert expected_cols.issubset(set(rows[0].keys()))


class TestExporterSummary:
    def test_print_summary_no_crash(self, capsys):
        """print_summary should run without errors for a full profile."""
        profile = _make_profile()
        Exporter.print_summary(profile)

        captured = capsys.readouterr()
        assert "Test User" in captured.out
        assert "Software Engineer" in captured.out
        assert "Python" in captured.out

    def test_print_summary_sparse_profile(self, capsys):
        """Should handle a profile with minimal data."""
        profile = LinkedInProfile(first_name="Sparse", last_name="User")
        Exporter.print_summary(profile)

        captured = capsys.readouterr()
        assert "Sparse User" in captured.out

    def test_print_summary_with_certifications(self, capsys):
        profile = _make_profile(
            certifications=[
                Certification(name="AWS Solutions Architect", authority="Amazon"),
            ],
        )
        Exporter.print_summary(profile)

        captured = capsys.readouterr()
        assert "AWS Solutions Architect" in captured.out
        assert "Amazon" in captured.out


class TestExporterOutputDir:
    def test_creates_output_dir(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        Exporter(nested)
        assert nested.exists()

    def test_existing_dir_ok(self, tmp_path):
        exporter = Exporter(tmp_path)
        profile = _make_profile()
        path = exporter.to_json(profile)
        assert path.exists()
