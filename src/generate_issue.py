from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from time import monotonic
from typing import Any
from unicodedata import category as unicode_category

from .common import (
    ROOT,
    issue_minutes,
    load_level_config,
    load_site_config,
    normalized_url,
    read_json,
)
from .validation import (
    briefs_are_near_duplicates,
    is_valid_https_url,
    is_meaningful_english,
    slugs_are_near_duplicates,
    validate_issue,
)


CATEGORIES = [
    "science",
    "technology",
    "city",
    "food",
    "culture",
    "nature",
    "travel",
    "work",
    "consumer",
    "transport",
    "history",
    "everyday",
]
PROVENANCE_ERRORS_KEY = "_provenanceErrors"
SOURCED_DISCOVERY_ATTEMPTS = 3
SOURCED_CANDIDATE_COUNT = 36
CURRENT_CANDIDATE_TARGET = 12
HISTORY_CANDIDATE_TARGET = 24
HISTORY_RESEARCH_REQUEST_FAILURE_LIMIT = 2
HISTORY_RESEARCH_MIN_BEATS = 8
HISTORY_RESEARCH_MAX_BEATS = 12
GENERATED_PLANNING_ATTEMPTS = 3
ADAPTATION_ATTEMPTS = 2
# Article validation failures are isolated by keeping every adaptation request to one story.
ADAPTATION_BATCH_SIZE = 1
CURRENT_TARGET = 4
HISTORY_TARGET = 7
EVERYDAY_TARGET = 2
DIALOG_TARGET = 2
HISTORY_FAMILIES = ["person", "israeliIndustry", "culture", "event", "place", "archaeology"]
HISTORY_REQUIRED_BEAT_ROLES = {"setup", "action", "turningPoint", "outcome"}
HISTORY_BEAT_ROLES = [*sorted(HISTORY_REQUIRED_BEAT_ROLES), "consequence", "detail"]
HISTORY_BEAT_CONTRACT_KEY = "_storyBeatContract"
DISCOVERY_SOURCE_KEY = "discoverySource"
ISRAELI_HISTORY_SOURCE_MINIMUMS = {
    "wikimedia": 12,
    "nationalLibraryPress": 6,
    "stateVisualArchives": 4,
    "cultureArchives": 2,
}
WORLDWIDE_HISTORY_SOURCE = "worldwideFallback"
HISTORY_CANDIDATE_MINIMUMS = {
    "person": 6,
    "israeliIndustry": 6,
    "culture": 6,
    "event": 4,
}
HISTORY_SELECTION_GROUPS = [
    ("person",),
    ("israeliIndustry",),
    ("culture",),
    ("event", "place"),
    ("person",),
    ("israeliIndustry",),
    ("culture",),
]


def _log(message: str) -> None:
    timestamp = datetime.now(UTC).strftime("%H:%M:%S UTC")
    print(f"[{timestamp}] {_safe_log_text(message)}", flush=True)


def _log_prompt(phase: str, instructions: str, request: str) -> None:
    """Log the exact role messages safely while retaining readable line breaks."""
    _log(f"{phase}: full LLM prompt follows")
    for role, content in (("SYSTEM", instructions), ("USER", request)):
        _log(f"{phase}: ----- {role} -----")
        for line in content.split("\n"):
            _log(f"{phase}: {line}")
    _log(f"{phase}: ----- END PROMPT -----")


def _safe_log_text(value: object) -> str:
    escaped: list[str] = []
    for character in str(value):
        codepoint = ord(character)
        unsafe = unicode_category(character).startswith("C") or unicode_category(character) in {"Zl", "Zp"}
        if not unsafe:
            escaped.append(character)
        elif codepoint <= 0xFF:
            escaped.append(f"\\x{codepoint:02x}")
        elif codepoint <= 0xFFFF:
            escaped.append(f"\\u{codepoint:04x}")
        else:
            escaped.append(f"\\U{codepoint:08x}")
    return "".join(escaped)


def _error_report(errors: list[str]) -> str:
    return "\n- ".join(_safe_log_text(error) for error in errors)


def _log_validation_errors(phase: str, errors: list[str], limit: int = 20) -> None:
    unique_errors = list(dict.fromkeys(errors))
    _log(f"{phase}: validation failed with {len(unique_errors)} unique error(s)")
    for error in unique_errors[:limit]:
        print(f"  - {_safe_log_text(error)}", flush=True)
    if len(unique_errors) > limit:
        print(f"  - … and {len(unique_errors) - limit} more", flush=True)


def _generated_external_urls(stories: list[dict[str, Any]]) -> set[str]:
    urls = {
        source["url"]
        for story in stories
        for source in story.get("sources", [])
        if isinstance(source, dict) and isinstance(source.get("url"), str)
    }
    for story in stories:
        image = story.get("image")
        if not isinstance(image, dict):
            continue
        for field in ("url", "rightsUrl"):
            if isinstance(image.get(field), str):
                urls.add(image[field])
    return urls


def _unit_schema(locales: list[str]) -> dict[str, Any]:
    translations = {
        "type": "object",
        "properties": {locale: {"type": "string"} for locale in locales},
        "required": locales,
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "text": {"type": "string", "pattern": ".+"},
            "type": {"type": "string", "enum": ["word", "expression", "properNoun", "separator"]},
            "translations": translations,
        },
        "required": ["text", "type", "translations"],
        "additionalProperties": False,
    }


def _story_batch_schema(
    minimum_count: int,
    maximum_count: int,
    levels: list[dict[str, Any]],
    locales: list[str],
    image_locales: list[str],
) -> dict[str, Any]:
    unit = _unit_schema(locales)
    unit_list = {"type": "array", "items": unit, "minItems": 1}
    level = {
        "type": "object",
        "properties": {
            "title": unit_list,
            "teaser": unit_list,
            "paragraphs": {
                "type": "array",
                "items": unit_list,
                "minItems": 4,
                "maxItems": 12,
            },
        },
        "required": ["title", "teaser", "paragraphs"],
        "additionalProperties": False,
    }
    level_map = {
        "type": "object",
        "properties": {item["id"]: level for item in levels},
        "required": [item["id"] for item in levels],
        "additionalProperties": False,
    }
    source = {
        "type": "object",
        "properties": {
            "publisher": {"type": "string"},
            "title": {"type": "string"},
            "url": {"type": "string"},
        },
        "required": ["publisher", "title", "url"],
        "additionalProperties": False,
    }
    image_object = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "sourceUrl": {"type": "string"},
            "credit": {"type": "string"},
            "rightsUrl": {"type": "string"},
            "rightsLabel": {"type": "string"},
            "alt": {
                "type": "object",
                "properties": {locale: {"type": "string"} for locale in image_locales},
                "required": image_locales,
                "additionalProperties": False,
            },
        },
        "required": ["url", "sourceUrl", "credit", "rightsUrl", "rightsLabel", "alt"],
        "additionalProperties": False,
    }
    everyday_meta = {
        "type": "object",
        "properties": {
            "domain": {"type": "string"},
            "scenario": {"type": "string"},
            "lexicalThemes": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "targetVocabulary": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        },
        "required": ["domain", "scenario", "lexicalThemes", "targetVocabulary"],
        "additionalProperties": False,
    }
    story = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"},
            "slug": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"},
            "type": {"type": "string", "enum": ["current", "everyday", "dialog", "history"]},
            "category": {"type": "string", "enum": CATEGORIES},
            "brief": {"type": "string"},
            "everydayMeta": {"anyOf": [everyday_meta, {"type": "null"}]},
            "sources": {"type": "array", "items": source},
            "image": {"anyOf": [image_object, {"type": "null"}]},
            "levels": level_map,
        },
        "required": ["id", "slug", "type", "category", "brief", "everydayMeta", "sources", "image", "levels"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "stories": {
                "type": "array",
                "items": story,
                "minItems": minimum_count,
                "maxItems": maximum_count,
            }
        },
        "required": ["stories"],
        "additionalProperties": False,
    }


def _seed_batch_schema(
    minimum_count: int,
    maximum_count: int,
    levels: list[dict[str, Any]],
    locales: list[str],
    image_locales: list[str],
    story_types: list[str] | None = None,
) -> dict[str, Any]:
    schema = copy.deepcopy(_story_batch_schema(minimum_count, maximum_count, levels, locales, image_locales))
    story = schema["properties"]["stories"]["items"]
    if story_types is not None:
        story["properties"]["type"]["enum"] = story_types
    story["properties"].pop("levels")
    story["required"].remove("levels")
    return schema


def _sourced_candidate_batch_schema(
    story_types: list[str],
    history_sources: list[str] | None = None,
) -> dict[str, Any]:
    source = {
        "type": "object",
        "properties": {
            "publisher": {"type": "string"},
            "title": {"type": "string"},
            "url": {"type": "string"},
        },
        "required": ["publisher", "title", "url"],
        "additionalProperties": False,
    }
    def candidate_schema(story_type: str) -> dict[str, Any]:
        properties: dict[str, Any] = {
            "id": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"},
            "type": {"type": "string", "enum": [story_type]},
            "category": {"type": "string", "enum": CATEGORIES},
            "historyFamily": {
                "type": "string",
                "enum": ["current"] if story_type == "current" else HISTORY_FAMILIES,
            },
            DISCOVERY_SOURCE_KEY: {
                "type": "string",
                "enum": (
                    ["current"]
                    if story_type == "current"
                    else history_sources or [*ISRAELI_HISTORY_SOURCE_MINIMUMS, WORLDWIDE_HISTORY_SOURCE]
                ),
            },
            "brief": {"type": "string"},
            "sources": {
                "type": "array",
                "items": source,
                **({"minItems": 1} if story_type == "current" else {}),
            },
        }
        required = [
            "id",
            "type",
            "category",
            "historyFamily",
            DISCOVERY_SOURCE_KEY,
            "brief",
            "sources",
        ]
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

    candidate_variants = [candidate_schema(story_type) for story_type in story_types]
    candidate = candidate_variants[0] if len(candidate_variants) == 1 else {"anyOf": candidate_variants}
    return {
        "type": "object",
        "properties": {
            "stories": {
                "type": "array",
                "items": candidate,
                "minItems": SOURCED_CANDIDATE_COUNT,
                "maxItems": SOURCED_CANDIDATE_COUNT,
            }
        },
        "required": ["stories"],
        "additionalProperties": False,
    }


