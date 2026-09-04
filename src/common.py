from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_site_config(root: Path = ROOT) -> dict[str, Any]:
    return read_json(root / "config" / "site.json")


def load_level_config(root: Path = ROOT) -> list[dict[str, Any]]:
    payload = read_json(root / "config" / "reading-levels.json")
    return payload["levels"]


def load_locales(root: Path = ROOT) -> dict[str, dict[str, str]]:
    site = load_site_config(root)
    return {
        code: read_json(root / "i18n" / f"{code}.json")
        for code in site["interfaceLocales"]
    }


def units_text(units: Iterable[dict[str, Any]]) -> str:
    unit_list = list(units)
    parts: list[str] = []
    for index, unit in enumerate(unit_list):
        if index and units_need_space(unit_list[index - 1], unit):
            parts.append(" ")
        parts.append(str(unit.get("text", "")))
    return "".join(parts)


def units_need_space(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    """Restore readable spacing when generated lexical units omit space tokens."""
    previous_text = str(previous.get("text", ""))
    current_text = str(current.get("text", ""))
    if not previous_text or not current_text or previous_text[-1].isspace() or current_text[0].isspace():
        return False

    no_space_punctuation = "-־–—/"
    closing_punctuation = ".,!?;:%…)]}׳״'\""
    opening_punctuation = "([{׳״'\""
    if current_text[0] in closing_punctuation or current_text[0] in no_space_punctuation:
        return False
    if previous_text[-1] in opening_punctuation or previous_text[-1] in no_space_punctuation:
        return False

    if current.get("type") == "separator":
        return current_text.isalpha()
    if previous.get("type") == "separator" and previous_text.isalpha():
        return False
    return True


def hebrew_word_count(level: dict[str, Any]) -> int:
    words = 0
    for paragraph in level.get("paragraphs", []):
        for unit in paragraph:
            if unit.get("type") != "separator":
                words += max(1, len(str(unit.get("text", "")).split()))
    return words


def story_minutes(story: dict[str, Any], level_id: str, levels: list[dict[str, Any]]) -> int:
    level_config = next(item for item in levels if item["id"] == level_id)
    count = hebrew_word_count(story["levels"][level_id])
    return max(1, math.ceil(count / int(level_config["learnerWordsPerMinute"])))


def issue_minutes(issue: dict[str, Any], level_id: str, levels: list[dict[str, Any]]) -> int:
    return sum(story_minutes(story, level_id, levels) for story in issue["stories"])


def ensure_base_path(value: str) -> str:
    return f"/{value.strip('/')}/" if value.strip("/") else "/"


def site_url(path: str, base_path: str) -> str:
    base = ensure_base_path(base_path)
    return f"{base}{path.lstrip('/')}" if path else base


def normalized_url(value: str) -> str:
    """Normalize URL spelling for provenance and duplicate comparisons."""
    parsed = urlsplit(value)
    tracking_keys = {
        "dclid",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "msclkid",
    }
    query = urlencode(
        sorted(
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.casefold().startswith("utm_") and key.casefold() not in tracking_keys
        ),
        doseq=True,
    )
    return urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            parsed.path.rstrip("/"),
            query,
            "",
        )
    )
