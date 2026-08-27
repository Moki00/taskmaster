from __future__ import annotations

import importlib

import pytest

AGENT_MODULES = [
    "intake_agent",
    "classifier_agent",
    "ticket_agent",
    "reply_agent",
    "scheduler_agent",
]


@pytest.mark.parametrize("module_name", AGENT_MODULES)
def test_agent_module_exposes_run_callable(module_name: str):
    """Each agent module must be importable and expose a run() entry point. This is the minimum
    contract needed before implementing the real agent logic, without requiring the full pipeline to
    work end-to-end yet."""
    module = importlib.import_module(f"app.agents.{module_name}")

    assert hasattr(module, "run"), f"{module_name} should define run()"
    assert callable(module.run), f"{module_name}.run should be callable"
