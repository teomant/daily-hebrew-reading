from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import tempfile
from datetime import UTC, date, datetime, timedelta
from difflib import SequenceMatcher
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
from .validation import validate_issue


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
RESEARCH_ATTEMPTS = 3
ADAPTATION_ATTEMPTS = 2
ADAPTATION_BATCH_SIZE = 2


def _log(message: str) -> None:
    timestamp = datetime.now(UTC).strftime("%H:%M:%S UTC")
    print(f"[{timestamp}] {_safe_log_text(message)}", flush=True)


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
                "maxItems": 5,
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
            "type": {"type": "string", "enum": ["current", "everyday", "history"]},
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
) -> dict[str, Any]:
    schema = copy.deepcopy(_story_batch_schema(minimum_count, maximum_count, levels, locales, image_locales))
    story = schema["properties"]["stories"]["items"]
    story["properties"].pop("levels")
    story["required"].remove("levels")
    return schema


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


def _read_prompts(root: Path) -> str:
    parts = []
    for name in ("editorial.md", "everyday.md", "adaptation.md"):
        parts.append((root / "prompts" / name).read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def _recent_history(history: dict[str, Any], target: date, days: int) -> list[dict[str, Any]]:
    cutoff = target - timedelta(days=days)
    recent = []
    for item in history.get("items", []):
        try:
            item_date = date.fromisoformat(item["date"])
        except (KeyError, TypeError, ValueError):
            continue
        if cutoff <= item_date <= target:
            recent.append(item)
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
                    "category": story.get("category"),
                    "brief": story.get("brief"),
                }
            )
        issues.append({"date": issue_date.isoformat(), "stories": stories})
    return issues


def _existing_exclusions(issue: dict[str, Any] | None) -> dict[str, Any]:
    if not issue:
        return {"slugs": [], "sourceUrls": [], "briefs": [], "types": {}}
    type_counts: dict[str, int] = {}
    for story in issue["stories"]:
        type_counts[story["type"]] = type_counts.get(story["type"], 0) + 1
    return {
        "slugs": [story["slug"] for story in issue["stories"]],
        "sourceUrls": [normalized_url(source["url"]) for story in issue["stories"] for source in story["sources"]],
        "briefs": [story["brief"] for story in issue["stories"]],
        "types": type_counts,
    }


