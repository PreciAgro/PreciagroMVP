import pytest
from ..dialog.safety_ui import SafetyUI
from ..dialog.dialog_policy import DialogPolicy


def test_safety_ui_sanitize():
    ui = SafetyUI()
    safe_text = ui.sanitize_response("This is safe.")
    assert safe_text == "This is safe."

    unsafe_text = ui.sanitize_response("This is UNSAFE content.")
    assert "cannot provide" in unsafe_text


def test_dialog_policy_risk():
    policy = DialogPolicy()
    agrollm_response = {
        "content": "Use chemical X",
        "flags": {"high_risk": True, "risk_details": "Toxic"},
    }
    action = policy.determine_action("How to kill bugs?", agrollm_response, {})
    assert action["action"] == "confirm_risk"
