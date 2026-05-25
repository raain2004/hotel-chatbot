"""Parse và xử lý thẻ <action> từ phản hồi Claude."""
import json
import re
from typing import Any

ACTION_PATTERN = re.compile(r"<action>\s*(\{.*?\})\s*</action>", re.DOTALL)


def extract_actions(text: str) -> list[dict[str, Any]]:
    actions = []
    for match in ACTION_PATTERN.finditer(text):
        try:
            actions.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            continue
    return actions


def strip_actions(text: str) -> str:
    cleaned = ACTION_PATTERN.sub("", text)
    return cleaned.strip()
