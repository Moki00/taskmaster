"""Tests for the vertical config system: packs validate, loader rejects bad packs, and swapping
ACTIVE_VERTICAL changes the taxonomy returned with zero code changes.
"""
from __future__ import annotations

from collections.abc import Callable

import pytest
import yaml
from pydantic import ValidationError

from app.config import settings
from app.models import Classification, Sentiment, Urgency
from app.verticals import VerticalConfig, VerticalConfigError, get_active_vertical, get_vertical
from app.verticals.loader import PACKS_DIR, load_vertical_pack

ALL_PACK_KEYS = ["it_support", "dental_clinic", "home_services", "property_management"]


def _write_pack_from_dict(tmp_path, mutate: Callable[[dict], None], filename: str = "custom"):
  """Create a temporary pack by changing structured data, not YAML text."""
  payload = yaml.safe_load((PACKS_DIR / "it_support.yaml").read_text(encoding="utf-8"))
  mutate(payload)
  payload["key"] = filename
  path = tmp_path / f"{filename}.yaml"
  path.write_text(yaml.dump(payload), encoding="utf-8")
  return path


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


def test_loader_rejects_malformed_yaml(tmp_path):
  (tmp_path / "malformed.yaml").write_text("key: [unterminated", encoding="utf-8")

  with pytest.raises(VerticalConfigError, match="not valid YAML"):
    load_vertical_pack("malformed", packs_dir=tmp_path)


@pytest.mark.parametrize("timezone", ["Not/ARealZone", "America/Definitely-Not-Real"])
def test_loader_rejects_invalid_timezone(tmp_path, timezone: str):
  _write_pack_from_dict(tmp_path, lambda payload: payload.update(timezone=timezone))

  with pytest.raises(VerticalConfigError, match="not a valid IANA timezone"):
    load_vertical_pack("custom", packs_dir=tmp_path)


@pytest.mark.parametrize("time_value", ["09:60", "25:00", "9am"])
def test_loader_rejects_invalid_business_hour_format(tmp_path, time_value: str):
  _write_pack_from_dict(
    tmp_path,
    lambda payload: payload["business_hours"]["monday"].update(open=time_value),
  )

  with pytest.raises(VerticalConfigError, match="failed validation"):
    load_vertical_pack("custom", packs_dir=tmp_path)


@pytest.mark.parametrize("missing_field", ["open", "close"])
def test_loader_rejects_unpaired_business_hour(tmp_path, missing_field: str):
  def remove_field(payload: dict) -> None:
    payload["business_hours"]["monday"].pop(missing_field)

  _write_pack_from_dict(tmp_path, remove_field)

  with pytest.raises(VerticalConfigError, match="open and close must both be set"):
    load_vertical_pack("custom", packs_dir=tmp_path)


def test_loader_rejects_duplicate_issue_types(tmp_path):
  def duplicate_issue_type(payload: dict) -> None:
    payload["issue_types"][1]["name"] = payload["issue_types"][0]["name"]

  _write_pack_from_dict(tmp_path, duplicate_issue_type)

  with pytest.raises(VerticalConfigError, match="issue_types names must be unique"):
    load_vertical_pack("custom", packs_dir=tmp_path)


def test_loader_rejects_incomplete_urgency_rules(tmp_path):
  def remove_critical_rule(payload: dict) -> None:
    payload["urgency_rules"] = [
      rule for rule in payload["urgency_rules"] if rule["level"] != "CRITICAL"
    ]

  _write_pack_from_dict(tmp_path, remove_critical_rule)

  with pytest.raises(VerticalConfigError, match="urgency_rules must cover exactly"):
    load_vertical_pack("custom", packs_dir=tmp_path)


def test_loader_rejects_incomplete_sla_definitions(tmp_path):
  _write_pack_from_dict(tmp_path, lambda payload: payload["sla_by_priority"].pop("CRITICAL"))

  with pytest.raises(VerticalConfigError, match="sla_by_priority must cover exactly"):
    load_vertical_pack("custom", packs_dir=tmp_path)


def test_loader_rejects_routing_rule_for_unknown_issue_type(tmp_path):
  def add_unknown_route(payload: dict) -> None:
    payload["routing_table"].append(
      {"issue_type": "not_declared", "assignee_role": "somebody"}
    )

  _write_pack_from_dict(tmp_path, add_unknown_route)

  with pytest.raises(VerticalConfigError, match="routing_table references unknown issue_type"):
    load_vertical_pack("custom", packs_dir=tmp_path)


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