def _generation_request(
    target_date: str,
    target_count: int,
    minimum_count: int,
    maximum_count: int,
    is_append: bool,
    levels: list[dict[str, Any]],
    locales: list[str],
    exclusions: dict[str, Any],
    recent_history: list[dict[str, Any]],
    recent_issues: list[dict[str, Any]],
    feedback: list[str] | None = None,
) -> str:
    mode = (
        "This issue already exists. Produce only new stories to append. Preserve the existing issue outside this response. "
        "The complete issue after appending must contain 3–5 EVERYDAY stories. Balance the existing type counts; normally do not add a second HISTORY story."
        if is_append
        else
        "Create the first complete issue for this date. Aim for 4 CURRENT stories, 4 EVERYDAY stories, and 2 HISTORY stories; "
        "allow 3–5 CURRENT, 3–5 EVERYDAY, and 1–2 HISTORY when quality requires it. Favor practical spoken-life value over a rigid quota."
    )
    level_payload = [
        {
            "id": item["id"],
            "targetWords": item["targetWords"],
            "minimumWords": item["minimumWords"],
            "maximumWords": item["maximumWords"],
            "guidance": item["guidance"],
        }
        for item in levels
    ]
    retry = f"\nPrevious attempt failed validation. Correct these problems: {json.dumps(feedback, ensure_ascii=False)}" if feedback else ""
    return f"""
Target publication date: {target_date}
Story count: aim for {target_count}; return between {minimum_count} and {maximum_count}. Never add a weak or padded story only to reach the target.
Mode: {mode}

Use web search for every CURRENT and HISTORY story. Prefer Israeli local and regional sources, then broader Israeli sources; use international stories only when their everyday-language value is stronger. Prefer sources published today or within the previous several days for CURRENT. Verify facts before adapting. Give every brief enough concrete situation, interaction, and outcome detail to support 4–5 developed paragraphs at the configured article lengths without invention. Never reuse any excluded story, URL, or substantially similar topic.

Configured reading levels:
{json.dumps(level_payload, ensure_ascii=False, indent=2)}

Required translation locales: {json.dumps(locales)}

Existing issue exclusions and type counts:
{json.dumps(exclusions, ensure_ascii=False, indent=2)}

Recent EVERYDAY history to avoid:
{json.dumps(recent_history, ensure_ascii=False, indent=2)}

Content from the previous {len(recent_issues)} available issue(s):
{json.dumps(recent_issues, ensure_ascii=False, indent=2)}

Do not repeat the same real event, historical subject, or everyday scenario from these previous issues. A genuine follow-up is allowed only when something materially changed and the new angle is clearly distinct.

The story id and slug must be identical. Prefer distinct canonical content-page URLs for sourced stories; use an empty source list rather than an uncertain URL. Do not use publisher homepages, section pages, generic latest pages, or liveblogs. Use null everydayMeta for sourced stories. Use null image when image provenance or embedding suitability is uncertain. Every separator unit must still contain translations with empty strings for every locale. Return no prose outside the schema.{retry}
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


def _normalized(value: str) -> str:
    return " ".join(re.findall(r"\w+", value.casefold()))


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


def _missing_translation_errors(stories: list[dict[str, Any]], locales: list[str]) -> list[str]:
    errors: list[str] = []
    for story_index, story in enumerate(stories):
        for level_id, level in story.get("levels", {}).items():
            groups = [("title", level.get("title")), ("teaser", level.get("teaser"))]
            groups.extend(
                (f"paragraphs[{index}]", paragraph)
                for index, paragraph in enumerate(level.get("paragraphs", []))
            )
            for group_name, units in groups:
                if not isinstance(units, list):
                    continue
                for unit_index, unit in enumerate(units):
                    if not isinstance(unit, dict) or unit.get("type") == "separator":
                        continue
                    translations = unit.get("translations")
                    if not isinstance(translations, dict):
                        continue
                    for locale in locales:
                        value = translations.get(locale)
                        if isinstance(value, str) and not value.strip():
                            errors.append(
                                f"generated batch.stories[{story_index}].levels.{level_id}."
                                f"{group_name}[{unit_index}].translations.{locale}: translation is required"
                            )
    return errors


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
This is the adaptation phase. The story metadata and briefs below are frozen results of a completed research phase.
Create title, teaser, paragraphs, lexical segmentation, and translations for every listed story and level. Do not change, extend, or infer beyond a brief. Do not add facts to reach a word target. Return each story ID exactly once and no other IDs.

Configured reading levels:
{json.dumps(level_payload, ensure_ascii=False, indent=2)}

Required translation locales: {json.dumps(locales)}

Frozen story briefs and metadata:
{json.dumps(seeds, ensure_ascii=False, indent=2)}
{retry}
""".strip()