def _sourced_candidate_to_seed(candidate: dict[str, Any], target_date: str) -> dict[str, Any]:
    candidate_id = str(candidate.get("id"))
    date_suffix = f"-{target_date}"
    story_id = candidate_id if candidate_id.endswith(date_suffix) else f"{candidate_id}{date_suffix}"
    seed = {
        "id": story_id,
        "slug": story_id,
        "type": candidate.get("type"),
        "category": candidate.get("category"),
        "historyFamily": candidate.get("historyFamily"),
        DISCOVERY_SOURCE_KEY: candidate.get(DISCOVERY_SOURCE_KEY),
        "brief": candidate.get("brief"),
        "everydayMeta": None,
        "sources": candidate.get("sources"),
        "image": None,
    }
    return seed


def _history_research_batch_schema(story_ids: list[str]) -> dict[str, Any]:
    source = {
        "type": "object",
        "properties": {
            "publisher": {"type": "string"},
            "title": {"type": "string"},
            "url": {"type": "string"},
        },
        "required": ["publisher", "title", "url"],
        "additionalProperties": False,
    }
    beat = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "pattern": "^b[1-9][0-9]*$"},
            "role": {"type": "string", "enum": HISTORY_BEAT_ROLES},
            "text": {"type": "string"},
            "required": {"type": "boolean"},
            "supportingSourceUrls": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["id", "role", "text", "required", "supportingSourceUrls"],
        "additionalProperties": False,
    }
    common_properties = {
        "id": {"type": "string", "enum": story_ids},
        "reason": {"type": "string"},
        "sources": {"type": "array", "items": source},
    }
    sufficient_record = {
        "type": "object",
        "properties": {
            **common_properties,
            "status": {"type": "string", "enum": ["sufficient"]},
            "storyBeats": {
                "type": "array",
                "items": beat,
                "minItems": HISTORY_RESEARCH_MIN_BEATS,
                "maxItems": HISTORY_RESEARCH_MAX_BEATS,
            },
        },
        "required": ["id", "status", "reason", "sources", "storyBeats"],
        "additionalProperties": False,
    }
    insufficient_record = {
        "type": "object",
        "properties": {
            **common_properties,
            "status": {"type": "string", "enum": ["insufficient"]},
            "storyBeats": {
                "type": "array",
                "items": beat,
                "maxItems": 0,
            },
        },
        "required": ["id", "status", "reason", "sources", "storyBeats"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "stories": {
                "type": "array",
                "items": {"anyOf": [sufficient_record, insufficient_record]},
                "minItems": len(story_ids),
                "maxItems": len(story_ids),
            }
        },
        "required": ["stories"],
        "additionalProperties": False,
    }


def _history_research_record_errors(record: dict[str, Any]) -> list[str]:
    story_id = str(record.get("id") or "unknown")
    if record.get("status") == "insufficient":
        reason = record.get("reason")
        return [] if isinstance(reason, str) and reason.strip() else [f"{story_id}: insufficient result needs a reason"]
    if record.get("status") != "sufficient":
        return [f"{story_id}: research status must be sufficient or insufficient"]

    errors: list[str] = []
    beats = record.get("storyBeats")
    if not isinstance(beats, list) or not HISTORY_RESEARCH_MIN_BEATS <= len(beats) <= HISTORY_RESEARCH_MAX_BEATS:
        errors.append(
            f"{story_id}: needs {HISTORY_RESEARCH_MIN_BEATS}–{HISTORY_RESEARCH_MAX_BEATS} researched story beats"
        )
        return errors

    seen_ids: set[str] = set()
    seen_texts: set[str] = set()
    required_roles: set[str] = set()
    forbidden_phrases = (
        "the article",
        "the feature",
        "the source",
        "the story shows",
        "shows how",
        "is presented as",
        "is framed as",
        "reflects society",
        "represents culture",
    )
    for index, beat in enumerate(beats):
        beat_path = f"{story_id}.storyBeats[{index}]"
        if not isinstance(beat, dict):
            errors.append(f"{beat_path}: expected an object")
            continue
        beat_id = beat.get("id")
        if not isinstance(beat_id, str) or not beat_id:
            errors.append(f"{beat_path}.id: required")
        elif beat_id in seen_ids:
            errors.append(f"{beat_path}.id: duplicate beat ID")
        else:
            seen_ids.add(beat_id)
        role = beat.get("role")
        if role not in HISTORY_BEAT_ROLES:
            errors.append(f"{beat_path}.role: unsupported narrative role")
        if beat.get("required") is True and isinstance(role, str):
            required_roles.add(role)
        text = beat.get("text")
        if not isinstance(text, str) or not is_meaningful_english(text):
            errors.append(f"{beat_path}.text: expected concrete English factual material")
        else:
            normalized_text = " ".join(text.casefold().split())
            if normalized_text in seen_texts:
                errors.append(f"{beat_path}.text: duplicate factual beat")
            if any(phrase in normalized_text for phrase in forbidden_phrases):
                errors.append(f"{beat_path}.text: source-summary language cannot replace an event")
            seen_texts.add(normalized_text)
    missing_roles = HISTORY_REQUIRED_BEAT_ROLES - required_roles
    if missing_roles:
        errors.append(f"{story_id}: required beats must cover {', '.join(sorted(missing_roles))}")
    return errors


def _validated_history_research(
    records: list[dict[str, Any]],
    requested_ids: list[str],
) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    records_by_id: dict[str, list[dict[str, Any]]] = {story_id: [] for story_id in requested_ids}
    errors: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            errors.append("history research returned a non-object record")
            continue
        story_id = record.get("id")
        if story_id not in records_by_id:
            errors.append(f"history research returned unexpected ID: {story_id}")
            continue
        records_by_id[str(story_id)].append(record)

    valid: dict[str, dict[str, Any]] = {}
    unresolved: list[str] = []
    for story_id in requested_ids:
        matches = records_by_id[story_id]
        if len(matches) != 1:
            errors.append(f"history research must return {story_id} exactly once; received {len(matches)}")
            unresolved.append(story_id)
            continue
        record = matches[0]
        if record.get("status") == "insufficient":
            reason = str(record.get("reason") or "no reason supplied")
            errors.append(f"{story_id}: research marked insufficient: {reason}")
            unresolved.append(story_id)
            continue
        record_errors = _history_research_record_errors(record)
        if record_errors:
            errors.extend(record_errors)
            unresolved.append(story_id)
            continue
        valid[story_id] = record
    return valid, unresolved, errors


def _public_story_seed(story: dict[str, Any]) -> dict[str, Any]:
    private_keys = {HISTORY_BEAT_CONTRACT_KEY, "historyFamily", DISCOVERY_SOURCE_KEY}
    return {key: value for key, value in story.items() if key not in private_keys}


def _pop_history_reserve(
    reserves: list[dict[str, Any]],
    preferred_family: str | None,
) -> dict[str, Any] | None:
    compatible_families = (
        {"event", "place"}
        if preferred_family in {"event", "place"}
        else {preferred_family}
    )
    match_index = next(
        (
            index
            for index, story in enumerate(reserves)
            if story.get("type") == "history"
            and story.get("historyFamily") in compatible_families
        ),
        None,
    )
    return reserves.pop(match_index) if match_index is not None else None


