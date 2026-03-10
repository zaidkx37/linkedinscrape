"""Response parsers for LinkedIn Voyager API data."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .models import (
    Certification,
    Company,
    Course,
    DateInfo,
    Education,
    FollowingState,
    HonorAward,
    ImageArtifact,
    Language,
    LinkedInProfile,
    Location,
    Position,
    ProfilePicture,
    Project,
    Publication,
    School,
    Skill,
    VolunteerExperience,
)

TYPE_KEY = "$type"


class ProfileParser:
    """
    Parses LinkedIn Voyager API responses into a structured LinkedInProfile.

    Handles data from multiple endpoints:
      - GraphQL top card (Dash types)
      - Dash profile REST endpoint
      - Dash section endpoints (positions, education, skills, etc.)
      - Local JSON files (either format)
    """

    def __init__(self, top_card: list[dict[str, Any]] | None = None) -> None:
        self._top_card = top_card or []
        self._index: dict[str, dict[str, Any]] = {}
        if top_card:
            for entity in top_card:
                urn = entity.get("entityUrn", "")
                if urn:
                    self._index[urn] = entity

    def _get(self, urn: str) -> dict[str, Any] | None:
        return self._index.get(urn)

    # ── Main entry points ────────────────────────────────────────────────

    def parse_full(self, raw_data: dict[str, Any]) -> LinkedInProfile:
        """Parse the complete multi-endpoint response from the HTTP client."""
        profile = LinkedInProfile()

        # 1. Top card — identity, network, mutual connections
        top_card = raw_data.get("top_card", [])
        if top_card:
            self._top_card = top_card
            for e in top_card:
                urn = e.get("entityUrn", "")
                if urn:
                    self._index[urn] = e
            main = _find_main_profile(top_card)
            if main:
                _parse_identity(profile, main)
                _parse_top_card_picture(profile, main)
                _parse_top_card_location(profile, main)
                self._parse_connections(profile, main)
                self._parse_following(profile, main)
                self._parse_mutual_connections(profile, top_card)
                _parse_pdf_url(profile, main)
                _parse_status(profile, main)
                self._fill_missing_from_fallbacks(profile, main)

        # 2. Dash profile (decorated) — geo, industry, email, about
        dash_entities = raw_data.get("dash_profile") or []
        if dash_entities:
            for e in dash_entities:
                urn = e.get("entityUrn", "")
                if urn:
                    self._index[urn] = e
            self._merge_dash_profile(profile, dash_entities)

        # 3. Section endpoints
        sections = raw_data.get("sections", {})
        _parse_positions(profile, sections.get("positions", []), self._index)
        _parse_educations(profile, sections.get("educations", []), self._index)
        _parse_skills(profile, sections.get("skills", []))
        _parse_certifications(profile, sections.get("certifications", []))
        _parse_projects(profile, sections.get("projects", []))
        _parse_languages(profile, sections.get("languages", []))
        _parse_volunteers(profile, sections.get("volunteers", []))
        _parse_honors(profile, sections.get("honors", []))
        _parse_publications(profile, sections.get("publications", []))
        _parse_courses(profile, sections.get("courses", []))

        return profile

    def parse_local(self, entities: list[dict[str, Any]]) -> LinkedInProfile:
        """Parse a local JSON file (flat array from any endpoint)."""
        self._top_card = entities
        for e in entities:
            urn = e.get("entityUrn", "")
            if urn:
                self._index[urn] = e

        profile = LinkedInProfile()
        main = _find_main_profile(entities)
        if main:
            _parse_identity(profile, main)
            _parse_top_card_picture(profile, main)
            _parse_top_card_location(profile, main)
            self._parse_connections(profile, main)
            self._parse_following(profile, main)
            self._parse_mutual_connections(profile, entities)
            _parse_pdf_url(profile, main)
            _parse_status(profile, main)
            self._fill_missing_from_fallbacks(profile, main)
            self._resolve_geo_location(profile, main, entities)
            self._resolve_industry(profile, main, entities)

        _parse_positions(profile, entities, self._index)
        _parse_educations(profile, entities, self._index)
        _parse_skills(profile, entities)
        _parse_certifications(profile, entities)
        _parse_projects(profile, entities)
        _parse_languages(profile, entities)
        _parse_volunteers(profile, entities)
        _parse_honors(profile, entities)
        _parse_publications(profile, entities)
        _parse_courses(profile, entities)

        return profile

    # ── Instance methods (need self._index / self._top_card) ─────────────

    def _parse_connections(self, profile: LinkedInProfile, raw: dict[str, Any]) -> None:
        conn_data = raw.get("connections", {})
        paging = conn_data.get("paging", {})
        profile.connection_info.total_connections = paging.get("total", 0)

        for entity in self._top_card:
            if entity.get(TYPE_KEY, "").endswith("MemberRelationship"):
                member_rel = entity.get("memberRelationship", {})
                if member_rel.get("*connection") or member_rel.get("connection"):
                    profile.connection_info.is_connected = True

        for entity in self._top_card:
            if (
                entity.get(TYPE_KEY, "").endswith("Connection")
                and entity.get("*connectedMemberResolutionResult") == raw.get("entityUrn")
            ):
                created_ms = entity.get("createdAt")
                if created_ms:
                    profile.connection_info.connected_at = datetime.fromtimestamp(
                        created_ms / 1000, tz=timezone.utc
                    )
                break

    def _parse_following(self, profile: LinkedInProfile, raw: dict[str, Any]) -> None:
        urn = raw.get("*followingState", "")
        data = self._get(urn) if urn else None
        if data:
            profile.following_state = FollowingState(
                follower_count=data.get("followerCount", 0),
                is_following=data.get("following", False),
            )

    def _parse_mutual_connections(
        self, profile: LinkedInProfile, entities: list[dict[str, Any]]
    ) -> None:
        for e in entities:
            if not e.get(TYPE_KEY, "").endswith("Insight"):
                continue
            text = e.get("text", {}).get("text", "")
            if "mutual connection" not in text.lower():
                continue
            profile.mutual_connections.browse_url = e.get("navigationUrl", "")
            count_match = re.search(r"(\d+)\s+other\s+mutual", text)
            names = _extract_names_from_insight(text)
            profile.mutual_connections.names = names
            extra = int(count_match.group(1)) if count_match else 0
            profile.mutual_connections.total_count = len(names) + extra
            break

    def _fill_missing_from_fallbacks(
        self, profile: LinkedInProfile, raw: dict[str, Any]
    ) -> None:
        if not profile.first_name and not profile.last_name:
            edge_urn = raw.get("*edgeSetting", "")
            edge = self._get(edge_urn) if edge_urn else None
            if edge:
                title = edge.get("title", "")
                prefix = "Manage notifications about "
                if title.startswith(prefix):
                    parts = title[len(prefix):].strip().split(None, 1)
                    profile.first_name = parts[0] if parts else ""
                    profile.last_name = parts[1] if len(parts) > 1 else ""

        if not profile.public_identifier:
            actions = raw.get("profileStatefulProfileActions", {})
            for action in actions.get("overflowActionsResolutionResults", []):
                url = action.get("shareProfileUrlViaMessage", "")
                if url and "linkedin.com/in/" in url:
                    profile.public_identifier = url.rstrip("/").split("/in/")[-1]
                    break

        if profile.public_identifier and not profile.profile_url:
            profile.profile_url = f"https://www.linkedin.com/in/{profile.public_identifier}"

    def _merge_dash_profile(
        self, profile: LinkedInProfile, entities: list[dict[str, Any]]
    ) -> None:
        """Merge the decorated Dash profile endpoint data."""
        # Find the target profile entity by member_id, not just the biggest
        raw = None
        if profile.member_id:
            raw = next(
                (e for e in entities
                 if e.get(TYPE_KEY, "").endswith("Profile")
                 and profile.member_id in e.get("entityUrn", "")),
                None,
            )
        if not raw:
            raw = _find_main_profile(entities)
        if not raw:
            raw = next((e for e in entities if e.get(TYPE_KEY, "").endswith("Profile")), {})

        if not profile.first_name:
            profile.first_name = (raw.get("firstName") or "").strip()
        if not profile.last_name:
            profile.last_name = (raw.get("lastName") or "").strip()
        if not profile.headline:
            profile.headline = raw.get("headline", "")
        if not profile.public_identifier:
            profile.public_identifier = raw.get("publicIdentifier", "")
            if profile.public_identifier and not profile.profile_url:
                profile.profile_url = (
                    f"https://www.linkedin.com/in/{profile.public_identifier}"
                )

        # About / Summary
        summary = raw.get("summary") or ""
        if not summary:
            multi = raw.get("multiLocaleSummary")
            if isinstance(multi, dict):
                summary = next(iter(multi.values()), "")
        profile.about = (summary or "").strip()

        self._resolve_geo_location(profile, raw, entities)
        self._resolve_industry(profile, raw, entities)

        # Address enrichment
        address = raw.get("address", "")
        if not address:
            multi = raw.get("multiLocaleAddress")
            if isinstance(multi, dict):
                address = next(iter(multi.values()), "")
        location_name = raw.get("locationName", "")
        if location_name and profile.location and not profile.location.geo_location_name:
            profile.location.geo_location_name = location_name

        # Contact info
        email_data = raw.get("emailAddress")
        if isinstance(email_data, dict):
            profile.contact_info.email_address = email_data.get("emailAddress")
        elif isinstance(email_data, str):
            profile.contact_info.email_address = email_data

        for ph in raw.get("phoneNumbers") or []:
            if isinstance(ph, dict):
                inner = ph.get("phoneNumber", {})
                number = inner.get("number", "") if isinstance(inner, dict) else ""
                profile.contact_info.phone_numbers.append(
                    {"number": number, "type": ph.get("type", "")}
                )

        profile.contact_info.twitter_handles = raw.get("twitterHandles") or []

        for w in raw.get("websites") or []:
            if isinstance(w, dict):
                profile.contact_info.websites.append(
                    {"url": w.get("url", ""), "label": w.get("category", "")}
                )
            else:
                profile.contact_info.websites.append({"url": str(w), "label": ""})

        birth = raw.get("birthDateOn")
        if birth and isinstance(birth, dict):
            profile.contact_info.birth_date = DateInfo(
                year=birth.get("year"), month=birth.get("month"), day=birth.get("day"),
            )

        # Profile picture (if not set from top card)
        if not profile.profile_picture:
            pic_data = raw.get("profilePicture")
            if pic_data:
                ref = (
                    pic_data.get("displayImageReference")
                    or pic_data.get("displayImage")
                    or {}
                )
                vector = ref.get("vectorImage")
                if vector:
                    profile.profile_picture = ProfilePicture(
                        display_image_urn=pic_data.get("displayImageUrn", ""),
                        a11y_text=pic_data.get("a11yText", ""),
                        artifacts=_parse_artifacts(vector),
                    )

        # Background picture
        if not profile.background_picture:
            bg = raw.get("backgroundPicture")
            if bg:
                ref = bg.get("displayImageReference") or bg.get("displayImage") or {}
                vector = ref.get("vectorImage")
                if vector:
                    profile.background_picture = ProfilePicture(
                        artifacts=_parse_artifacts(vector),
                    )

    def _resolve_geo_location(
        self,
        profile: LinkedInProfile,
        raw: dict[str, Any],
        entities: list[dict[str, Any]],
    ) -> None:
        geo_loc = raw.get("geoLocation") or {}
        geo_urn = geo_loc.get("geoUrn") or geo_loc.get("*geo") or ""

        geo_entity = self._get(geo_urn) if geo_urn else None
        if not geo_entity:
            for e in entities:
                if e.get(TYPE_KEY, "").endswith("Geo") and e.get("entityUrn") == geo_urn:
                    geo_entity = e
                    break

        display_name = geo_entity.get("defaultLocalizedName", "") if geo_entity else ""

        if not profile.location:
            loc_data = raw.get("location") or {}
            profile.location = Location(
                country_code=loc_data.get("countryCode"),
                postal_code=loc_data.get("postalCode"),
                geo_place=loc_data.get("preferredGeoPlace"),
            )

        if display_name:
            profile.location.geo_location_name = display_name

    def _resolve_industry(
        self,
        profile: LinkedInProfile,
        raw: dict[str, Any],
        entities: list[dict[str, Any]],
    ) -> None:
        if profile.industry_name:
            return
        industry_name = raw.get("industryName", "")
        if industry_name:
            profile.industry_name = industry_name
            return

        industry_urn = raw.get("industryUrn", "")
        if not industry_urn:
            return

        industry_entity = self._get(industry_urn)
        if not industry_entity:
            for e in entities:
                if e.get("entityUrn") == industry_urn:
                    industry_entity = e
                    break
        if industry_entity:
            profile.industry_name = industry_entity.get("name", "")


# ── Pure functions (no instance state needed) ────────────────────────────────


def _find_main_profile(entities: list[dict[str, Any]]) -> dict[str, Any] | None:
    profiles = [e for e in entities if e.get(TYPE_KEY, "").endswith("Profile")]
    best = None
    best_score = 0
    for p in profiles:
        score = sum(1 for k in ("headline", "location", "connections", "firstName") if k in p)
        score += len(p)
        if score > best_score:
            best_score = score
            best = p
    return best


def _parse_identity(profile: LinkedInProfile, raw: dict[str, Any]) -> None:
    profile.entity_urn = raw.get("entityUrn", "")
    profile.member_id = _extract_member_id(profile.entity_urn)
    profile.public_identifier = raw.get("publicIdentifier", "")
    profile.first_name = (raw.get("firstName") or "").strip()
    profile.last_name = (raw.get("lastName") or "").strip()
    profile.headline = raw.get("headline", "")
    if profile.public_identifier:
        profile.profile_url = f"https://www.linkedin.com/in/{profile.public_identifier}"


def _parse_top_card_picture(profile: LinkedInProfile, raw: dict[str, Any]) -> None:
    pic_data = raw.get("profilePicture")
    if not pic_data:
        return
    picture = ProfilePicture(
        display_image_urn=pic_data.get("displayImageUrn", ""),
        a11y_text=pic_data.get("a11yText", ""),
        frame_type=pic_data.get("frameType"),
    )
    if picture.frame_type == "OPEN_TO_WORK":
        profile.is_open_to_work = True

    resolution = pic_data.get("displayImageReferenceResolutionResult", {})
    vector = resolution.get("vectorImage") if resolution else None
    if not vector:
        display_img = pic_data.get("displayImage", {})
        vector = display_img.get("vectorImage") if display_img else None
    if vector:
        picture.artifacts = _parse_artifacts(vector)
    profile.profile_picture = picture


def _parse_top_card_location(profile: LinkedInProfile, raw: dict[str, Any]) -> None:
    loc = raw.get("location")
    if loc:
        profile.location = Location(
            country_code=loc.get("countryCode"),
            postal_code=loc.get("postalCode"),
            geo_place=loc.get("preferredGeoPlace"),
        )


def _parse_pdf_url(profile: LinkedInProfile, raw: dict[str, Any]) -> None:
    actions = raw.get("profileStatefulProfileActions", {})
    for action in actions.get("overflowActionsResolutionResults", []):
        pdf_url = action.get("saveToPdfUrl")
        if pdf_url:
            profile.profile_pdf_url = pdf_url
            break


def _parse_status(profile: LinkedInProfile, raw: dict[str, Any]) -> None:
    profile.is_memorialized = raw.get("memorialized", False)
    profile.creator_badge_status = raw.get("creatorBadgeStatus", "")


# ── Section parsers ──────────────────────────────────────────────────────────


def _parse_positions(
    profile: LinkedInProfile,
    entities: list[dict[str, Any]],
    index: dict[str, dict[str, Any]] | None = None,
) -> None:
    seen: set[str] = set()
    for e in entities:
        if "Position" not in e.get(TYPE_KEY, ""):
            continue
        urn = e.get("entityUrn", "")
        if urn in seen:
            continue
        seen.add(urn)

        position = Position(
            entity_urn=urn,
            title=(e.get("title") or "").strip(),
            company_name=(e.get("companyName") or "").strip(),
            description=(e.get("description") or "").strip(),
            location_name=(e.get("locationName") or "").strip(),
            employment_type=(e.get("employmentType") or "").strip(),
        )

        dr = e.get("dateRange") or e.get("timePeriod") or {}
        position.start_date = _parse_date(dr.get("start") or dr.get("startDate"))
        position.end_date = _parse_date(dr.get("end") or dr.get("endDate"))

        company_urn = e.get("companyUrn") or e.get("*company", "")
        if company_urn and index:
            position.company = _resolve_company(company_urn, index)

        profile.positions.append(position)


def _parse_educations(
    profile: LinkedInProfile,
    entities: list[dict[str, Any]],
    index: dict[str, dict[str, Any]] | None = None,
) -> None:
    seen: set[str] = set()
    for e in entities:
        if "Education" not in e.get(TYPE_KEY, ""):
            continue
        urn = e.get("entityUrn", "")
        if urn in seen:
            continue
        seen.add(urn)

        school_name = e.get("schoolName") or ""
        if not school_name:
            ml = e.get("multiLocaleSchoolName")
            if isinstance(ml, dict):
                school_name = next(iter(ml.values()), "")

        field_of_study = e.get("fieldOfStudy") or ""
        if not field_of_study:
            ml = e.get("multiLocaleFieldOfStudy")
            if isinstance(ml, dict):
                field_of_study = next(iter(ml.values()), "")

        education = Education(
            entity_urn=urn,
            school_name=school_name.strip(),
            degree_name=(e.get("degreeName") or "").strip(),
            field_of_study=field_of_study.strip(),
            grade=(e.get("grade") or "").strip(),
            activities=(e.get("activities") or "").strip(),
            description=(e.get("description") or "").strip(),
        )

        dr = e.get("dateRange") or e.get("timePeriod") or {}
        education.start_date = _parse_date(dr.get("start") or dr.get("startDate"))
        education.end_date = _parse_date(dr.get("end") or dr.get("endDate"))

        school_urn = e.get("schoolUrn") or e.get("*school", "")
        if school_urn and index:
            education.school = _resolve_school(school_urn, index)
        company_urn = e.get("companyUrn") or e.get("*company", "")
        if company_urn and index:
            education.company = _resolve_company(company_urn, index)

        profile.educations.append(education)


def _parse_skills(profile: LinkedInProfile, entities: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for e in entities:
        if "Skill" not in e.get(TYPE_KEY, ""):
            continue
        name = (e.get("name") or "").strip()
        if not name:
            ml = e.get("multiLocaleName")
            if isinstance(ml, dict):
                name = next(iter(ml.values()), "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        profile.skills.append(Skill(name=name, entity_urn=e.get("entityUrn", "")))


def _parse_certifications(
    profile: LinkedInProfile, entities: list[dict[str, Any]]
) -> None:
    seen: set[str] = set()
    for e in entities:
        if "Certification" not in e.get(TYPE_KEY, ""):
            continue
        urn = e.get("entityUrn", "")
        if urn in seen:
            continue
        seen.add(urn)

        dr = e.get("dateRange") or e.get("timePeriod") or {}
        profile.certifications.append(Certification(
            name=(e.get("name") or "").strip(),
            authority=(e.get("authority") or "").strip(),
            license_number=(e.get("licenseNumber") or "").strip(),
            url=(e.get("url") or "").strip(),
            start_date=_parse_date(dr.get("start") or dr.get("startDate")),
            end_date=_parse_date(dr.get("end") or dr.get("endDate")),
        ))


def _parse_projects(profile: LinkedInProfile, entities: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for e in entities:
        if "Project" not in e.get(TYPE_KEY, ""):
            continue
        urn = e.get("entityUrn", "")
        if urn in seen:
            continue
        seen.add(urn)

        dr = e.get("dateRange") or e.get("timePeriod") or {}
        profile.projects.append(Project(
            title=(e.get("title") or "").strip(),
            description=(e.get("description") or "").strip(),
            url=(e.get("url") or "").strip(),
            start_date=_parse_date(dr.get("start") or dr.get("startDate")),
            end_date=_parse_date(dr.get("end") or dr.get("endDate")),
        ))


def _parse_languages(profile: LinkedInProfile, entities: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for e in entities:
        if "Language" not in e.get(TYPE_KEY, ""):
            continue
        name = (e.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        profile.languages.append(Language(
            name=name,
            proficiency=(e.get("proficiency") or "").strip(),
        ))


def _parse_volunteers(
    profile: LinkedInProfile, entities: list[dict[str, Any]]
) -> None:
    seen: set[str] = set()
    for e in entities:
        if "VolunteerExperience" not in e.get(TYPE_KEY, ""):
            continue
        urn = e.get("entityUrn", "")
        if urn in seen:
            continue
        seen.add(urn)
        dr = e.get("dateRange") or e.get("timePeriod") or {}
        profile.volunteer_experiences.append(VolunteerExperience(
            role=(e.get("role") or "").strip(),
            organization_name=(e.get("companyName") or "").strip(),
            cause=(e.get("cause") or "").strip(),
            description=(e.get("description") or "").strip(),
            start_date=_parse_date(dr.get("start")),
            end_date=_parse_date(dr.get("end")),
        ))


def _parse_honors(profile: LinkedInProfile, entities: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for e in entities:
        if "Honor" not in e.get(TYPE_KEY, ""):
            continue
        urn = e.get("entityUrn", "")
        if urn in seen:
            continue
        seen.add(urn)
        profile.honors_awards.append(HonorAward(
            title=(e.get("title") or "").strip(),
            issuer=(e.get("issuer") or "").strip(),
            description=(e.get("description") or "").strip(),
            issue_date=_parse_date(e.get("issueDate") or e.get("issuedOn")),
        ))


def _parse_publications(
    profile: LinkedInProfile, entities: list[dict[str, Any]]
) -> None:
    seen: set[str] = set()
    for e in entities:
        if "Publication" not in e.get(TYPE_KEY, ""):
            continue
        urn = e.get("entityUrn", "")
        if urn in seen:
            continue
        seen.add(urn)
        profile.publications.append(Publication(
            name=(e.get("name") or "").strip(),
            publisher=(e.get("publisher") or e.get("publisherName") or "").strip(),
            description=(e.get("description") or "").strip(),
            url=(e.get("url") or "").strip(),
            date=_parse_date(e.get("date") or e.get("publishedDate")),
        ))


def _parse_courses(profile: LinkedInProfile, entities: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for e in entities:
        if "Course" not in e.get(TYPE_KEY, ""):
            continue
        urn = e.get("entityUrn", "")
        if urn in seen:
            continue
        seen.add(urn)
        profile.courses.append(Course(
            name=(e.get("name") or "").strip(),
            number=(e.get("number") or "").strip(),
        ))


# ── Helpers ──────────────────────────────────────────────────────────────────


def _extract_member_id(urn: str) -> str:
    match = re.search(r"fsd_profile:(.+)$", urn)
    return match.group(1) if match else ""


def _parse_artifacts(vector: dict[str, Any]) -> list[ImageArtifact]:
    root = vector.get("rootUrl", "")
    return [
        ImageArtifact(
            url=f"{root}{a.get('fileIdentifyingUrlPathSegment', '')}" if root else "",
            width=a.get("width", 0),
            height=a.get("height", 0),
            expires_at=(
                datetime.fromtimestamp(a["expiresAt"] / 1000, tz=timezone.utc)
                if a.get("expiresAt")
                else None
            ),
        )
        for a in vector.get("artifacts", [])
    ]


def _resolve_company(
    urn: str, index: dict[str, dict[str, Any]]
) -> Company | None:
    raw = index.get(urn)
    if not raw:
        return None
    return Company(
        entity_urn=urn,
        name=(raw.get("name") or "").strip(),
        universal_name=raw.get("universalName", ""),
        url=raw.get("url", ""),
        logo_url=_best_logo(raw),
    )


def _resolve_school(
    urn: str, index: dict[str, dict[str, Any]]
) -> School | None:
    raw = index.get(urn)
    if not raw:
        return None
    return School(
        entity_urn=urn,
        name=(raw.get("name") or "").strip(),
        url=raw.get("url", ""),
        logo_url=_best_logo(raw),
    )


def _best_logo(raw: dict[str, Any]) -> str | None:
    for key in ("logoResolutionResult", "logo"):
        container = raw.get(key)
        if not container:
            continue
        vector = container.get("vectorImage")
        if not vector and isinstance(container, dict):
            vector = container.get("com.linkedin.common.VectorImage")
        if vector:
            arts = _parse_artifacts(vector)
            if arts:
                return max(arts, key=lambda a: a.width).url
    return None


def _parse_date(raw: dict[str, Any] | None) -> DateInfo | None:
    if not raw or not isinstance(raw, dict):
        return None
    if not raw.get("year") and not raw.get("month"):
        return None
    return DateInfo(year=raw.get("year"), month=raw.get("month"), day=raw.get("day"))


def _extract_names_from_insight(text: str) -> list[str]:
    match = re.match(r"^(.+?)(?:,?\s+and\s+\d+\s+other)", text)
    if match:
        return [n.strip() for n in match.group(1).split(",") if n.strip()]
    return []


def extract_member_id_from_top_card(top_card: list[dict[str, Any]]) -> str | None:
    """Extract the profile member_id (ACoAA...) from top card entities."""
    for entity in top_card:
        urn = entity.get("entityUrn", "")
        etype = entity.get(TYPE_KEY, "")
        if (
            "Profile" in etype
            and "fsd_profile:" in urn
            and ("headline" in entity or "location" in entity or "connections" in entity)
        ):
            return urn.split("fsd_profile:")[-1]
    for entity in top_card:
        urn = entity.get("entityUrn", "")
        if "fsd_profile:" in urn and entity.get(TYPE_KEY, "").endswith("Profile"):
            return urn.split("fsd_profile:")[-1]
    return None
