"""Generation-only annotation checks and atomic, text-preserving repairs."""
from __future__ import annotations

import copy
import re
from typing import Any

from .common import units_need_space, units_text
from .validation import _validate_units

REPLIES = {"אין בעיה", "תודה רבה", "בוקר טוב", "יום טוב", "כל הכבוד", "בסדר גמור"}
LABEL = re.compile(r"^[\u0590-\u05ff׳״'\" -]{1,30}:\s*")
WORD = re.compile(r"[^\W_]+(?:[׳״'־-][^\W_]+)*", re.UNICODE)


def segmentation_errors(units: list[dict[str, Any]], *, title: bool = False, dialog: bool = False) -> list[str]:
    errors = []
    text = units_text(units)
    spans = []
    offset = 0
    for index, unit in enumerate(units):
        if index and units_need_space(units[index - 1], unit):
            offset += 1
        value = unit["text"]
        spans.append((offset, offset + len(value), unit))
        offset += len(value)
        if unit["type"] != "separator" and len(value.split()) > 4:
            errors.append("lexical unit exceeds four words")
    start = 0
    label = LABEL.match(text) if dialog else None
    if label:
        start = label.end()
    for boundary in re.finditer(r"[.!?…]+(?:[\"׳״')\]}]*)", text):
        end = boundary.start()
        owners = [unit for left, right, unit in spans
                  if unit["type"] != "separator" and WORD.search(text[max(left, start):min(right, end)])
                  and max(left, start) < min(right, end)]
        sentence = text[start:end].strip().strip('"׳״()[] ')
        if len(owners) == 1 and len(WORD.findall(sentence)) >= 2:
            unit = owners[0]
            name_only = unit["type"] == "properNoun" and len(unit["text"].split()) <= 4 and not re.search(r"[.!?…]", unit["text"].rstrip('.!?…'))
            if not name_only and sentence not in REPLIES:
                errors.append("complete sentence is one lexical unit")
        start = boundary.end()
    return list(dict.fromkeys(errors))


def affected_groups(story: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for level_id, level in story["levels"].items():
        context = "\n".join(units_text(p) for p in level["paragraphs"])
        groups = [("title", level["title"]), ("teaser", level["teaser"])]
        groups.extend((f"paragraphs/{i}", units) for i, units in enumerate(level["paragraphs"]))
        for field, units in groups:
            errors = segmentation_errors(units, title=field == "title", dialog=story["type"] == "dialog" and field.startswith("paragraphs/"))
            if errors:
                result.append({"id": f"{level_id}/{field}", "level": level_id, "field": field,
                               "text": units_text(units), "context": context, "errors": errors})
    return result


def repair_schema(groups: list[dict[str, Any]], unit_schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object", "properties": {"repairs": {
            "type": "array", "minItems": len(groups), "maxItems": len(groups),
            "items": {"type": "object", "properties": {
                "id": {"type": "string", "enum": [g["id"] for g in groups]},
                "units": {"type": "array", "items": unit_schema, "minItems": 1},
            }, "required": ["id", "units"], "additionalProperties": False},
        }}, "required": ["repairs"], "additionalProperties": False,
    }


def apply_repairs(story: dict[str, Any], groups: list[dict[str, Any]], payload: dict[str, Any], locales: list[str]) -> tuple[dict[str, Any] | None, list[str]]:
    repairs = payload.get("repairs") if isinstance(payload, dict) else None
    if not isinstance(repairs, list) or any(not isinstance(r, dict) for r in repairs):
        return None, ["expected repair records"]
    ids = [r.get("id") for r in repairs]
    expected = {g["id"] for g in groups}
    if any(not isinstance(key, str) for key in ids) or len(ids) != len(expected) or set(ids) != expected:
        return None, ["repair must return each requested group exactly once"]
    candidate = copy.deepcopy(story)
    originals = {g["id"]: g for g in groups}
    errors: list[str] = []
    for repair in repairs:
        group = originals[repair["id"]]
        units = repair.get("units")
        structural: list[str] = []
        _validate_units(units, group["id"], locales, structural)
        if structural:
            errors.extend(structural)
            continue
        if units_text(units) != group["text"]:
            errors.append(f"{group['id']}: repair changed frozen Hebrew")
        for unit in units:
            if unit["type"] == "separator" and any(c.isalpha() for c in unit["text"]):
                errors.append(f"{group['id']}: language-bearing separator")
        field = group["field"]
        level = candidate["levels"][group["level"]]
        if field.startswith("paragraphs/"):
            level["paragraphs"][int(field.split("/")[1])] = units
        else:
            level[field] = units
    if errors:
        return None, errors
    remaining = affected_groups(candidate)
    if remaining:
        return None, [f"{g['id']}: {'; '.join(g['errors'])}" for g in remaining]
    return candidate, []