def _duplicate_errors(new_stories: list[dict[str, Any]], existing: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    old_stories = existing["stories"] if existing else []
    all_previous = list(old_stories)
    existing_slugs = {story["slug"] for story in old_stories}
    existing_urls = {normalized_url(source["url"]) for story in old_stories for source in story["sources"]}
    for story in new_stories:
        if story["slug"] in existing_slugs:
            errors.append(f"duplicate slug: {story['slug']}")
        for source in story["sources"]:
            source_url = normalized_url(source["url"])
            if source_url in existing_urls:
                errors.append(f"duplicate source URL: {source['url']}")
        normalized_brief = _normalized(story["brief"])
        for previous in all_previous:
            score = SequenceMatcher(None, normalized_brief, _normalized(previous["brief"])).ratio()
            if score >= 0.82:
                errors.append(f"near-duplicate story briefs: {story['slug']} and {previous['slug']}")
                break
        all_previous.append(story)
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
) -> list[str]:
    """Validate frozen research metadata before paying for language adaptation."""
    seed_issue = {
        "schemaVersion": 1,
        "date": target_date,
        "availableLevels": level_ids,
        "translationLocales": locales,
        "stories": [{**story, "levels": {}} for story in seeds],
    }
    errors = [
        error
        for error in validate_issue(seed_issue, site, levels, "research batch")
        if ".levels" not in error
    ]
    story_ids = [story.get("id", "") for story in seeds]
    if len(set(story_ids)) != len(story_ids):
        errors.append("research phase returned duplicate story IDs")
    if not minimum_count <= len(seeds) <= maximum_count:
        errors.append(f"expected {minimum_count}–{maximum_count} research stories, got {len(seeds)}")
    existing_everyday = sum(
        story.get("type") == "everyday"
        for story in (existing.get("stories", []) if existing else [])
        if isinstance(story, dict)
    )
    generated_everyday = sum(
        story.get("type") == "everyday"
        for story in seeds
        if isinstance(story, dict)
    )
    total_everyday = existing_everyday + generated_everyday
    enforce_everyday_mix = existing is None or len(existing.get("stories", [])) >= int(site["minimumIssueStoryCount"])
    if enforce_everyday_mix and not 3 <= total_everyday <= 5:
        errors.append(
            "issue requires 3–5 EVERYDAY (fully AI-generated) stories; "
            f"existing {existing_everyday} + generated {generated_everyday} = {total_everyday}"
        )
    if all(isinstance(story, dict) and isinstance(story.get("sources"), list) and isinstance(story.get("brief"), str) for story in seeds):
        errors.extend(_duplicate_errors(seeds, existing))
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
        if story["type"] != "everyday":
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
    instructions = _read_prompts(root)
    image_locales = list(dict.fromkeys([*site["interfaceLocales"], *locales]))
    seed_schema = _seed_batch_schema(minimum_count, maximum_count, levels, locales, image_locales)
    mode = "append" if existing else "new issue"
    _log(
        f"Preparing {target_date} ({mode}); target {target_count} stories, "
        f"allowed range {minimum_count}-{maximum_count}"
    )
    research_feedback: list[str] | None = None
    seeds: list[dict[str, Any]] | None = None

    for attempt in range(RESEARCH_ATTEMPTS):
        attempt_number = attempt + 1
        research_request = _generation_request(
            target_date,
            target_count,
            minimum_count,
            maximum_count,
            existing is not None,
            levels,
            locales,
            exclusions,
            recent,
            recent_issues,
            research_feedback,
        )
        research_request += "\n\nThis is the research and planning phase. Return only sourced/scenario metadata and concise frozen briefs; do not write level adaptations yet."
        seed_batch = _call_openai(
            os.environ["OPENAI_MODEL"],
            instructions,
            research_request,
            seed_schema,
            phase=f"Research attempt {attempt_number}/{RESEARCH_ATTEMPTS}",
        )
        unverified_urls = seed_batch.pop(PROVENANCE_ERRORS_KEY, [])
        candidate_seeds = seed_batch.get("stories", [])
        removed_sources, removed_images = _remove_redundant_sources(
            candidate_seeds,
            existing,
            unverified_urls,
        )
        if removed_sources or removed_images:
            _log(
                f"Research attempt {attempt_number}/{RESEARCH_ATTEMPTS}: removed "
                f"{removed_sources} unusable source(s) and {removed_images} dependent image(s)"
            )
        _log(
            f"Research attempt {attempt_number}/{RESEARCH_ATTEMPTS}: "
            f"validating {len(candidate_seeds)} story briefs"
        )
        research_errors = _seed_errors(
            candidate_seeds,
            target_date,
            level_ids,
            locales,
            site,
            levels,
            existing,
            minimum_count,
            maximum_count,
        )
        if research_errors:
            research_feedback = list(dict.fromkeys(research_errors))[:20]
            _log_validation_errors(
                f"Research attempt {attempt_number}/{RESEARCH_ATTEMPTS}",
                research_errors,
            )
            if attempt == RESEARCH_ATTEMPTS - 1:
                raise RuntimeError("Generated research failed validation:\n- " + _error_report(research_errors))
            continue
        seeds = candidate_seeds
        _log(
            f"Research attempt {attempt_number}/{RESEARCH_ATTEMPTS}: "
            "validation passed; briefs are frozen"
        )
        break

    if seeds is None:
        raise RuntimeError("Research produced no usable story briefs")

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
                    instructions,
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
            translation_errors = _missing_translation_errors(candidate_stories, locales)
            candidate_errors.extend(translation_errors)
            if len(set(adaptation_ids)) != len(adaptation_ids) or set(adaptation_ids) != set(story_ids):
                candidate_errors.append("adaptation phase must return every frozen story ID exactly once")
            if not candidate_errors:
                completed_batch = candidate_stories
                _log(f"{phase}: validation passed")
                break
            blocking_errors = [error for error in candidate_errors if error not in translation_errors]
            if attempt == ADAPTATION_ATTEMPTS - 1 and translation_errors and not blocking_errors:
                completed_batch = candidate_stories
                _log(
                    f"{phase}: accepted with {len(translation_errors)} untranslated value(s); "
                    "their tooltips will be skipped"
                )
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
    _log("Writing issue, index, and EVERYDAY history transactionally")
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
