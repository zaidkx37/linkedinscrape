"""
linkedinscrape — LinkedIn profile scraper SDK.

Quick start::

    from linkedinscrape import LinkedIn

    with LinkedIn() as li:
        profile = li.scrape("username")
        print(profile.full_name)
        print(profile.to_dict())

"""

from .client import LinkedIn
from .exceptions import (
    AuthenticationError,
    CookieExpiredError,
    LinkedInError,
    ParsingError,
    ProfileNotFoundError,
    RateLimitError,
    RequestError,
)
from .exporter import Exporter
from .models import (
    Certification,
    Company,
    ConnectionInfo,
    ContactInfo,
    Course,
    DateInfo,
    Education,
    FollowingState,
    HonorAward,
    ImageArtifact,
    Language,
    LinkedInProfile,
    Location,
    MutualConnection,
    Organization,
    Patent,
    Position,
    ProfilePicture,
    Project,
    Publication,
    School,
    Skill,
    TestScore,
    VolunteerExperience,
)

__version__ = "0.1.0"

__all__ = [
    # Client
    "LinkedIn",
    # Export
    "Exporter",
    # Exceptions
    "LinkedInError",
    "AuthenticationError",
    "CookieExpiredError",
    "ProfileNotFoundError",
    "RateLimitError",
    "RequestError",
    "ParsingError",
    # Models
    "LinkedInProfile",
    "DateInfo",
    "ImageArtifact",
    "ProfilePicture",
    "Location",
    "ContactInfo",
    "FollowingState",
    "MutualConnection",
    "ConnectionInfo",
    "Company",
    "School",
    "Position",
    "Education",
    "Skill",
    "Certification",
    "Project",
    "Language",
    "VolunteerExperience",
    "HonorAward",
    "Publication",
    "Course",
    "Patent",
    "TestScore",
    "Organization",
]
