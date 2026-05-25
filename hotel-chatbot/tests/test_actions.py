from app.core.actions import extract_actions, strip_actions


def test_extract_single_action():
    text = 'OK <action>{"type": "check_availability", "check_in": "2026-06-01"}</action>'
    actions = extract_actions(text)
    assert len(actions) == 1
    assert actions[0]["type"] == "check_availability"


def test_strip_actions():
    text = "Xin chào! <action>{\"type\": \"transfer_human\"}</action>"
    assert strip_actions(text) == "Xin chào!"
