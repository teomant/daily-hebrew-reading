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
from .validation import briefs_are_near_duplicates, slugs_are_near_duplicates, validate_issue


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
SOURCED_DISCOVERY_ATTEMPTS = 2
SOURCED_CANDIDATE_COUNT = 28
CURRENT_CANDIDATE_TARGET = 12
HISTORY_CANDIDATE_TARGET = 16
GENERATED_PLANNING_ATTEMPTS = 3
ADAPTATION_ATTEMPTS = 2
ADAPTATION_BATCH_SIZE = 2
CURRENT_TARGET = 4
HISTORY_TARGET = 4
EVERYDAY_TARGET = 2
DIALOG_TARGET = 2


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


def _sourced_candidate_batch_schema(story_types: list[str]) -> dict[str, Any]:
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
    candidate = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"},
            "type": {"type": "string", "enum": story_types},
            "category": {"type": "string", "enum": CATEGORIES},
            "brief": {"type": "string"},
            "sources": {"type": "array", "items": source, "minItems": 1},
        },
        "required": ["id", "type", "category", "brief", "sources"],
        "additionalProperties": False,
    }
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


def _sourced_candidate_to_seed(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": candidate.get("id"),
        "slug": candidate.get("id"),
        "type": candidate.get("type"),
        "category": candidate.get("category"),
        "brief": candidate.get("brief"),
        "everydayMeta": None,
        "sources": candidate.get("sources"),
        "image": None,
    }