def _sourced_candidate_mix_errors(
    candidates: list[dict[str, Any]],
    requested_types: list[str],
    expected_history_sources: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    current = [story for story in candidates if story.get("type") == "current"]
    history = [story for story in candidates if story.get("type") == "history"]
    if set(requested_types) == {"current", "history"}:
        if len(current) != CURRENT_CANDIDATE_TARGET or len(history) != HISTORY_CANDIDATE_TARGET:
            errors.append(
                f"candidate mix must contain exactly {CURRENT_CANDIDATE_TARGET} CURRENT and "
                f"{HISTORY_CANDIDATE_TARGET} HISTORY stories"
            )
    if any(story.get("historyFamily") != "current" for story in current):
        errors.append("CURRENT candidates must use historyFamily=current")
    if any(story.get("historyFamily") not in HISTORY_FAMILIES for story in history):
        errors.append("HISTORY candidates must use a supported historyFamily")
    if any(story.get(DISCOVERY_SOURCE_KEY) != "current" for story in current):
        errors.append("CURRENT candidates must use discoverySource=current")
    if expected_history_sources is not None and "history" in requested_types:
        invalid_sources = sorted({
            str(story.get(DISCOVERY_SOURCE_KEY))
            for story in history
            if story.get(DISCOVERY_SOURCE_KEY) not in expected_history_sources
        })
        if invalid_sources:
            errors.append(
                "HISTORY candidates must use the expected discovery sources; received "
                + ", ".join(invalid_sources)
            )
        if expected_history_sources == set(ISRAELI_HISTORY_SOURCE_MINIMUMS):
            source_counts = {
                source: sum(story.get(DISCOVERY_SOURCE_KEY) == source for story in history)
                for source in ISRAELI_HISTORY_SOURCE_MINIMUMS
            }
            for source, minimum in ISRAELI_HISTORY_SOURCE_MINIMUMS.items():
                if source_counts[source] < minimum:
                    errors.append(
                        f"HISTORY candidate pool needs at least {minimum} {source} discovery stories"
                    )
    if len(history) >= HISTORY_CANDIDATE_TARGET:
        family_counts = {
            family: sum(story.get("historyFamily") == family for story in history)
            for family in HISTORY_FAMILIES
        }
        for family, minimum in HISTORY_CANDIDATE_MINIMUMS.items():
            if family_counts[family] < minimum:
                errors.append(f"HISTORY candidate pool needs at least {minimum} {family} stories")
        if family_counts["place"] > 2:
            errors.append("HISTORY candidate pool may contain at most 2 place stories")
        if family_counts["archaeology"] > 1:
            errors.append("HISTORY candidate pool may contain at most 1 archaeology story")
    return errors


def _select_sourced_candidates(
    selected: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    current_target: int,
    history_target: int,
) -> list[dict[str, Any]]:
    additions: list[dict[str, Any]] = []
    current_slots = current_target - sum(story.get("type") == "current" for story in selected)
    additions.extend(
        story for story in candidates if story.get("type") == "current"
    )
    additions = additions[:max(0, current_slots)]

    selected_history = [story for story in [*selected, *additions] if story.get("type") == "history"]
    history_pool = [story for story in candidates if story.get("type") == "history"]
    for position, family_group in enumerate(HISTORY_SELECTION_GROUPS[:history_target], start=1):
        if len(selected_history) >= history_target:
            break
        required = sum(
            previous_group == family_group
            for previous_group in HISTORY_SELECTION_GROUPS[:position]
        )
        fulfilled = sum(story.get("historyFamily") in family_group for story in selected_history)
        if fulfilled >= required:
            continue
        match = next(
            (story for story in history_pool if story.get("historyFamily") in family_group),
            None,
        )
        if match is None:
            continue
        additions.append(match)
        selected_history.append(match)
        history_pool.remove(match)

    remaining_history_slots = history_target - len(selected_history)
    if remaining_history_slots > 0 and history_target > len(HISTORY_SELECTION_GROUPS):
        preferred = [
            story
            for story in history_pool
            if story.get("historyFamily") in {"person", "israeliIndustry", "culture", "event"}
        ]
        additions.extend(preferred[:remaining_history_slots])
    return additions


def _adaptation_batch_schema(
    stories: list[dict[str, Any]],
    levels: list[dict[str, Any]],
    locales: list[str],
    image_locales: list[str],
) -> dict[str, Any]:
    full = _story_batch_schema(1, 1, levels, locales, image_locales)
    level_map = full["properties"]["stories"]["items"]["properties"]["levels"]
    level_ids = [level["id"] for level in levels]
    adaptations = []
    for story in stories:
        contract = story.get(HISTORY_BEAT_CONTRACT_KEY)
        beat_ids = [beat["id"] for beat in contract] if isinstance(contract, list) else []
        coverage = {
            "type": "object",
            "properties": {
                level_id: {
                    "type": "array",
                    "items": {"type": "string", **({"enum": beat_ids} if beat_ids else {})},
                    "maxItems": len(beat_ids),
                }
                for level_id in level_ids
            },
            "required": level_ids,
            "additionalProperties": False,
        }
        adaptations.append({
            "type": "object",
            "properties": {
                "id": {"type": "string", "enum": [story["id"]]},
                "levels": level_map,
                "coveredStoryBeatIds": coverage,
            },
            "required": ["id", "levels", "coveredStoryBeatIds"],
            "additionalProperties": False,
        })
    adaptation = adaptations[0] if len(adaptations) == 1 else {"anyOf": adaptations}
    return {
        "type": "object",
        "properties": {
            "adaptations": {
                "type": "array",
                "items": adaptation,
                "minItems": len(stories),
                "maxItems": len(stories),
            }
        },
        "required": ["adaptations"],
        "additionalProperties": False,
    }


def _duplicate_review_schema(candidate_ids: list[str]) -> dict[str, Any]:
    verdict = {
        "type": "object",
        "properties": {
            "candidateId": {"type": "string", "enum": candidate_ids},
            "isDuplicate": {"type": "boolean"},
            "matchedStoryId": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "reason": {"type": "string"},
        },
        "required": ["candidateId", "isDuplicate", "matchedStoryId", "reason"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "verdicts": {
                "type": "array",
                "items": verdict,
                "minItems": len(candidate_ids),
                "maxItems": len(candidate_ids),
            }
        },
        "required": ["verdicts"],
        "additionalProperties": False,
    }


def _read_prompts(root: Path, names: tuple[str, ...]) -> str:
    return "\n\n".join(
        (root / "prompts" / name).read_text(encoding="utf-8")
        for name in names
    )


def _recent_history(history: dict[str, Any], target: date, days: int) -> list[dict[str, Any]]:
    cutoff = target - timedelta(days=days)
    recent = []
    for item in history.get("items", []):
        try:
            item_date = date.fromisoformat(item["date"])
        except (KeyError, TypeError, ValueError):
            continue
        if cutoff <= item_date <= target:
            recent.append(
                {
                    "date": item.get("date"),
                    "storyId": item.get("storyId"),
                    "domain": item.get("domain"),
                    "scenario": item.get("scenario"),
                }
            )
    return recent


def _recent_issue_context(content_dir: Path, target: date, days: int) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    dated_paths: list[tuple[date, Path]] = []
    cutoff = target - timedelta(days=days)
    for path in content_dir.glob("????-??-??.json"):
        try:
            issue_date = date.fromisoformat(path.stem)
        except ValueError:
            continue
        if cutoff <= issue_date < target:
            dated_paths.append((issue_date, path))
    for issue_date, path in sorted(dated_paths, reverse=True):
        issue = read_json(path)
        stories = []
        for story in issue.get("stories", []):
            if not isinstance(story, dict):
                continue
            stories.append(
                {
                    "id": story.get("id"),
                    "type": story.get("type"),
                    "brief": story.get("brief"),
                    "sourceUrls": [
                        normalized_url(source["url"])
                        for source in story.get("sources", [])
                        if isinstance(source, dict) and isinstance(source.get("url"), str)
                    ],
                }
            )
        issues.append({"date": issue_date.isoformat(), "stories": stories})
    return issues


def _existing_exclusions(issue: dict[str, Any] | None) -> dict[str, Any]:
    if not issue:
        return {"stories": []}
    return {
        "stories": [
            {
                "id": story["id"],
                "type": story.get("type"),
                "brief": story["brief"],
                "sourceUrls": [normalized_url(source["url"]) for source in story["sources"]],
            }
            for story in issue["stories"]
        ],
    }


def _compact_story_record(story: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": story.get("id"),
        "type": story.get("type"),
        "brief": story.get("brief"),
        "sourceUrls": [
            normalized_url(source["url"])
            for source in story.get("sources", [])
            if isinstance(source, dict) and isinstance(source.get("url"), str)
        ],
    }
    meta = story.get("everydayMeta")
    if isinstance(meta, dict):
        record["scenario"] = meta.get("scenario")
    return record


def _forbidden_story_records(
    exclusions: dict[str, Any],
    recent_issues: list[dict[str, Any]],
    allowed_types: set[str],
) -> list[dict[str, Any]]:
    records = [
        *exclusions.get("stories", []),
        *[
            story
            for issue in recent_issues
            for story in issue.get("stories", [])
        ],
    ]
    return [record for record in records if record.get("type") in allowed_types]


def _sourced_discovery_request(
    target_date: str,
    current_count: int,
    history_count: int,
    forbidden_stories: list[dict[str, Any]],
    selected_stories: list[dict[str, Any]],
    feedback: list[str] | None = None,
    worldwide_fallback: bool = False,
) -> str:
    if current_count and history_count:
        candidate_mix = (
            f"Return both types: exactly {CURRENT_CANDIDATE_TARGET} CURRENT and "
            f"{HISTORY_CANDIDATE_TARGET} HISTORY candidates."
        )
    elif current_count:
        candidate_mix = "Every candidate should be CURRENT because only CURRENT slots remain."
    else:
        candidate_mix = "Every candidate should be HISTORY because only HISTORY slots remain."
    if worldwide_fallback:
        retry_scope = (
            "\nFINAL WORLDWIDE FALLBACK SEARCH\nThe two Israel-focused searches left sourced slots unfilled. "
            "Search worldwide only for the remaining slots, using new subjects across at least six countries or regions. "
            "Do not re-query, rename, translate, update, or find alternate coverage for any duplicate or forbidden story. "
            "For CURRENT, use practical events from the target date or previous several days. For HISTORY, use short, "
            "concrete, relatable subjects from any period; no date connection is required. Label every HISTORY candidate "
            f"with `{DISCOVERY_SOURCE_KEY}` = `{WORLDWIDE_HISTORY_SOURCE}`. Keep every editorial, source-quality, safety, "
            "and novelty rule."
        )
    elif feedback:
        retry_scope = (
            "\nRETRY ISRAEL-FOCUSED SOURCE SEARCH\nThis is a second fresh search of Israeli material, not a worldwide "
            "fallback. Use new queries across the named Israeli and Wikimedia collections and do not return alternate "
            "coverage, translations, updates, or renamed versions of rejected subjects. Search Hebrew as well as English."
        )
    else:
        retry_scope = ""
    history_source_process = (
        "- For HISTORY on this final worldwide fallback, search varied countries and source collections for concrete, "
        "relatable subjects. Use the source page as a lead to a person, company, work, decision, event, institution, "
        "invention, or ordinary-life development—not as a reason to write about the page itself. Label every HISTORY "
        f"candidate with `{DISCOVERY_SOURCE_KEY}` = `{WORLDWIDE_HISTORY_SOURCE}`."
        if worldwide_fallback else
        "- For HISTORY on this Israel-focused pass, search Israeli subjects and Israeli repositories in Hebrew as well as "
        "English. HISTORY does not need a connection to the target date or current news. Use the source page as a lead to "
        "a person, company, work, decision, event, institution, invention, or ordinary-life development—not as a reason "
        "to write about an article, photograph, archive record, museum object, or exhibition page.\n"
        "- Build the 24-candidate Israel-focused HISTORY pool from four editorial discovery lanes. Return 12 `wikimedia` "
        "candidates discovered through Hebrew or English Wikipedia or Wikidata; six `nationalLibraryPress` candidates from "
        "the National Library of Israel or Historical Jewish Press; four `stateVisualArchives` candidates from the Israel "
        "State Archives, National Photo Collection, or PikiWiki Israel; and two `cultureArchives` candidates from the Israel "
        f"Film Archive or Project Ben-Yehuda. Store the lane in `{DISCOVERY_SOURCE_KEY}`. This field records the discovery "
        "route for editorial balancing; it is not proof that every fact is supported by a returned URL."
    )
    retry = (
        "\nRETRY FEEDBACK\nThe previous attempt left sourced slots unfilled. Do not return duplicate or otherwise "
        f"rejected candidates again. Correct these problems while continuing the search: {json.dumps(feedback, ensure_ascii=False)}"
        if feedback else ""
    )
    return f"""
Target publication date: {target_date}
The issue still needs up to {current_count} CURRENT and up to {history_count} HISTORY stories. Return exactly {SOURCED_CANDIDATE_COUNT} distinct screening candidates even though fewer final slots remain. These are candidates for later deduplication and selection, not final stories. {candidate_mix}
{retry_scope}{retry}

SEARCH PROCESS
- Use web search and begin from the target date and permitted editorial areas, never from the forbidden records.
- For CURRENT, search Israeli reporting from the target date and previous several days. Search across the whole country and varied communities; do not default to Jerusalem or treat it as the center of every issue.
{history_source_process}
- Give every candidate a `historyFamily`. CURRENT uses `current`. HISTORY uses exactly one of `person`, `israeliIndustry`, `culture`, `event`, `place`, or `archaeology` according to its actual central subject, not the wording used to sell it.
- When both sourced types are requested, build the 24-candidate HISTORY portion with at least six `person`, six `israeliIndustry`, six `culture`, and four `event` candidates. If only HISTORY remains, all 36 candidates are HISTORY and must preserve those minimums while using the extra slots for the same preferred families. `person` means a specific historical person's life, work, decisions, and impact; a newly published obituary or current death report is CURRENT, not HISTORY. `israeliIndustry` means the history of an Israeli company, manufacturer, brand, cooperative, factory, trade, product, or industrial development—not today's startup, high-tech unicorn, funding round, valuation, product launch, or executive profile. `culture` covers the history of literature, music, theater, cinema, visual art, dance, design, architecture, food culture, publishing, broadcasting, or a cultural movement, work, or institution. A museum qualifies only when the story is about cultural creation, collections, or influence, not merely an old building to visit. `event` covers concrete past events, customs, education, infrastructure, transport, institutions, or everyday objects with a clear human sequence and consequence.
- `place` is optional and rare, not a required family. Return at most two `place` candidates and reject generic park-preservation, tourist-guide, trail, viewpoint, fortress-visit, or “a place where nature and history meet” pitches. A place candidate needs an exceptional, specific human story that could not be told by swapping in another location. Return at most one `archaeology` candidate.
- Order the first seven HISTORY candidates so they contain at least two `person`, two `israeliIndustry`, two `culture`, and one `event` or exceptional `place`; no more than one may be `place`, and none may be `archaeology`. Python applies the same mix when selecting the seven published HISTORY stories.
- Order candidates by editorial value within each type, not by search order. Avoid returning several places with the same generic excavation-discovery plot even when their names differ.
- Search substantially more than {SOURCED_CANDIDATE_COUNT} source pages. A rejected page does not count; continue searching for another candidate.
- Do not formulate searches from forbidden IDs, briefs, subjects, or URLs. They are comparison data only.
- Return only compact screening candidates, not search notes or adaptations.

NOVELTY CONTRACT
- A CURRENT candidate is a duplicate when it has the same central entity or subject and the same underlying event, action, announcement, change, project, or outcome as a forbidden record or selected candidate. A later status report, continuing consequence, “still” update, new article, or changed statistic about that event is still a duplicate.
- For HISTORY, first identify the candidate's primary named subject. The same street, building, archaeological site, institution, person, event, object, custom, or other primary subject used in a forbidden or selected HISTORY story is always a duplicate. A different source, excavation report, historical period, archaeological layer, newly emphasized fact, or angle about the same primary subject does not make it new.
- The same or equivalent source URL is always a duplicate. Another publisher, URL, headline, language, date, angle, or minor follow-up does not make the same underlying event new.
- A new slug, renamed people, changed wording, or cosmetic details never make a duplicate new.
Before returning the batch, perform a final rejection pass: compare each candidate's primary subject and underlying meaning—not only exact words—with every forbidden and already selected brief and URL. If it matches or uniqueness is uncertain, do not return it. Discard it and continue searching until either a genuinely different candidate is found or the response returns fewer sourced stories.

FORBIDDEN SOURCED STORIES FROM THE EXISTING ISSUE AND RECENT ISSUES:
<forbidden_story_records>
{json.dumps(forbidden_stories, ensure_ascii=False, indent=2)}
</forbidden_story_records>

ALREADY SELECTED SOURCED STORIES IN THIS RUN:
<selected_story_records>
{json.dumps(selected_stories, ensure_ascii=False, indent=2)}
</selected_story_records>

OUTPUT CONTRACT
Return exactly {SOURCED_CANDIDATE_COUNT} compact screening records. Every record contains only `id`, `type`, `category`, `historyFamily`, `{DISCOVERY_SOURCE_KEY}`, `brief`, and `sources`. CURRENT uses `{DISCOVERY_SOURCE_KEY}` = `current`. On an Israel-focused pass, HISTORY uses one of `wikimedia`, `nationalLibraryPress`, `stateVisualArchives`, or `cultureArchives`; on the final worldwide fallback it uses `worldwideFallback`. Prefer a descriptive lowercase hyphenated topic ID such as `haifa-library-late-hours`; do not use ordinal placeholders such as `current-01` or `history-02`. Keep `brief` compact and use it only to identify the underlying subject and story during deduplication and later selection. Do not research or return story beats in this screening phase.

Give every CURRENT candidate at least one distinct canonical HTTPS content-page source. For HISTORY, include a useful source when available; an empty source list is acceptable because selected subjects receive separate research. Never use homepages, section pages, search pages, generic latest pages, or liveblogs. Do not return Hebrew, story beats, level adaptations, scenario metadata, images, or prose outside the schema.
""".strip()


def _history_research_request(
    target_date: str,
    stories: list[dict[str, Any]],
    feedback: list[str] | None = None,
) -> str:
    retry = (
        "\nRETRY FEEDBACK\nCorrect every listed problem while researching only the unresolved subjects: "
        f"{json.dumps(feedback, ensure_ascii=False)}"
        if feedback else ""
    )
    return f"""
Target publication date: {target_date}

Deeply research each selected HISTORY subject below. These subjects already passed novelty review and selection. Search Hebrew and English when relevant. For Israeli subjects, prioritize Israeli archival, library, press, film, photographic, literary, official, and institutional material; for a worldwide fallback subject, use the strongest appropriate primary, archival, institutional, and biographical sources. The internal `discoverySource` value records how the screening lead was found, but is not verified provenance and must not limit follow-up research. This phase decides whether each subject can support a developed retelling and freezes its factual material; it does not write Hebrew.

<selected_history_subjects>
{json.dumps([_compact_story_record(story) | {"historyFamily": story.get("historyFamily"), DISCOVERY_SOURCE_KEY: story.get(DISCOVERY_SOURCE_KEY)} for story in stories], ensure_ascii=False, indent=2)}
</selected_history_subjects>

RESEARCH CONTRACT
- Return exactly one record for every supplied ID and no other IDs. Preserve each ID exactly.
- Search beyond the screening lead and return {HISTORY_RESEARCH_MIN_BEATS}–{HISTORY_RESEARCH_MAX_BEATS} concrete, non-overlapping English factual beats for every sufficient subject. Source links are optional: include trustworthy canonical HTTPS content pages when available, but do not mark an otherwise retellable subject insufficient merely because no usable link can be returned.
- Each beat has a stable ID (`b1`, `b2`, ...), one narrative role, factual text, a required flag, and a supporting-source URL list. The list may be empty; when it is not empty, use URLs from the record's source list.
- Required beats must collectively cover setup, action, turningPoint, and outcome. Use consequence and detail for additional supported developments.
- Facts must describe what people or institutions actually did, what changed, the problem or decision, what happened next, and the outcome. A Wikipedia page, archive record, photograph, newspaper result, museum object, film record, or literary text is a lead to the underlying story, not the story itself. Do not describe what an article, feature, exhibition, life, legacy, or institution supposedly shows, reflects, represents, or symbolizes.
- A currently running exhibition, festival listing, anniversary program, promotional institutional profile, or private collection is insufficient unless the researched material independently supplies a real historical sequence with concrete actors, decisions, changes, and outcomes.
- If research cannot support that story arc, return `insufficient`, explain why briefly, and leave storyBeats empty. Never stretch thin material, invent facts, or return generic significance claims to satisfy the schema. Missing source metadata alone is not a reason to reject a story.
- For `sufficient`, include only useful sources you actually consulted. An empty source list is valid.

Return only schema-matching data and no prose.{retry}
""".strip()


def _sourced_duplicate_review_request(
    forbidden_stories: list[dict[str, Any]],
    selected_stories: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> str:
    return f"""
Compare every candidate against every forbidden record, every already selected record, and earlier candidates in this batch. A candidate must be marked duplicate when it is the same underlying story even if its slug, wording, source, URL form, date, or angle differs.

FORBIDDEN SOURCED STORIES FROM PREVIOUS DAYS:
<forbidden_story_records>
{json.dumps(forbidden_stories, ensure_ascii=False, indent=2)}
</forbidden_story_records>

ALREADY SELECTED SOURCED STORIES IN THIS RUN:
<selected_story_records>
{json.dumps(selected_stories, ensure_ascii=False, indent=2)}
</selected_story_records>

PROPOSED CANDIDATES IN ORDER:
<candidate_story_records>
{json.dumps([_compact_story_record(story) for story in candidates], ensure_ascii=False, indent=2)}
</candidate_story_records>

Return exactly one verdict per proposed candidate ID. For a unique candidate use false, null, and a short reason. For a duplicate use true, the matched record's ID, and a short explanation of the shared underlying story. Return only schema-matching data.
""".strip()


def _duplicate_review_findings(
    review: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> tuple[set[int], list[str]]:
    candidate_ids = [story["id"] for story in candidates]
    verdicts = review.get("verdicts")
    if not isinstance(verdicts, list):
        raise RuntimeError("duplicate review returned no verdict list")
    reviewed_ids = [verdict.get("candidateId") for verdict in verdicts if isinstance(verdict, dict)]
    if (
        len(verdicts) != len(candidate_ids)
        or len(reviewed_ids) != len(candidate_ids)
        or set(reviewed_ids) != set(candidate_ids)
    ):
        raise RuntimeError("duplicate review did not classify every candidate exactly once")

    indexes_by_id = {story_id: index for index, story_id in enumerate(candidate_ids)}
    duplicate_indexes: set[int] = set()
    findings: list[str] = []
    for verdict in verdicts:
        if not isinstance(verdict.get("isDuplicate"), bool):
            raise RuntimeError("duplicate review returned an invalid verdict")
        if not verdict["isDuplicate"]:
            continue
        candidate_id = verdict["candidateId"]
        duplicate_indexes.add(indexes_by_id[candidate_id])
        matched_id = verdict.get("matchedStoryId") or "another sourced story"
        reason = verdict.get("reason") or "same underlying story"
        findings.append(f"LLM duplicate review: {candidate_id} matches {matched_id}: {reason}")
    return duplicate_indexes, findings


def _generated_planning_request(
    target_date: str,
    target_count: int,
    everyday_count: int,
    dialog_count: int,
    is_append: bool,
    forbidden_stories: list[dict[str, Any]],
    recent_history: list[dict[str, Any]],
    selected_stories: list[dict[str, Any]],
    feedback: list[str] | None = None,
) -> str:
    mode = "append new stories to the existing issue" if is_append else "complete the new issue after sourced discovery"
    retry = (
        "\nRETRY FEEDBACK\nThe previous result was rejected. Do not rewrite rejected scenarios. "
        f"Generate unrelated replacements and correct these problems: {json.dumps(feedback, ensure_ascii=False)}"
        if feedback else ""
    )
    return f"""
Target publication date: {target_date}
Task: {mode}.
Generate up to {target_count} new stories, using only EVERYDAY and DIALOG. Aim to include at least {everyday_count} EVERYDAY and {dialog_count} DIALOG stories among them; any remaining slots may use either type. These are planning targets, not publication-blocking quotas. Do not use web search and do not produce CURRENT or HISTORY stories.

Create each scenario independently from ordinary life. Give every story a concrete situation, interaction, action, clarification or reaction, and outcome. Return only English scenario briefs and metadata; do not write Hebrew adaptations.

NOVELTY CONTRACT
- A scenario is a duplicate when its practical problem or goal, interaction, and resolution substantially match a forbidden or already selected scenario.
- An identical `scenario` value is always a duplicate. Changing its identifier, names, setting details, wording, or story type does not make the same scenario new.
- Sharing only a broad domain or useful vocabulary is not a duplicate when the actual situation and resolution are different.
- Treat all forbidden records only as comparison data, never as examples or templates.
Compare every proposed scenario with all forbidden and already selected records. If it matches or uniqueness is uncertain, discard it and generate an unrelated scenario. Do not output the comparison process.

RECENT SCENARIO RECORDS:
<forbidden_scenario_records>
{json.dumps(recent_history, ensure_ascii=False, indent=2)}
</forbidden_scenario_records>

FORBIDDEN GENERATED STORIES FROM THE EXISTING ISSUE AND RECENT ISSUES:
<forbidden_story_records>
{json.dumps(forbidden_stories, ensure_ascii=False, indent=2)}
</forbidden_story_records>

ALREADY SELECTED STORIES IN THIS RUN:
<selected_story_records>
{json.dumps(selected_stories, ensure_ascii=False, indent=2)}
</selected_story_records>

OUTPUT CONTRACT
Write every `brief` in English and make the id and slug identical. Supply complete scenario metadata. Make EVERYDAY briefs support 4–5 developed story beats, and make DIALOG briefs support 8–12 useful alternating direct-speech turns with questions, clarification, reactions, and an outcome. Every story must have an empty source list and null image. Return only schema-matching data and no prose.{retry}
""".strip()


def _call_openai(
    model: str,
    instructions: str,
    request: str,
    schema: dict[str, Any],
    use_web_search: bool = True,
    phase: str = "OpenAI request",
) -> dict[str, Any]:
    started = monotonic()
    _log(f"{phase}: started with model {model}")
    try:
        from openai import OpenAI

        client = OpenAI(max_retries=2, timeout=300.0)
        parameters: dict[str, Any] = dict(
            model=model,
            input=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": request},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "daily_hebrew_story_batch",
                    "strict": True,
                    "schema": schema,
                }
            },
            store=False,
        )
        if use_web_search:
            parameters["tools"] = [{"type": "web_search", "search_context_size": "medium"}]
            parameters["include"] = ["web_search_call.action.sources"]
        _log_prompt(phase, instructions, request)
        response = client.responses.create(**parameters)
        _log(f"{phase}: response received after {monotonic() - started:.1f}s")
        if not response.output_text:
            raise RuntimeError("model returned no structured output")
        result = json.loads(response.output_text)
        response_data = response.model_dump() or {}
        consulted_urls: set[str] = set()
        for item in response_data.get("output") or []:
            if not isinstance(item, dict) or item.get("type") != "web_search_call":
                continue
            action = item.get("action") or {}
            consulted_urls.update(
                source["url"]
                for source in action.get("sources") or []
                if isinstance(source, dict) and source.get("url")
            )
            if action.get("url"):
                consulted_urls.add(action["url"])
        generated_urls = _generated_external_urls(result.get("stories", []))
        normalized_consulted = {normalized_url(url) for url in consulted_urls}
        unverified = sorted(url for url in generated_urls if normalized_url(url) not in normalized_consulted)
        if use_web_search and unverified:
            result[PROVENANCE_ERRORS_KEY] = unverified
            _log(f"{phase}: will discard {len(unverified)} unverified URL(s)")
        _log(f"{phase}: completed after {monotonic() - started:.1f}s")
        return result
    except Exception as exc:
        _log(f"{phase}: failed after {monotonic() - started:.1f}s ({type(exc).__name__})")
        raise RuntimeError(f"OpenAI generation failed ({type(exc).__name__})") from exc


def _remove_empty_lexical_units(adaptations: list[dict[str, Any]]) -> int:
    """Drop zero-length units, which carry no text and are safe to omit."""
    removed = 0
    for adaptation in adaptations:
        levels = adaptation.get("levels")
        if not isinstance(levels, dict):
            continue
        for level in levels.values():
            if not isinstance(level, dict):
                continue
            for field in ("title", "teaser"):
                units = level.get(field)
                if isinstance(units, list):
                    filtered = [unit for unit in units if not isinstance(unit, dict) or unit.get("text") != ""]
                    removed += len(units) - len(filtered)
                    level[field] = filtered
            paragraphs = level.get("paragraphs")
            if isinstance(paragraphs, list):
                for index, units in enumerate(paragraphs):
                    if not isinstance(units, list):
                        continue
                    filtered = [unit for unit in units if not isinstance(unit, dict) or unit.get("text") != ""]
                    removed += len(units) - len(filtered)
                    paragraphs[index] = filtered
    return removed


def _remove_redundant_sources(
    stories: list[dict[str, Any]],
    existing: dict[str, Any] | None,
    unverified_urls: list[str] | None = None,
) -> tuple[int, int]:
    """Discard unverified and repeated sources, allowing an empty source list."""
    seen = {
        normalized_url(source["url"])
        for story in (existing["stories"] if existing else [])
        for source in story.get("sources", [])
        if isinstance(source, dict) and isinstance(source.get("url"), str)
    }
    unverified = {normalized_url(url) for url in (unverified_urls or [])}
    removed_sources = 0
    removed_images = 0
    for story in stories:
        sources = story.get("sources")
        if not isinstance(sources, list):
            continue
        locally_unique: list[dict[str, Any]] = []
        local_urls: set[str] = set()
        for source in sources:
            if (
                not isinstance(source, dict)
                or any(
                    not isinstance(source.get(field), str) or not source[field].strip()
                    for field in ("publisher", "title", "url")
                )
                or not is_valid_https_url(source["url"])
            ):
                removed_sources += 1
                continue
            source_url = normalized_url(source["url"])
            if source_url in unverified or source_url in local_urls:
                removed_sources += 1
                continue
            local_urls.add(source_url)
            locally_unique.append(source)

        globally_unique = [
            source
            for source in locally_unique
            if not isinstance(source, dict)
            or not isinstance(source.get("url"), str)
            or normalized_url(source["url"]) not in seen
        ]
        kept = globally_unique
        removed_sources += len(locally_unique) - len(kept)
        story["sources"] = kept
        kept_urls = {
            normalized_url(source["url"])
            for source in kept
            if isinstance(source, dict) and isinstance(source.get("url"), str)
        }
        seen.update(kept_urls)
        image = story.get("image")
        if isinstance(image, dict):
            image_urls = {
                normalized_url(image[field])
                for field in ("url", "sourceUrl", "rightsUrl")
                if isinstance(image.get(field), str)
            }
            if image_urls & unverified or normalized_url(str(image.get("sourceUrl", ""))) not in kept_urls:
                story["image"] = None
                removed_images += 1
    return removed_sources, removed_images


def _adaptation_request(
    seeds: list[dict[str, Any]],
    levels: list[dict[str, Any]],
    locales: list[str],
    feedback: list[str] | None,
) -> str:
    level_payload = [
        {key: level[key] for key in ("id", "targetWords", "minimumWords", "maximumWords", "guidance")}
        for level in levels
    ]
    retry = f"\nCorrect these validation problems from the previous adaptation: {json.dumps(feedback, ensure_ascii=False)}" if feedback else ""
    return f"""
This is the adaptation phase. The story metadata, briefs, and any HISTORY storyBeats below are frozen results of completed sourced discovery and generated-scenario planning.
Create title, teaser, paragraphs, lexical segmentation, translations, and `coveredStoryBeatIds` for every listed story and level. Develop each body toward its configured targetWords and perform the prompt's one pre-segmentation length revision when needed. Do not change, extend, or infer beyond the supplied brief, scenario metadata, or HISTORY story-beat contract, and do not add facts or filler to reach a word target. A result below minimumWords remains usable and must not be padded; every researched HISTORY level must still cover every required beat ID or it will be retried. Return each story ID exactly once and no other IDs. For non-HISTORY stories, return an empty covered-story-beat list for every level.

Configured reading levels:
{json.dumps(level_payload, ensure_ascii=False, indent=2)}

Required translation locales: {json.dumps(locales)}

Frozen story briefs and metadata:
{json.dumps(seeds, ensure_ascii=False, indent=2)}
{retry}
""".strip()


def _history_adaptation_errors(
    seeds: list[dict[str, Any]],
    adaptations: list[dict[str, Any]],
    levels: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    adaptations_by_id = {
        adaptation.get("id"): adaptation
        for adaptation in adaptations
        if isinstance(adaptation, dict)
    }
    level_ids = [level["id"] for level in levels]
    for seed in seeds:
        contract = seed.get(HISTORY_BEAT_CONTRACT_KEY)
        if not isinstance(contract, list):
            continue
        story_id = str(seed.get("id"))
        adaptation = adaptations_by_id.get(story_id)
        if not isinstance(adaptation, dict):
            errors.append(f"{story_id}: missing HISTORY adaptation coverage")
            continue
        beat_ids = {beat.get("id") for beat in contract if isinstance(beat, dict)}
        required_ids = {
            beat.get("id")
            for beat in contract
            if isinstance(beat, dict) and beat.get("required") is True
        }
        coverage = adaptation.get("coveredStoryBeatIds")
        for level_id in level_ids:
            covered = coverage.get(level_id) if isinstance(coverage, dict) else None
            if not isinstance(covered, list):
                errors.append(f"{story_id}.{level_id}: missing coveredStoryBeatIds")
            else:
                covered_set = set(covered)
                if len(covered) != len(covered_set):
                    errors.append(f"{story_id}.{level_id}: duplicate covered story beat IDs")
                unknown_ids = covered_set - beat_ids
                missing_ids = required_ids - covered_set
                if unknown_ids:
                    errors.append(
                        f"{story_id}.{level_id}: unknown covered story beat IDs: {', '.join(sorted(unknown_ids))}"
                    )
                if missing_ids:
                    errors.append(
                        f"{story_id}.{level_id}: missing required story beat IDs: {', '.join(sorted(missing_ids))}"
                    )
    return errors


def _duplicate_findings(
    new_stories: list[dict[str, Any]],
    existing: dict[str, Any] | None,
    recent_stories: list[dict[str, Any]] | None = None,
) -> tuple[list[str], set[int]]:
    errors: list[str] = []
    old_stories = [
        *(existing["stories"] if existing else []),
        *(recent_stories or []),
    ]
    all_previous = list(old_stories)
    seen_slugs = {
        str(story.get("slug") or story.get("id"))
        for story in old_stories
        if story.get("slug") or story.get("id")
    }
    seen_urls = {
        normalized_url(url)
        for story in old_stories
        for url in [
            *[
                source.get("url")
                for source in story.get("sources", [])
                if isinstance(source, dict)
            ],
            *story.get("sourceUrls", []),
        ]
        if isinstance(url, str)
    }
    seen_scenarios = {
        str(scenario)
        for story in old_stories
        for scenario in [
            story.get("scenario"),
            story.get("everydayMeta", {}).get("scenario")
            if isinstance(story.get("everydayMeta"), dict)
            else None,
        ]
        if scenario
    }
    duplicate_indexes: set[int] = set()
    for index, story in enumerate(new_stories):
        story_is_duplicate = False
        if story["slug"] in seen_slugs:
            errors.append(f"duplicate slug: {story['slug']}")
            story_is_duplicate = True
        else:
            similar_slug = next(
                (slug for slug in seen_slugs if slugs_are_near_duplicates(story["slug"], slug)),
                None,
            )
            if similar_slug:
                errors.append(f"near-duplicate story slugs: {story['slug']} and {similar_slug}")
                story_is_duplicate = True
        for source in story["sources"]:
            source_url = normalized_url(source["url"])
            if source_url in seen_urls:
                errors.append(f"duplicate source URL: {source['url']}")
                story_is_duplicate = True
        meta = story.get("everydayMeta")
        scenario = meta.get("scenario") if isinstance(meta, dict) else None
        if scenario and scenario in seen_scenarios:
            errors.append(f"duplicate generated scenario: {scenario}")
            story_is_duplicate = True
        for previous in all_previous:
            previous_brief = previous.get("brief")
            if isinstance(previous_brief, str) and briefs_are_near_duplicates(story["brief"], previous_brief):
                previous_slug = previous.get("slug") or previous.get("id") or "previous story"
                errors.append(f"near-duplicate story briefs: {story['slug']} and {previous_slug}")
                story_is_duplicate = True
                break
        if story_is_duplicate:
            duplicate_indexes.add(index)
            continue
        all_previous.append(story)
        seen_slugs.add(story["slug"])
        seen_urls.update(normalized_url(source["url"]) for source in story["sources"])
        if scenario:
            seen_scenarios.add(str(scenario))
    return errors, duplicate_indexes


def _duplicate_errors(
    new_stories: list[dict[str, Any]],
    existing: dict[str, Any] | None,
    recent_stories: list[dict[str, Any]] | None = None,
) -> list[str]:
    errors, _ = _duplicate_findings(new_stories, existing, recent_stories)
    return errors


def _seed_errors(
    seeds: list[dict[str, Any]],
    target_date: str,
    level_ids: list[str],
    locales: list[str],
    site: dict[str, Any],
    levels: list[dict[str, Any]],
    existing: dict[str, Any] | None,
    minimum_count: int,
    maximum_count: int,
    recent_stories: list[dict[str, Any]] | None = None,
    allowed_story_types: set[str] | None = None,
) -> list[str]:
    """Validate frozen discovery or planning metadata before language adaptation."""
    seed_issue = {
        "schemaVersion": 1,
        "date": target_date,
        "availableLevels": level_ids,
        "translationLocales": locales,
        "stories": [{**story, "levels": {}} for story in seeds],
    }
    errors = [
        error
        for error in validate_issue(seed_issue, site, levels, "planning batch")
        if ".levels" not in error
    ]
    story_ids = [story.get("id", "") for story in seeds]
    if len(set(story_ids)) != len(story_ids):
        errors.append("planning phase returned duplicate story IDs")
    if not minimum_count <= len(seeds) <= maximum_count:
        errors.append(f"expected {minimum_count}–{maximum_count} planned stories, got {len(seeds)}")
    if allowed_story_types is not None:
        invalid_types = sorted({
            str(story.get("type"))
            for story in seeds
            if isinstance(story, dict) and story.get("type") not in allowed_story_types
        })
        if invalid_types:
            errors.append(
                "story types must be "
                + " or ".join(sorted(story_type.upper() for story_type in allowed_story_types))
                + "; received "
                + ", ".join(invalid_types)
            )
    if existing is not None:
        invalid_append_types = sorted({
            str(story.get("type"))
            for story in seeds
            if isinstance(story, dict) and story.get("type") not in {"everyday", "dialog"}
        })
        if invalid_append_types:
            errors.append(
                "append stories must be EVERYDAY or DIALOG; received "
                + ", ".join(invalid_append_types)
            )
    if all(isinstance(story, dict) and isinstance(story.get("sources"), list) and isinstance(story.get("brief"), str) for story in seeds):
        errors.extend(_duplicate_errors(seeds, existing, recent_stories))
    return errors


def _build_index(
    content_dir: Path,
    candidate: dict[str, Any],
    site: dict[str, Any],
    levels: list[dict[str, Any]],
) -> dict[str, Any]:
    issues: dict[str, dict[str, Any]] = {}
    for path in content_dir.glob("????-??-??.json"):
        if path.stem != candidate["date"]:
            issues[path.stem] = read_json(path)
    issues[candidate["date"]] = candidate
    dates = []
    for issue_date in sorted(issues, reverse=True):
        issue = issues[issue_date]
        preferred_level = site["defaultReadingLevel"]
        level_id = preferred_level if preferred_level in issue["availableLevels"] else issue["availableLevels"][0]
        dates.append(
            {
                "date": issue_date,
                "storyCount": len(issue["stories"]),
                "readingMinutes": issue_minutes(issue, level_id, levels),
            }
        )
    return {"schemaVersion": 1, "dates": dates}


def _updated_history(history: dict[str, Any], stories: list[dict[str, Any]], target_date: str) -> dict[str, Any]:
    items = list(history.get("items", []))
    for story in stories:
        if story["type"] not in {"everyday", "dialog"}:
            continue
        meta = story["everydayMeta"]
        items.append(
            {
                "date": target_date,
                "storyId": story["id"],
                "domain": meta["domain"],
                "scenario": meta["scenario"],
                "lexicalThemes": meta["lexicalThemes"],
                "targetVocabulary": meta["targetVocabulary"],
            }
        )
    return {"schemaVersion": 1, "items": items}


def _generated_story_target(target_count: int, sourced_count: int, appending: bool) -> int:
    if appending:
        return target_count
    return min(
        max(0, target_count - sourced_count),
        EVERYDAY_TARGET + DIALOG_TARGET,
    )


def _transactional_write(payloads: dict[Path, dict[str, Any]]) -> None:
    staged: dict[Path, Path] = {}
    backups: dict[Path, Path | None] = {}
    promoted: list[Path] = []
    try:
        for path, payload in payloads.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                staged[path] = Path(handle.name)
            if path.exists():
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as backup:
                    backup_path = Path(backup.name)
                backups[path] = backup_path
                shutil.copy2(path, backup_path)
            else:
                backups[path] = None
        for path, staged_path in staged.items():
            os.replace(staged_path, path)
            promoted.append(path)
        staged.clear()
    except Exception:
        for path in reversed(promoted):
            backup = backups[path]
            if backup is None:
                path.unlink(missing_ok=True)
            else:
                os.replace(backup, path)
                backups[path] = None
        raise
    finally:
        for temporary in [*staged.values(), *(item for item in backups.values() if item is not None)]:
            temporary.unlink(missing_ok=True)


def generate(root: Path, target_date: str, additional_stories: int) -> dict[str, Any] | None:
    target = date.fromisoformat(target_date)
    site = load_site_config(root)
    configured_levels = load_level_config(root)
    content_dir = root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    issue_path = content_dir / f"{target_date}.json"
    existing = read_json(issue_path) if issue_path.exists() else None
    history_path = content_dir / "everyday-history.json"
    history = read_json(history_path) if history_path.exists() else {"schemaVersion": 1, "items": []}
    if existing:
        existing_errors = validate_issue(existing, site, configured_levels, issue_path.name)
        if existing_errors:
            raise RuntimeError("Existing issue is invalid; refusing to append:\n- " + _error_report(existing_errors))

    level_ids = existing["availableLevels"] if existing else [item["id"] for item in configured_levels]
    levels = [item for item in configured_levels if item["id"] in level_ids]
    locales = list(existing["translationLocales"] if existing else site["translationLocales"])

    target_count = additional_stories if existing else int(site["defaultIssueStoryCount"])
    minimum_count = additional_stories if existing else int(site["minimumIssueStoryCount"])
    maximum_count = additional_stories if existing else int(site["maximumIssueStoryCount"])
    exclusions = _existing_exclusions(existing)
    recent = _recent_history(history, target, int(site["everydayHistoryDays"]))
    recent_issues = _recent_issue_context(
        content_dir,
        target,
        int(site["recentIssueContextDays"]),
    )
    recent_story_records = [
        story
        for issue in recent_issues
        for story in issue.get("stories", [])
    ]
    recent_sourced_records = [
        story for story in recent_story_records if story.get("type") in {"current", "history"}
    ]
    recent_generated_records = [
        story for story in recent_story_records if story.get("type") in {"everyday", "dialog"}
    ]
    sourced_instructions = _read_prompts(root, ("editorial.md",))
    duplicate_review_instructions = _read_prompts(root, ("deduplication.md",))
    history_research_instructions = _read_prompts(root, ("history-research.md",))
    generated_instructions = _read_prompts(root, ("everyday.md", "dialog.md"))
    adaptation_instructions = _read_prompts(root, ("adaptation.md",))
    image_locales = list(dict.fromkeys([*site["interfaceLocales"], *locales]))
    mode = "append" if existing else "new issue"
    _log(
        f"Preparing {target_date} ({mode}); target {target_count} stories, "
        f"allowed range {minimum_count}-{maximum_count}"
    )
    sourced_seeds: list[dict[str, Any]] = []
    sourced_reserves: list[dict[str, Any]] = []
    if existing is None:
        sourced_target = min(target_count, CURRENT_TARGET + HISTORY_TARGET)
        current_target = min(CURRENT_TARGET, sourced_target)
        history_target = min(HISTORY_TARGET, sourced_target - current_target)
        sourced_feedback: list[str] | None = None
        forbidden_sourced = _forbidden_story_records(
            exclusions,
            recent_issues,
            {"current", "history"},
        )
        for attempt in range(SOURCED_DISCOVERY_ATTEMPTS):
            worldwide_fallback = attempt == SOURCED_DISCOVERY_ATTEMPTS - 1
            expected_history_sources = (
                {WORLDWIDE_HISTORY_SOURCE}
                if worldwide_fallback
                else set(ISRAELI_HISTORY_SOURCE_MINIMUMS)
            )
            current_remaining = max(
                0,
                current_target - sum(story.get("type") == "current" for story in sourced_seeds),
            )
            history_remaining = max(
                0,
                history_target - sum(story.get("type") == "history" for story in sourced_seeds),
            )
            request_target = current_remaining + history_remaining
            if request_target == 0:
                break
            requested_types = [
                story_type
                for story_type, remaining in (
                    ("current", current_remaining),
                    ("history", history_remaining),
                )
                if remaining
            ]
            reviewed_sourced = [*sourced_seeds, *sourced_reserves]
            attempt_number = attempt + 1
            phase = f"Sourced discovery attempt {attempt_number}/{SOURCED_DISCOVERY_ATTEMPTS}"
            try:
                seed_batch = _call_openai(
                    os.environ["OPENAI_MODEL"],
                    sourced_instructions,
                    _sourced_discovery_request(
                        target_date,
                        current_remaining,
                        history_remaining,
                        forbidden_sourced,
                        [_compact_story_record(story) for story in reviewed_sourced],
                        sourced_feedback,
                        worldwide_fallback,
                    ),
                    _sourced_candidate_batch_schema(
                        requested_types,
                        sorted(expected_history_sources),
                    ),
                    use_web_search=True,
                    phase=phase,
                )
            except RuntimeError:
                sourced_feedback = ["The previous sourced-discovery request failed; retry the search for all remaining slots."]
                _log(f"{phase}: request failed; continuing sourced discovery")
                continue
            unverified_urls = seed_batch.pop(PROVENANCE_ERRORS_KEY, [])
            returned_candidates = seed_batch.get("stories", [])
            returned_seeds = [
                _sourced_candidate_to_seed(candidate, target_date)
                for candidate in returned_candidates
                if isinstance(candidate, dict)
            ]
            removed_sources, removed_images = _remove_redundant_sources(
                returned_seeds,
                {"stories": reviewed_sourced} if reviewed_sourced else None,
                unverified_urls,
            )
            if removed_sources or removed_images:
                _log(
                    f"{phase}: removed {removed_sources} unusable source(s) and "
                    f"{removed_images} dependent image(s)"
                )
            if not returned_seeds:
                sourced_feedback = ["No candidates were returned; continue searching for the requested sourced stories."]
                _log(f"{phase}: returned no candidates; continuing sourced discovery")
                continue
            validation_context = [*recent_sourced_records, *reviewed_sourced]
            candidate_batch: list[dict[str, Any]] = []
            candidate_errors: list[str] = []
            candidate_validation_context = list(validation_context)
            for candidate in returned_seeds:
                errors = _seed_errors(
                    [candidate],
                    target_date,
                    level_ids,
                    locales,
                    site,
                    levels,
                    None,
                    0,
                    1,
                    candidate_validation_context,
                    {"current", "history"},
                )
                if errors:
                    candidate_errors.extend(
                        f"candidate {candidate.get('id')}: {error}"
                        for error in errors
                    )
                    continue
                candidate_batch.append(candidate)
                candidate_validation_context.append(candidate)

            mix_errors = _sourced_candidate_mix_errors(
                returned_seeds,
                requested_types,
                expected_history_sources,
            )
            attempt_feedback = list(dict.fromkeys([*mix_errors, *candidate_errors]))
            if candidate_errors:
                _log_validation_errors(phase, candidate_errors)
            if mix_errors:
                unique_mix_errors = list(dict.fromkeys(mix_errors))
                _log(
                    f"{phase}: candidate pool has {len(unique_mix_errors)} non-blocking mix issue(s); "
                    "valid candidates will continue"
                )
                for error in unique_mix_errors[:20]:
                    _log(f"  - {error}")
            if candidate_errors:
                _log(
                    f"{phase}: retained {len(candidate_batch)} individually valid sourced candidate(s) "
                    f"after discarding {len(returned_seeds) - len(candidate_batch)} invalid candidate(s)"
                )
            if not candidate_batch:
                sourced_feedback = attempt_feedback or [
                    "No individually valid candidates were returned; continue searching for the requested sourced stories."
                ]
                continue

            if candidate_batch:
                review_phase = f"{phase} duplicate review"
                try:
                    duplicate_review = _call_openai(
                        os.environ["OPENAI_MODEL"],
                        duplicate_review_instructions,
                        _sourced_duplicate_review_request(
                            forbidden_sourced,
                            [_compact_story_record(story) for story in reviewed_sourced],
                            candidate_batch,
                        ),
                        _duplicate_review_schema([story["id"] for story in candidate_batch]),
                        use_web_search=False,
                        phase=review_phase,
                    )
                    reviewed_duplicate_indexes, reviewed_findings = _duplicate_review_findings(
                        duplicate_review,
                        candidate_batch,
                    )
                except (KeyError, TypeError, RuntimeError):
                    sourced_feedback = list(dict.fromkeys([
                        *attempt_feedback,
                        "The strict duplicate review failed, so none of the unreviewed candidates were retained. "
                        "Continue searching for all remaining sourced slots.",
                    ]))[:20]
                    _log(f"{review_phase}: failed closed; discarded {len(candidate_batch)} unreviewed candidate(s)")
                    continue
                if reviewed_duplicate_indexes:
                    candidate_batch = [
                        story
                        for index, story in enumerate(candidate_batch)
                        if index not in reviewed_duplicate_indexes
                    ]
                    attempt_feedback = [
                        *attempt_feedback,
                        *reviewed_findings[:19],
                        "Continue web search for genuinely unrelated replacements.",
                    ]
                    _log(
                        f"{review_phase}: rejected {len(reviewed_duplicate_indexes)} semantic duplicate(s); "
                        f"retained {len(candidate_batch)} candidate(s)"
                    )
                else:
                    _log(f"{review_phase}: all {len(candidate_batch)} candidate(s) are semantically unique")

            before_count = len(sourced_seeds)
            additions = _select_sourced_candidates(
                sourced_seeds,
                candidate_batch,
                current_target,
                history_target,
            )
            sourced_seeds.extend(additions)
            selected_ids = {story["id"] for story in additions}
            known_reserve_ids = {story["id"] for story in sourced_reserves}
            sourced_reserves.extend(
                story
                for story in candidate_batch
                if story["id"] not in selected_ids and story["id"] not in known_reserve_ids
            )
            _log(
                f"{phase}: selected {len(sourced_seeds) - before_count} candidate(s); "
                f"{len(sourced_seeds)} sourced story brief(s) retained"
            )
            sourced_feedback = list(dict.fromkeys(attempt_feedback))[:20] or None
            if len(sourced_seeds) < sourced_target and sourced_feedback is None:
                sourced_feedback = [
                    "The current pass returned fewer usable sourced stories than requested; "
                    "continue with fresh candidates for the remaining CURRENT or HISTORY slots."
                ]

        pending_history = [story for story in sourced_seeds if story.get("type") == "history"]
        research_feedback: list[str] | None = None
        consecutive_failed_research_requests = 0
        research_round = 0
        while pending_history:
            research_round += 1
            phase = f"HISTORY research round {research_round}"
            requested_ids = [story["id"] for story in pending_history]
            try:
                research_batch = _call_openai(
                    os.environ["OPENAI_MODEL"],
                    history_research_instructions,
                    _history_research_request(target_date, pending_history, research_feedback),
                    _history_research_batch_schema(requested_ids),
                    use_web_search=True,
                    phase=phase,
                )
            except RuntimeError:
                consecutive_failed_research_requests += 1
                research_feedback = ["The previous HISTORY research request failed; retry every unresolved subject."]
                _log(f"{phase}: request failed")
                if consecutive_failed_research_requests >= HISTORY_RESEARCH_REQUEST_FAILURE_LIMIT:
                    raise RuntimeError(
                        "HISTORY research failed twice consecutively; refusing to discard researched-story slots"
                    )
                continue
            consecutive_failed_research_requests = 0

            unverified_urls = research_batch.pop(PROVENANCE_ERRORS_KEY, [])
            research_records = [
                record
                for record in research_batch.get("stories", [])
                if isinstance(record, dict)
            ]
            removed_sources, _ = _remove_redundant_sources(research_records, None, unverified_urls)
            if removed_sources:
                _log(f"{phase}: removed {removed_sources} unusable research source(s)")
            valid_packs, unresolved_ids, research_errors = _validated_history_research(
                research_records,
                requested_ids,
            )
            if research_errors:
                _log_validation_errors(phase, research_errors)

            pending_by_id = {story["id"]: story for story in pending_history}
            for story_id, pack in valid_packs.items():
                story = pending_by_id[story_id]
                contract = copy.deepcopy(pack["storyBeats"])
                story["sources"] = copy.deepcopy(pack["sources"])
                story["storyBeats"] = [beat["text"] for beat in contract]
                story[HISTORY_BEAT_CONTRACT_KEY] = contract
            _log(
                f"{phase}: retained {len(valid_packs)} researched HISTORY pack(s); "
                f"{len(unresolved_ids)} unresolved"
            )

            unresolved_stories = [pending_by_id[story_id] for story_id in unresolved_ids]
            next_pending: list[dict[str, Any]] = []
            for unresolved_story in unresolved_stories:
                unresolved_id = unresolved_story["id"]
                story_index = next(
                    index for index, story in enumerate(sourced_seeds) if story.get("id") == unresolved_id
                )
                replacement = _pop_history_reserve(
                    sourced_reserves,
                    unresolved_story.get("historyFamily"),
                )
                if replacement is not None:
                    sourced_seeds[story_index] = replacement
                    next_pending.append(replacement)
                    continue
                sourced_seeds.pop(story_index)
            pending_history = next_pending
            research_feedback = list(dict.fromkeys(research_errors))[:20] or None

    generated_target = _generated_story_target(
        target_count,
        len(sourced_seeds),
        existing is not None,
    )
    generated_seeds: list[dict[str, Any]] = []
    generated_feedback: list[str] | None = None
    forbidden_generated = _forbidden_story_records(
        exclusions,
        recent_issues,
        {"everyday", "dialog"},
    )
    for attempt in range(GENERATED_PLANNING_ATTEMPTS):
        request_target = generated_target - len(generated_seeds)
        if request_target <= 0:
            break
        attempt_number = attempt + 1
        phase = f"Generated planning attempt {attempt_number}/{GENERATED_PLANNING_ATTEMPTS}"
        everyday_remaining = 0 if existing else max(
            0,
            EVERYDAY_TARGET - sum(story.get("type") == "everyday" for story in generated_seeds),
        )
        dialog_remaining = 0 if existing else max(
            0,
            DIALOG_TARGET - sum(story.get("type") == "dialog" for story in generated_seeds),
        )
        requested_everyday = min(everyday_remaining, request_target)
        requested_dialog = min(dialog_remaining, request_target - requested_everyday)
        if requested_dialog < dialog_remaining:
            requested_dialog = min(dialog_remaining, request_target)
            requested_everyday = min(everyday_remaining, request_target - requested_dialog)
        try:
            returned_batch = _call_openai(
                os.environ["OPENAI_MODEL"],
                generated_instructions,
                _generated_planning_request(
                    target_date,
                    request_target,
                    requested_everyday,
                    requested_dialog,
                    existing is not None,
                    forbidden_generated,
                    recent,
                    [_compact_story_record(story) for story in [*sourced_seeds, *generated_seeds]],
                    generated_feedback,
                ),
                _seed_batch_schema(
                    0,
                    request_target,
                    levels,
                    locales,
                    image_locales,
                    ["everyday", "dialog"],
                ),
                use_web_search=False,
                phase=phase,
            ).get("stories", [])
        except RuntimeError:
            generated_feedback = ["The previous generated-planning request failed; retry all remaining slots."]
            _log(f"{phase}: request failed; retrying the remaining slots")
            continue
        if not returned_batch:
            generated_feedback = ["No scenarios were returned; generate fresh unrelated scenarios for the remaining slots."]
            _log(f"{phase}: returned no scenarios; retrying the remaining slots")
            continue
        validation_context = [*recent_generated_records, *recent, *sourced_seeds, *generated_seeds]
        generated_errors = _seed_errors(
            returned_batch,
            target_date,
            level_ids,
            locales,
            site,
            levels,
            existing,
            0,
            request_target,
            validation_context,
            {"everyday", "dialog"},
        )
        candidate_batch = returned_batch
        if generated_errors:
            _log_validation_errors(phase, generated_errors)
            duplicate_errors, duplicate_indexes = _duplicate_findings(
                returned_batch,
                existing,
                validation_context,
            )
            duplicate_only = bool(duplicate_indexes) and all(
                "duplicate" in error.lower()
                for error in generated_errors
            )
            if not duplicate_only:
                generated_feedback = list(dict.fromkeys(generated_errors))[:20]
                continue
            candidate_batch = [
                story
                for index, story in enumerate(returned_batch)
                if index not in duplicate_indexes
            ]
            generated_feedback = [
                *list(dict.fromkeys(duplicate_errors))[:19],
                f"Generate up to {request_target - len(candidate_batch)} unrelated replacements for rejected scenarios.",
            ]
            _log(
                f"{phase}: kept {len(candidate_batch)} unique scenario(s); "
                f"retrying {len(duplicate_indexes)} rejected slot(s)"
            )
        else:
            generated_feedback = None
        generated_seeds.extend(candidate_batch)
        _log(
            f"{phase}: {len(generated_seeds)} of {generated_target} generated story brief(s) retained"
        )

    seeds = [
        {
            key: value
            for key, value in story.items()
            if key not in {"historyFamily", DISCOVERY_SOURCE_KEY}
        }
        for story in [*sourced_seeds, *generated_seeds]
    ]
    if not seeds:
        raise RuntimeError("Planning produced no usable story briefs")
    if len(seeds) < target_count:
        _log(
            f"Planning retained {len(seeds)} unique stories, below the target of {target_count}; "
            "continuing without a strict count failure"
        )
    else:
        _log(f"Planning completed with {len(seeds)} frozen story briefs")

    new_stories: list[dict[str, Any]] = []
    if ADAPTATION_BATCH_SIZE != 1:
        raise RuntimeError("Adaptation validation isolation requires one story per batch")
    adaptation_batches = [
        seeds[index:index + ADAPTATION_BATCH_SIZE]
        for index in range(0, len(seeds), ADAPTATION_BATCH_SIZE)
    ]
    for batch_index, batch_seeds in enumerate(adaptation_batches, start=1):
        story_ids = [story.get("id", "") for story in batch_seeds]
        adaptation_schema = _adaptation_batch_schema(batch_seeds, levels, locales, image_locales)
        adaptation_feedback: list[str] | None = None
        completed_batch: list[dict[str, Any]] | None = None
        for attempt in range(ADAPTATION_ATTEMPTS):
            attempt_number = attempt + 1
            phase = (
                f"Adaptation batch {batch_index}/{len(adaptation_batches)}, "
                f"attempt {attempt_number}/{ADAPTATION_ATTEMPTS}"
            )
            try:
                adaptation_batch = _call_openai(
                    os.environ["OPENAI_MODEL"],
                    adaptation_instructions,
                    _adaptation_request(batch_seeds, levels, locales, adaptation_feedback),
                    adaptation_schema,
                    use_web_search=False,
                    phase=phase,
                )
            except RuntimeError:
                if attempt == ADAPTATION_ATTEMPTS - 1:
                    raise
                _log(f"{phase}: request failed; retrying only this batch")
                continue

            adaptations = adaptation_batch.get("adaptations", [])
            removed_units = _remove_empty_lexical_units(adaptations)
            if removed_units:
                _log(f"{phase}: removed {removed_units} empty lexical unit(s)")
            adaptation_ids = [item.get("id") for item in adaptations]
            adaptation_map = {item.get("id"): item.get("levels", {}) for item in adaptations}
            candidate_stories = [
                {**_public_story_seed(story), "levels": adaptation_map.get(story.get("id"), {})}
                for story in batch_seeds
            ]
            candidate_issue = {
                "schemaVersion": 1,
                "date": target_date,
                "generatedAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
                "availableLevels": level_ids,
                "translationLocales": locales,
                "stories": candidate_stories,
            }
            _log(f"{phase}: validating {len(candidate_stories)} adapted stories")
            candidate_errors = validate_issue(candidate_issue, site, levels, "generated batch")
            candidate_errors.extend(_history_adaptation_errors(batch_seeds, adaptations, levels))
            if len(set(adaptation_ids)) != len(adaptation_ids) or set(adaptation_ids) != set(story_ids):
                candidate_errors.append("adaptation phase must return every frozen story ID exactly once")
            if not candidate_errors:
                completed_batch = candidate_stories
                _log(f"{phase}: validation passed")
                break
            adaptation_feedback = candidate_errors[:20]
            _log_validation_errors(phase, candidate_errors)

        if completed_batch is None:
            _log(
                f"Adaptation batch {batch_index}/{len(adaptation_batches)} failed article validation after "
                f"{ADAPTATION_ATTEMPTS} attempts; omitting story {', '.join(story_ids)}"
            )
            continue
        new_stories.extend(completed_batch)

    if not new_stories:
        if existing is not None:
            _log("No appended articles passed adaptation validation; leaving the existing issue unchanged")
            return existing
        _log("No articles passed adaptation validation; no issue file was created")
        return None

    combined = list(existing["stories"]) + new_stories if existing else new_stories
    issue = {
        "schemaVersion": 1,
        "date": target_date,
        "generatedAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "availableLevels": level_ids,
        "translationLocales": locales,
        "stories": combined,
    }
    errors = validate_issue(issue, site, configured_levels, issue_path.name)
    if errors:
        raise RuntimeError("Combined issue failed validation:\n- " + _error_report(errors))
    _log(f"Combined issue validation passed with {len(issue['stories'])} total stories")

    next_history = _updated_history(history, new_stories, target_date)
    next_index = _build_index(content_dir, issue, site, configured_levels)
    _log("Writing issue, index, and generated-scenario history transactionally")
    _transactional_write(
        {
            issue_path: issue,
            history_path: next_history,
            content_dir / "index.json": next_index,
        }
    )
    _log("Content files updated successfully")
    return issue


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or append a daily Hebrew issue.")
    parser.add_argument("--date", default="", help="Publication date (YYYY-MM-DD); defaults to current UTC date.")
    parser.add_argument("--additional-stories", type=int, default=None, help="Stories to append when the date already exists.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    target_date = args.date or datetime.now(UTC).date().isoformat()
    site = load_site_config(args.root.resolve())
    additional = args.additional_stories or int(site["defaultAppendStoryCount"])
    if not 1 <= additional <= 10:
        parser.error("--additional-stories must be between 1 and 10")
    if not os.environ.get("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY is required")
    if not os.environ.get("OPENAI_MODEL"):
        parser.error("OPENAI_MODEL is required")
    issue = generate(args.root.resolve(), target_date, additional)
    if issue is None:
        print(f"No valid articles remained for {target_date}; no issue was created.")
        return 0
    print(f"Prepared {issue['date']} with {len(issue['stories'])} stories using {os.environ['OPENAI_MODEL']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
