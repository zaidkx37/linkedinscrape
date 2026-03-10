"""Export LinkedIn profile data to JSON, CSV, and console."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from .models import LinkedInProfile

logger = logging.getLogger(__name__)


class Exporter:
    """Exports scraped LinkedIn profile data to JSON, CSV, and console."""

    def __init__(self, output_dir: str | Path = "output") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_filename(self, profile: LinkedInProfile, ext: str) -> str:
        base = profile.public_identifier or profile.member_id or "profile"
        return f"{base}.{ext}"

    def to_json(
        self, profile: LinkedInProfile, filename: str | None = None
    ) -> Path:
        """Export a single profile to a JSON file."""
        filename = filename or self._resolve_filename(profile, "json")
        path = self._output_dir / filename
        data = profile.to_dict()
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("Exported JSON: %s", path)
        return path

    def to_json_batch(
        self, profiles: list[LinkedInProfile], filename: str = "profiles.json"
    ) -> Path:
        """Export multiple profiles to a single JSON file."""
        path = self._output_dir / filename
        data = [p.to_dict() for p in profiles]
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("Exported batch JSON (%d profiles): %s", len(profiles), path)
        return path

    def to_csv(
        self, profiles: list[LinkedInProfile], filename: str = "profiles.csv"
    ) -> Path:
        """Export profiles to a CSV file (flat format)."""
        path = self._output_dir / filename
        if not profiles:
            logger.warning("No profiles to export")
            return path

        rows = [p.to_flat_dict() for p in profiles]
        fieldnames = list(rows[0].keys())

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logger.info("Exported CSV (%d profiles): %s", len(profiles), path)
        return path

    @staticmethod
    def print_summary(profile: LinkedInProfile) -> None:
        """Print a formatted profile summary to the console."""
        pic = profile.profile_picture
        loc = profile.location
        ci = profile.contact_info
        width = 62

        print(f"\n{'=' * width}")
        print(f"  {profile.full_name}")
        if profile.headline:
            print(f"  {profile.headline[:width -4]}")
        print(f"{'=' * width}")

        _row("Profile URL", profile.profile_url)
        _row("Industry", profile.industry_name)
        _row("Location", loc.display_name if loc else "N/A")
        _row("Country", (loc.country_code or "").upper() if loc else "N/A")

        print(f"\n  {'-- Network --':^{width - 4}}")
        _row("Connections", profile.connection_info.total_connections)
        _row("Followers", profile.following_state.follower_count)
        _row("Connected", "Yes" if profile.connection_info.is_connected else "No")
        _row("Following", "Yes" if profile.following_state.is_following else "No")
        _row("Open to Work", "Yes" if profile.is_open_to_work else "No")
        if profile.mutual_connections.total_count > 0:
            names = ", ".join(profile.mutual_connections.names) or "N/A"
            _row("Mutual Conn", f"{profile.mutual_connections.total_count} ({names})")

        if profile.about:
            print(f"\n  {'-- About --':^{width - 4}}")
            for line in profile.about.split("\n"):
                print(f"  {line.strip()[:width -4]}")

        if ci.email_address or ci.websites or ci.twitter_handles:
            print(f"\n  {'-- Contact --':^{width - 4}}")
            if ci.email_address:
                _row("Email", ci.email_address)
            for ph in ci.phone_numbers:
                num = ph.get("number", ph) if isinstance(ph, dict) else ph
                _row("Phone", num)
            for w in ci.websites:
                url = w.get("url", w) if isinstance(w, dict) else w
                _row("Website", url)
            for t in ci.twitter_handles:
                _row("Twitter", f"@{t}")

        if profile.positions:
            print(f"\n  {'-- Experience --':^{width - 4}}")
            for p in profile.positions:
                status = "Present" if p.is_current else str(p.end_date or "?")
                start = str(p.start_date) if p.start_date else "?"
                print(f"  {p.title or '(no title)'}")
                print(f"    {p.company_name}  ({start} - {status})")
                if p.location_name:
                    print(f"    {p.location_name}")
                if p.employment_type:
                    print(f"    Type: {p.employment_type}")
                if p.description:
                    desc = p.description.replace("\n", " ")[:120]
                    print(f"    {desc}{'...' if len(p.description) > 120 else ''}")

        if profile.educations:
            print(f"\n  {'-- Education --':^{width - 4}}")
            for e in profile.educations:
                print(f"  {e.school_name}")
                parts = [x for x in [e.degree_name, e.field_of_study] if x]
                if parts:
                    print(f"    {' - '.join(parts)}")
                dates = []
                if e.start_date:
                    dates.append(str(e.start_date))
                if e.end_date:
                    dates.append(str(e.end_date))
                if dates:
                    print(f"    {' to '.join(dates)}")
                if e.grade:
                    print(f"    Grade: {e.grade}")

        if profile.skills:
            print(f"\n  {'-- Skills --':^{width - 4}}")
            skill_names = [s.name for s in profile.skills]
            line = "  "
            for name in skill_names:
                if len(line) + len(name) + 4 > width:
                    print(line)
                    line = "  "
                line += f"{name}, "
            if line.strip():
                print(line.rstrip(", "))

        if profile.certifications:
            print(f"\n  {'-- Licenses & Certifications --':^{width - 4}}")
            for c in profile.certifications:
                print(f"  {c.name}")
                if c.authority:
                    print(f"    Issued by: {c.authority}")

        if profile.projects:
            print(f"\n  {'-- Projects --':^{width - 4}}")
            for proj in profile.projects:
                print(f"  {proj.title}")
                if proj.description:
                    desc = proj.description.replace("\n", " ")[:100]
                    print(f"    {desc}{'...' if len(proj.description) > 100 else ''}")

        if profile.languages:
            print(f"\n  {'-- Languages --':^{width - 4}}")
            for lang in profile.languages:
                prof = f" ({lang.proficiency})" if lang.proficiency else ""
                print(f"  {lang.name}{prof}")

        if profile.courses:
            print(f"\n  {'-- Courses --':^{width - 4}}")
            for course in profile.courses:
                num = f" ({course.number})" if course.number else ""
                print(f"  {course.name}{num}")

        if profile.volunteer_experiences:
            print(f"\n  {'-- Volunteer Experience --':^{width - 4}}")
            for v in profile.volunteer_experiences:
                print(f"  {v.role} at {v.organization_name}")

        if profile.honors_awards:
            print(f"\n  {'-- Honors & Awards --':^{width - 4}}")
            for h in profile.honors_awards:
                print(f"  {h.title}")
                if h.issuer:
                    print(f"    From: {h.issuer}")

        if profile.publications:
            print(f"\n  {'-- Publications --':^{width - 4}}")
            for pub in profile.publications:
                print(f"  {pub.name}")
                if pub.publisher:
                    print(f"    Publisher: {pub.publisher}")

        if pic and pic.best_url:
            print(f"\n  Photo: {pic.best_url[:width -10]}...")

        print(f"{'=' * width}\n")


def _row(label: str, value: object) -> None:
    if value:
        print(f"  {label:<16}: {value}")