def _adaptation_batch_schema(
    story_ids: list[str],
    levels: list[dict[str, Any]],
    locales: list[str],
    image_locales: list[str],
) -> dict[str, Any]:
    full = _story_batch_schema(1, 1, levels, locales, image_locales)
    level_map = full["properties"]["stories"]["items"]["properties"]["levels"]
    adaptation = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "enum": story_ids},
            "levels": level_map,
        },
        "required": ["id", "levels"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "adaptations": {
                "type": "array",
                "items": adaptation,
                "minItems": len(story_ids),
                "maxItems": len(story_ids),
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
    retry_scope = (
        "\nRETRY WORLDWIDE REPLACEMENT SEARCH\nThis is not another Israel-first pass. Start new searches across "
        f"the world for the remaining CURRENT and HISTORY slots. At least 21 of the {SOURCED_CANDIDATE_COUNT} candidates should come from "
        "outside Israel and should span at least six countries or regions. Search both international outlets and useful "
        "local sources. Do not re-query, rename, translate, update, or find alternate coverage for any rejected or forbidden "
        "story. For CURRENT, use practical events from the target date or previous several days. For HISTORY, use short, "
        "concrete, relatable subjects from any period; no date connection is required. Israeli candidates remain allowed "
        "only when they are genuinely new. Keep every editorial, source-quality, safety, and novelty rule."
        if feedback else ""
    )
    retry = (
        "\nRETRY FEEDBACK\nThe previous attempt left sourced slots unfilled. Do not return any rejected "
        f"candidates again. Correct these problems while continuing the search: {json.dumps(feedback, ensure_ascii=False)}"
        if feedback else ""
    )
    return f"""
Target publication date: {target_date}
The issue still needs up to {current_count} CURRENT and up to {history_count} HISTORY stories. Return exactly {SOURCED_CANDIDATE_COUNT} distinct screening candidates even though fewer final slots remain. These are candidates for later deduplication and selection, not final stories. {candidate_mix}
{retry_scope}{retry}

SEARCH PROCESS
- Use web search and begin from the target date and permitted editorial areas, never from the forbidden records.
- For CURRENT, search Israeli reporting from the target date and previous several days. Search across the whole country and varied communities; do not default to Jerusalem or treat it as the center of every issue.
- For HISTORY, first look for date-related Israeli facts when worthwhile, then search for unrelated short, interesting facts from anywhere in Israel. HISTORY does not need a connection to the target date or current news.
- Build a deliberately varied HISTORY pool. Include at least four candidates from each of these groups: (1) real past events with a clear sequence and consequence, (2) notable people such as artists, writers, scientists, educators, engineers, athletes, founders, guides, and community figures, and (3) the stories of Israeli nature sites, national parks, gardens, trails, viewpoints, museums, landmarks, unusual local attractions, and tourist destinations. Use the remaining HISTORY candidates for the strongest varied subjects.
- Among the first four HISTORY candidates in the returned batch, cover at least three of those preferred groups. At most one of those first four, and at most two HISTORY candidates in the full batch, may have an archaeological excavation, ancient street, building layer, pottery find, or construction-site dig as the main hook. Archaeology is a fallback, not the default meaning of HISTORY.
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
Return exactly {SOURCED_CANDIDATE_COUNT} records containing only `id`, `type`, `category`, `brief`, and `sources`. Write every `brief` in English with enough source-supported detail both to identify the underlying story during deduplication and to sustain a developed 4–5-paragraph adaptation without invented facts or filler. Give every candidate at least one distinct canonical HTTPS content-page source; never use homepages, section pages, search pages, generic latest pages, or liveblogs. Do not return Hebrew, level adaptations, scenario metadata, images, or prose outside the schema.
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
            if not isinstance(source, dict) or not isinstance(source.get("url"), str):
                locally_unique.append(source)
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
This is the adaptation phase. The story metadata and briefs below are frozen results of completed sourced discovery and generated-scenario planning.
Create title, teaser, paragraphs, lexical segmentation, and translations for every listed story and level. Develop each body toward its configured targetWords and perform the prompt's one pre-segmentation length revision when needed. Do not change, extend, or infer beyond a brief, and do not add facts or filler to reach a word target. A result that remains below minimumWords is still usable and must not cause the request or generation run to fail. Return each story ID exactly once and no other IDs.

Configured reading levels:
{json.dumps(level_payload, ensure_ascii=False, indent=2)}

Required translation locales: {json.dumps(locales)}

Frozen story briefs and metadata:
{json.dumps(seeds, ensure_ascii=False, indent=2)}
{retry}
""".strip()


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


def generate(root: Path, target_date: str, additional_stories: int) -> dict[str, Any]:
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
    generated_instructions = _read_prompts(root, ("everyday.md", "dialog.md"))
    adaptation_instructions = _read_prompts(root, ("adaptation.md",))
    image_locales = list(dict.fromkeys([*site["interfaceLocales"], *locales]))
    mode = "append" if existing else "new issue"
    _log(
        f"Preparing {target_date} ({mode}); target {target_count} stories, "
        f"allowed range {minimum_count}-{maximum_count}"
    )
    sourced_seeds: list[dict[str, Any]] = []
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
                        [_compact_story_record(story) for story in sourced_seeds],
                        sourced_feedback,
                    ),
                    _sourced_candidate_batch_schema(requested_types),
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
                _sourced_candidate_to_seed(candidate)
                for candidate in returned_candidates
                if isinstance(candidate, dict)
            ]
            removed_sources, removed_images = _remove_redundant_sources(
                returned_seeds,
                {"stories": sourced_seeds} if sourced_seeds else None,
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
            validation_context = [*recent_sourced_records, *sourced_seeds]
            sourced_errors = _seed_errors(
                returned_seeds,
                target_date,
                level_ids,
                locales,
                site,
                levels,
                None,
                0,
                SOURCED_CANDIDATE_COUNT,
                validation_context,
                {"current", "history"},
            )
            candidate_batch = returned_seeds
            if sourced_errors:
                _log_validation_errors(phase, sourced_errors)
                duplicate_errors, duplicate_indexes = _duplicate_findings(
                    returned_seeds,
                    None,
                    validation_context,
                )
                duplicate_only = bool(duplicate_indexes) and all(
                    "duplicate" in error.lower()
                    for error in sourced_errors
                )
                if not duplicate_only:
                    sourced_feedback = list(dict.fromkeys(sourced_errors))[:20]
                    continue
                candidate_batch = [
                    story
                    for index, story in enumerate(returned_seeds)
                    if index not in duplicate_indexes
                ]
                sourced_feedback = [
                    *list(dict.fromkeys(duplicate_errors))[:19],
                    "Continue web search for unrelated replacements; do not switch to generated stories.",
                ]
                _log(
                    f"{phase}: kept {len(candidate_batch)} unique sourced candidate(s); "
                    f"continuing web search for {len(duplicate_indexes)} replacement(s)"
                )
            else:
                sourced_feedback = None

            if candidate_batch:
                review_phase = f"{phase} duplicate review"
                try:
                    duplicate_review = _call_openai(
                        os.environ["OPENAI_MODEL"],
                        duplicate_review_instructions,
                        _sourced_duplicate_review_request(
                            forbidden_sourced,
                            [_compact_story_record(story) for story in sourced_seeds],
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
                    sourced_feedback = [
                        "The strict duplicate review failed, so none of the unreviewed candidates were retained. "
                        "Continue searching for all remaining sourced slots."
                    ]
                    _log(f"{review_phase}: failed closed; discarded {len(candidate_batch)} unreviewed candidate(s)")
                    continue
                if reviewed_duplicate_indexes:
                    candidate_batch = [
                        story
                        for index, story in enumerate(candidate_batch)
                        if index not in reviewed_duplicate_indexes
                    ]
                    sourced_feedback = [
                        *(sourced_feedback or []),
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
            for story in candidate_batch:
                story_type = story.get("type")
                if story_type == "current":
                    if sum(item.get("type") == "current" for item in sourced_seeds) < current_target:
                        sourced_seeds.append(story)
                elif story_type == "history":
                    if sum(item.get("type") == "history" for item in sourced_seeds) < history_target:
                        sourced_seeds.append(story)
            _log(
                f"{phase}: selected {len(sourced_seeds) - before_count} candidate(s); "
                f"{len(sourced_seeds)} sourced story brief(s) retained"
            )
            if len(sourced_seeds) < sourced_target and sourced_feedback is None:
                sourced_feedback = [
                    "The Israel-focused pass returned fewer usable sourced stories than requested; "
                    "search worldwide for the remaining CURRENT or HISTORY slots."
                ]

    generated_target = target_count - len(sourced_seeds) if existing is None else target_count
    generated_target = max(0, generated_target)
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

    seeds = [*sourced_seeds, *generated_seeds]
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
    adaptation_batches = [
        seeds[index:index + ADAPTATION_BATCH_SIZE]
        for index in range(0, len(seeds), ADAPTATION_BATCH_SIZE)
    ]
    for batch_index, batch_seeds in enumerate(adaptation_batches, start=1):
        story_ids = [story.get("id", "") for story in batch_seeds]
        adaptation_schema = _adaptation_batch_schema(story_ids, levels, locales, image_locales)
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
                {**story, "levels": adaptation_map.get(story.get("id"), {})}
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
            if len(set(adaptation_ids)) != len(adaptation_ids) or set(adaptation_ids) != set(story_ids):
                candidate_errors.append("adaptation phase must return every frozen story ID exactly once")
            if not candidate_errors:
                completed_batch = candidate_stories
                _log(f"{phase}: validation passed")
                break
            adaptation_feedback = candidate_errors[:20]
            _log_validation_errors(phase, candidate_errors)
            if attempt == ADAPTATION_ATTEMPTS - 1:
                raise RuntimeError("Generated content failed validation:\n- " + _error_report(candidate_errors))

        if completed_batch is None:
            raise RuntimeError(f"Adaptation batch {batch_index} produced no usable stories")
        new_stories.extend(completed_batch)

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
    print(f"Prepared {issue['date']} with {len(issue['stories'])} stories using {os.environ['OPENAI_MODEL']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
