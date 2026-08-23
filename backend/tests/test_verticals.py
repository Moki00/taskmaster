"""Tests for the vertical config system: packs validate, loader rejects bad packs, and swapping
ACTIVE_VERTICAL changes the taxonomy returned with zero code changes.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import settings
from app.models import Classification, Sentiment, Urgency
from app.verticals import VerticalConfig, VerticalConfigError, get_active_vertical, get_vertical
from app.verticals.loader import load_vertical_pack

ALL_PACK_KEYS = ["it_support", "dental_clinic", "home_services", "property_management"]


# --- every pack validates ---------------------------------------------------


@pytest.mark.parametrize("key", ALL_PACK_KEYS)
def test_all_packs_validate(key: str):
    config = get_vertical(key)
    assert isinstance(config, VerticalConfig)
    assert config.key == key
    assert config.issue_type_names  # non-empty


# --- loader rejects malformed packs -----------------------------------------


def test_loader_rejects_pack_missing_required_field(tmp_path):
    (tmp_path / "broken.yaml").write_text(
        """
key: broken
display_name: "Broken Pack"
business_description: "Missing issue_types entirely."
urgency_rules:
  - {level: LOW, definition: "low", concrete_examples: []}
  - {level: MEDIUM, definition: "medium", concrete_examples: []}
  - {level: HIGH, definition: "high", concrete_examples: []}
  - {level: CRITICAL, definition: "critical", concrete_examples: []}
reply_tone: "neutral"
business_hours:
  monday: {open: null, close: null}
  tuesday: {open: null, close: null}
  wednesday: {open: null, close: null}
  thursday: {open: null, close: null}
  friday: {open: null, close: null}
  saturday: {open: null, close: null}
  sunday: {open: null, close: null}
timezone: "UTC"
sla_by_priority:
  LOW: {first_response_minutes: 1}
  MEDIUM: {first_response_minutes: 1}
  HIGH: {first_response_minutes: 1}
  CRITICAL: {first_response_minutes: 1}
default_assignee_role: nobody
""",
        encoding="utf-8",
    )

    with pytest.raises(VerticalConfigError, match="failed validation"):
        load_vertical_pack("broken", packs_dir=tmp_path)


def test_loader_rejects_key_filename_mismatch(tmp_path):
    (tmp_path / "mismatch.yaml").write_text(
        """
key: not_mismatch
display_name: "Mismatch Pack"
business_description: "key field does not match filename"
issue_types:
  - {name: general, description: "general issues", examples: []}
urgency_rules:
  - {level: LOW, definition: "low", concrete_examples: []}
  - {level: MEDIUM, definition: "medium", concrete_examples: []}
  - {level: HIGH, definition: "high", concrete_examples: []}
  - {level: CRITICAL, definition: "critical", concrete_examples: []}
reply_tone: "neutral"
business_hours:
  monday: {open: null, close: null}
  tuesday: {open: null, close: null}
  wednesday: {open: null, close: null}
  thursday: {open: null, close: null}
  friday: {open: null, close: null}
  saturday: {open: null, close: null}
  sunday: {open: null, close: null}
timezone: "UTC"
sla_by_priority:
  LOW: {first_response_minutes: 1}
  MEDIUM: {first_response_minutes: 1}
  HIGH: {first_response_minutes: 1}
  CRITICAL: {first_response_minutes: 1}
default_assignee_role: nobody
""",
        encoding="utf-8",
    )

    with pytest.raises(VerticalConfigError, match="must match"):
        load_vertical_pack("mismatch", packs_dir=tmp_path)


def test_loader_rejects_missing_pack(tmp_path):
    with pytest.raises(VerticalConfigError, match="No vertical config pack found"):
        load_vertical_pack("does_not_exist", packs_dir=tmp_path)


# --- caching -----------------------------------------------------------------


def test_get_vertical_caches():
    assert get_vertical("it_support") is get_vertical("it_support")


# --- swapping ACTIVE_VERTICAL changes the taxonomy, zero code changes --------


def test_active_vertical_swaps_with_zero_code_changes(monkeypatch):
    monkeypatch.setattr(settings, "ACTIVE_VERTICAL", "it_support")
    it_support = get_active_vertical()
    assert it_support.key == "it_support"

    monkeypatch.setattr(settings, "ACTIVE_VERTICAL", "dental_clinic")
    dental = get_active_vertical()
    assert dental.key == "dental_clinic"

    assert it_support.issue_type_names != dental.issue_type_names
    assert "network" in it_support.issue_type_names
    assert "pain_or_emergency" in dental.issue_type_names


# --- routing -------------------------------------------------------------------


def test_resolve_assignee_prefers_specific_over_wildcard():
    config = get_vertical("it_support")
    assert config.resolve_assignee("network", Urgency.CRITICAL) == "senior_network_engineer"
    assert config.resolve_assignee("network", Urgency.LOW) == "network_technician"
    assert config.resolve_assignee("totally_unknown_type", Urgency.LOW) == config.default_assignee_role


# --- wired into app.models.Classification via validation context -------------


def _classification_payload(issue_type: str) -> dict:
    return {
        "issue_type": issue_type,
        "urgency": Urgency.HIGH,
        "summary": "test",
        "sentiment": Sentiment.ANNOYED,
        "frustration_score": 0.3,
        "business_impact": "test",
        "confidence": 0.9,
        "reasoning": "test",
    }


def test_classification_validates_against_real_vertical_taxonomy():
    config = get_vertical("it_support")

    valid = Classification.model_validate(
        _classification_payload("network"), context={"valid_issue_types": config.issue_type_names}
    )
    assert valid.issue_type == "network"

    with pytest.raises(ValidationError):
        Classification.model_validate(
            _classification_payload("not_a_real_issue_type"),
            context={"valid_issue_types": config.issue_type_names},
        )
