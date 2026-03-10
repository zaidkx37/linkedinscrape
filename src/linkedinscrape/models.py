"""Data models for LinkedIn profile data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

# ── Primitives ───────────────────────────────────────────────────────────────


@dataclass(slots=True)
class DateInfo:
    year: int | None = None
    month: int | None = None
    day: int | None = None

    def to_date(self) -> date | None:
        if not self.year:
            return None
        return date(self.year, self.month or 1, self.day or 1)

    def __str__(self) -> str:
        parts: list[str] = []
        if self.year:
            parts.append(str(self.year))
        if self.month:
            parts.append(f"{self.month:02d}")
        if self.day:
            parts.append(f"{self.day:02d}")
        return "-".join(parts) if parts else ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.year is not None:
            d["year"] = self.year
        if self.month is not None:
            d["month"] = self.month
        if self.day is not None:
            d["day"] = self.day
        return d


@dataclass(slots=True)
class ImageArtifact:
    url: str
    width: int
    height: int
    expires_at: datetime | None = None


@dataclass(slots=True)
class ProfilePicture:
    display_image_urn: str = ""
    artifacts: list[ImageArtifact] = field(default_factory=list)
    a11y_text: str = ""
    frame_type: str | None = None

    @property
    def best_url(self) -> str | None:
        if not self.artifacts:
            return None
        return max(self.artifacts, key=lambda a: a.width).url


@dataclass(slots=True)
class Location:
    country_code: str | None = None
    postal_code: str | None = None
    geo_place: str | None = None
    geo_location_name: str | None = None

    @property
    def display_name(self) -> str:
        if self.geo_location_name:
            return self.geo_location_name
        if self.country_code:
            return self.country_code.upper()
        return ""


@dataclass(slots=True)
class ContactInfo:
    email_address: str | None = None
    phone_numbers: list[dict[str, str]] = field(default_factory=list)
    websites: list[dict[str, str]] = field(default_factory=list)
    twitter_handles: list[str] = field(default_factory=list)
    ims: list[dict[str, str]] = field(default_factory=list)
    birth_date: DateInfo | None = None
    connected_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "email": self.email_address,
            "phone_numbers": self.phone_numbers or None,
            "websites": self.websites or None,
            "twitter_handles": self.twitter_handles or None,
            "birth_date": str(self.birth_date) if self.birth_date else None,
        }


# ── Network ──────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class FollowingState:
    follower_count: int = 0
    is_following: bool = False


@dataclass(slots=True)
class MutualConnection:
    total_count: int = 0
    names: list[str] = field(default_factory=list)
    browse_url: str | None = None


@dataclass(slots=True)
class ConnectionInfo:
    is_connected: bool = False
    connected_at: datetime | None = None
    total_connections: int = 0


# ── Organizations ────────────────────────────────────────────────────────────


@dataclass(slots=True)
class Company:
    entity_urn: str = ""
    name: str = ""
    universal_name: str = ""
    url: str = ""
    logo_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url or None,
            "logo_url": self.logo_url,
        }


@dataclass(slots=True)
class School:
    entity_urn: str = ""
    name: str = ""
    url: str = ""
    logo_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url or None,
            "logo_url": self.logo_url,
        }


# ── Experience / Positions ───────────────────────────────────────────────────


@dataclass(slots=True)
class Position:
    entity_urn: str = ""
    title: str = ""
    company_name: str = ""
    description: str = ""
    location_name: str = ""
    employment_type: str = ""
    start_date: DateInfo | None = None
    end_date: DateInfo | None = None
    company: Company | None = None

    @property
    def is_current(self) -> bool:
        return self.end_date is None or str(self.end_date) == ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "company_name": self.company_name,
            "description": self.description or None,
            "location": self.location_name or None,
            "employment_type": self.employment_type or None,
            "start_date": str(self.start_date) if self.start_date else None,
            "end_date": str(self.end_date) if self.end_date else None,
            "is_current": self.is_current,
            "company_url": self.company.url if self.company else None,
            "company_logo": self.company.logo_url if self.company else None,
        }


# ── Education ────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class Education:
    entity_urn: str = ""
    school_name: str = ""
    degree_name: str = ""
    field_of_study: str = ""
    grade: str = ""
    activities: str = ""
    description: str = ""
    start_date: DateInfo | None = None
    end_date: DateInfo | None = None
    school: School | None = None
    company: Company | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "school_name": self.school_name,
            "degree_name": self.degree_name or None,
            "field_of_study": self.field_of_study or None,
            "grade": self.grade or None,
            "activities": self.activities or None,
            "description": self.description or None,
            "start_date": str(self.start_date) if self.start_date else None,
            "end_date": str(self.end_date) if self.end_date else None,
            "school_url": self.school.url if self.school else None,
            "school_logo": self.school.logo_url if self.school else None,
        }


# ── Skills ───────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class Skill:
    name: str = ""
    entity_urn: str = ""
    endorsement_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"name": self.name}
        if self.endorsement_count:
            d["endorsement_count"] = self.endorsement_count
        return d


# ── Certifications ───────────────────────────────────────────────────────────


@dataclass(slots=True)
class Certification:
    name: str = ""
    authority: str = ""
    license_number: str = ""
    url: str = ""
    start_date: DateInfo | None = None
    end_date: DateInfo | None = None
    company: Company | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "authority": self.authority or None,
            "license_number": self.license_number or None,
            "url": self.url or None,
            "start_date": str(self.start_date) if self.start_date else None,
            "end_date": str(self.end_date) if self.end_date else None,
        }


# ── Projects ─────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class Project:
    title: str = ""
    description: str = ""
    url: str = ""
    start_date: DateInfo | None = None
    end_date: DateInfo | None = None
    members: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description or None,
            "url": self.url or None,
            "start_date": str(self.start_date) if self.start_date else None,
            "end_date": str(self.end_date) if self.end_date else None,
            "members": self.members or None,
        }


# ── Languages ────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class Language:
    name: str = ""
    proficiency: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"name": self.name}
        if self.proficiency:
            d["proficiency"] = self.proficiency
        return d


# ── Volunteer Experience ─────────────────────────────────────────────────────


@dataclass(slots=True)
class VolunteerExperience:
    role: str = ""
    organization_name: str = ""
    cause: str = ""
    description: str = ""
    start_date: DateInfo | None = None
    end_date: DateInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "organization_name": self.organization_name,
            "cause": self.cause or None,
            "description": self.description or None,
            "start_date": str(self.start_date) if self.start_date else None,
            "end_date": str(self.end_date) if self.end_date else None,
        }


# ── Honors & Awards ─────────────────────────────────────────────────────────


@dataclass(slots=True)
class HonorAward:
    title: str = ""
    issuer: str = ""
    description: str = ""
    issue_date: DateInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "issuer": self.issuer or None,
            "description": self.description or None,
            "issue_date": str(self.issue_date) if self.issue_date else None,
        }


# ── Publications ─────────────────────────────────────────────────────────────


@dataclass(slots=True)
class Publication:
    name: str = ""
    publisher: str = ""
    description: str = ""
    url: str = ""
    date: DateInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "publisher": self.publisher or None,
            "description": self.description or None,
            "url": self.url or None,
            "date": str(self.date) if self.date else None,
        }


# ── Courses ──────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class Course:
    name: str = ""
    number: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"name": self.name}
        if self.number:
            d["number"] = self.number
        return d


# ── Patents ──────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class Patent:
    title: str = ""
    issuer: str = ""
    description: str = ""
    url: str = ""
    patent_number: str = ""
    status: str = ""
    filing_date: DateInfo | None = None
    issue_date: DateInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "issuer": self.issuer or None,
            "description": self.description or None,
            "url": self.url or None,
            "patent_number": self.patent_number or None,
            "status": self.status or None,
            "filing_date": str(self.filing_date) if self.filing_date else None,
            "issue_date": str(self.issue_date) if self.issue_date else None,
        }


# ── Test Scores ──────────────────────────────────────────────────────────────


@dataclass(slots=True)
class TestScore:
    name: str = ""
    score: str = ""
    description: str = ""
    date: DateInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score or None,
            "description": self.description or None,
            "date": str(self.date) if self.date else None,
        }


# ── Organizations ────────────────────────────────────────────────────────────


@dataclass(slots=True)
class Organization:
    name: str = ""
    position: str = ""
    description: str = ""
    start_date: DateInfo | None = None
    end_date: DateInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "position": self.position or None,
            "description": self.description or None,
            "start_date": str(self.start_date) if self.start_date else None,
            "end_date": str(self.end_date) if self.end_date else None,
        }


# ── Full Profile ─────────────────────────────────────────────────────────────


@dataclass(slots=True)
class LinkedInProfile:
    # Identity
    entity_urn: str = ""
    member_id: str = ""
    public_identifier: str = ""
    first_name: str = ""
    last_name: str = ""
    headline: str = ""
    about: str = ""
    industry_name: str = ""

    # URLs
    profile_url: str = ""
    profile_pdf_url: str = ""

    # Media
    profile_picture: ProfilePicture | None = None
    background_picture: ProfilePicture | None = None

    # Location
    location: Location | None = None

    # Contact
    contact_info: ContactInfo = field(default_factory=ContactInfo)

    # Network
    connection_info: ConnectionInfo = field(default_factory=ConnectionInfo)
    following_state: FollowingState = field(default_factory=FollowingState)
    mutual_connections: MutualConnection = field(default_factory=MutualConnection)

    # Professional sections
    positions: list[Position] = field(default_factory=list)
    educations: list[Education] = field(default_factory=list)
    skills: list[Skill] = field(default_factory=list)
    certifications: list[Certification] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    languages: list[Language] = field(default_factory=list)
    volunteer_experiences: list[VolunteerExperience] = field(default_factory=list)
    honors_awards: list[HonorAward] = field(default_factory=list)
    publications: list[Publication] = field(default_factory=list)
    courses: list[Course] = field(default_factory=list)
    patents: list[Patent] = field(default_factory=list)
    test_scores: list[TestScore] = field(default_factory=list)
    organizations: list[Organization] = field(default_factory=list)

    # Status flags
    is_memorialized: bool = False
    is_open_to_work: bool = False
    creator_badge_status: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def current_position(self) -> Position | None:
        for pos in self.positions:
            if pos.is_current:
                return pos
        return self.positions[0] if self.positions else None

    @property
    def current_company(self) -> str | None:
        pos = self.current_position
        return pos.company_name if pos else None

    @property
    def current_title(self) -> str | None:
        pos = self.current_position
        return pos.title if pos else None

    def to_dict(self) -> dict[str, Any]:
        """Full nested dictionary for JSON export."""
        pic = self.profile_picture
        loc = self.location
        ci = self.contact_info

        d: dict[str, Any] = {
            "entity_urn": self.entity_urn,
            "member_id": self.member_id,
            "public_identifier": self.public_identifier,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "headline": self.headline,
            "about": self.about or None,
            "industry": self.industry_name or None,
            "profile_url": self.profile_url,
            "profile_pdf_url": self.profile_pdf_url or None,
            "profile_picture_url": pic.best_url if pic else None,
            "is_open_to_work": self.is_open_to_work,
            "frame_type": pic.frame_type if pic else None,
            "location": {
                "country_code": loc.country_code if loc else None,
                "geo_location_name": loc.geo_location_name if loc else None,
                "display": loc.display_name if loc else "",
            },
            "contact_info": ci.to_dict(),
            "network": {
                "total_connections": self.connection_info.total_connections,
                "is_connected": self.connection_info.is_connected,
                "connected_at": (
                    self.connection_info.connected_at.isoformat()
                    if self.connection_info.connected_at
                    else None
                ),
                "follower_count": self.following_state.follower_count,
                "is_following": self.following_state.is_following,
                "mutual_connections": {
                    "count": self.mutual_connections.total_count,
                    "names": self.mutual_connections.names or None,
                    "browse_url": self.mutual_connections.browse_url,
                },
            },
            "positions": [p.to_dict() for p in self.positions],
            "educations": [e.to_dict() for e in self.educations],
            "skills": [s.to_dict() for s in self.skills],
            "certifications": [c.to_dict() for c in self.certifications],
            "projects": [p.to_dict() for p in self.projects],
            "languages": [ln.to_dict() for ln in self.languages],
            "volunteer_experiences": [v.to_dict() for v in self.volunteer_experiences],
            "honors_awards": [h.to_dict() for h in self.honors_awards],
            "publications": [p.to_dict() for p in self.publications],
            "courses": [c.to_dict() for c in self.courses],
            "patents": [p.to_dict() for p in self.patents],
            "test_scores": [t.to_dict() for t in self.test_scores],
            "organizations": [o.to_dict() for o in self.organizations],
            "is_memorialized": self.is_memorialized,
            "creator_badge_status": self.creator_badge_status or None,
        }
        return d

    def to_flat_dict(self) -> dict[str, Any]:
        """Flat dictionary for CSV export."""
        pic = self.profile_picture
        loc = self.location

        return {
            "entity_urn": self.entity_urn,
            "member_id": self.member_id,
            "public_identifier": self.public_identifier,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "headline": self.headline,
            "about": self.about[:200] if self.about else "",
            "industry": self.industry_name,
            "profile_url": self.profile_url,
            "profile_picture_url": pic.best_url if pic else None,
            "is_open_to_work": self.is_open_to_work,
            "location": loc.display_name if loc else "",
            "country_code": loc.country_code if loc else None,
            "email": self.contact_info.email_address or "",
            "current_title": self.current_title or "",
            "current_company": self.current_company or "",
            "total_connections": self.connection_info.total_connections,
            "follower_count": self.following_state.follower_count,
            "is_connected": self.connection_info.is_connected,
            "is_following": self.following_state.is_following,
            "mutual_connections_count": self.mutual_connections.total_count,
            "skills_count": len(self.skills),
            "skills": ", ".join(s.name for s in self.skills[:10]),
            "certifications_count": len(self.certifications),
            "projects_count": len(self.projects),
            "positions_count": len(self.positions),
            "educations_count": len(self.educations),
            "courses_count": len(self.courses),
        }
