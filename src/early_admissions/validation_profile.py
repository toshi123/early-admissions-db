"""Explicit validation profiles for production and candidate inspection builds."""

from __future__ import annotations

from typing import Final


PRODUCTION_PROFILE: Final = "production"
CANDIDATE_AUDIT_PROFILE: Final = "candidate_audit"
VALIDATION_PROFILES: Final = (PRODUCTION_PROFILE, CANDIDATE_AUDIT_PROFILE)


def normalize_validation_profile(value: str) -> str:
    """Return the canonical profile name or raise for an unsupported value."""

    canonical = value.replace("-", "_")
    if canonical not in VALIDATION_PROFILES:
        choices = ", ".join(name.replace("_", "-") for name in VALIDATION_PROFILES)
        raise ValueError(
            f"Unsupported validation profile {value!r}; expected one of: {choices}."
        )
    return canonical


def publication_status(profile: str) -> str:
    """Return the publication classification attached to an artifact manifest."""

    normalized = normalize_validation_profile(profile)
    if normalized == CANDIDATE_AUDIT_PROFILE:
        return "inspection_only_candidate_audit"
    return "published_after_all_validations_passed"


def is_production(profile: str) -> bool:
    return normalize_validation_profile(profile) == PRODUCTION_PROFILE
