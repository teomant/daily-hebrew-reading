from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from unicodedata import category as unicode_category
from urllib.parse import urlparse

from .common import issue_minutes, normalized_url, read_json, units_text


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STORY_TYPES = {"current", "everyday", "dialog", "history"}
UNIT_TYPES = {"word", "expression", "properNoun", "separator"}
MIN_TRANSLATION_COVERAGE = 0.75
BRIEF_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "been", "but", "by",
    "can", "could", "for", "from", "has", "have", "how", "in", "into", "is", "it",
    "its", "may", "more", "new", "not", "of", "on", "or", "other", "out", "so",
    "some", "than", "that", "the", "their", "them", "then", "there", "they", "this",
    "to", "too", "up", "was", "were", "what", "when", "where", "which", "while",
    "who", "why", "will", "with", "would",
}


def briefs_are_near_duplicates(first: str, second: str) -> bool:
    """Detect the same story when a generated brief has been lightly rewritten."""
    normalized_first = " ".join(re.findall(r"\w+", first.casefold()))
    normalized_second = " ".join(re.findall(r"\w+", second.casefold()))
    if SequenceMatcher(None, normalized_first, normalized_second).ratio() >= 0.82:
        return True

    first_tokens = {
        token for token in normalized_first.split()
        if len(token) > 2 and token not in BRIEF_STOP_WORDS
    }
    second_tokens = {
        token for token in normalized_second.split()
        if len(token) > 2 and token not in BRIEF_STOP_WORDS
    }
    if not first_tokens or not second_tokens:
        return False
    shared = first_tokens & second_tokens
    overlap = len(shared) / min(len(first_tokens), len(second_tokens))
    jaccard = len(shared) / len(first_tokens | second_tokens)
    return len(shared) >= 8 and overlap >= 0.70 and jaccard >= 0.45


def _https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if any(character.isspace() or unicode_category(character).startswith("C") for character in value):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _validate_units(
    units: Any,
    path: str,
    locales: list[str],
    errors: list[str],
) -> None:
    if not isinstance(units, list) or not units:
        errors.append(f"{path}: expected a non-empty lexical-unit list")
        return
    for index, unit in enumerate(units):
        unit_path = f"{path}[{index}]"
        if not isinstance(unit, dict):
            errors.append(f"{unit_path}: expected an object")
            continue
        text = unit.get("text")
        unit_type = unit.get("type")
        translations = unit.get("translations")
        if not isinstance(text, str) or not text:
            errors.append(f"{unit_path}.text: expected a non-empty string")
        if unit_type not in UNIT_TYPES:
            errors.append(f"{unit_path}.type: unsupported lexical-unit type")
        if not isinstance(translations, dict):
            errors.append(f"{unit_path}.translations: expected an object")
            continue
        missing = set(locales) - set(translations)
        if missing:
            errors.append(f"{unit_path}.translations: missing {sorted(missing)}")
        for locale in locales:
            translation = translations.get(locale)
            if not isinstance(translation, str):
                errors.append(f"{unit_path}.translations.{locale}: expected a string")


def _validate_translation_coverage(
    level: dict[str, Any],
    path: str,
    locales: list[str],
    errors: list[str],
) -> None:
    paragraphs = level.get("paragraphs")
    groups = [level.get("title"), level.get("teaser")]
    if isinstance(paragraphs, list):
        groups.extend(paragraphs)
    meaningful = [
        unit
        for units in groups
        if isinstance(units, list)
        for unit in units
        if isinstance(unit, dict) and unit.get("type") != "separator"
    ]
    if not meaningful:
        return
    for locale in locales:
        translated = sum(
            1
            for unit in meaningful
            if isinstance(unit.get("translations"), dict)
            and isinstance(unit["translations"].get(locale), str)
            and bool(unit["translations"][locale].strip())
        )
        coverage = translated / len(meaningful)
        if coverage < MIN_TRANSLATION_COVERAGE:
            errors.append(
                f"{path}.translations.{locale}: {coverage:.0%} coverage; "
                f"expected at least {MIN_TRANSLATION_COVERAGE:.0%}"
            )


def validate_issue(
    issue: Any,
    site: dict[str, Any],
    configured_levels: list[dict[str, Any]],
    label: str = "issue",
) -> list[str]:
    errors: list[str] = []
    if not isinstance(issue, dict):
        return [f"{label}: expected an object"]
    if issue.get("schemaVersion") != 1:
        errors.append(f"{label}.schemaVersion: expected 1")
    date = issue.get("date")
    if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        errors.append(f"{label}.date: expected YYYY-MM-DD")

    known_levels = {item["id"] for item in configured_levels}
    level_ids = issue.get("availableLevels")
    if not isinstance(level_ids, list) or not level_ids:
        errors.append(f"{label}.availableLevels: expected a non-empty list")
        level_ids = []
    elif len(level_ids) != len(set(level_ids)) or not set(level_ids).issubset(known_levels):
        errors.append(f"{label}.availableLevels: contains duplicates or unknown IDs")

    locales = issue.get("translationLocales")
    known_locales = set(site["translationLocales"])
    if not isinstance(locales, list) or not locales:
        errors.append(f"{label}.translationLocales: expected a non-empty list")
        locales = []
    elif len(locales) != len(set(locales)) or not set(locales).issubset(known_locales):
        errors.append(f"{label}.translationLocales: contains duplicates or unknown locales")

    stories = issue.get("stories")
    if not isinstance(stories, list) or not stories:
        errors.append(f"{label}.stories: expected at least one story")
        return errors

    seen_slugs: set[str] = set()
    seen_source_urls: set[str] = set()
    seen_briefs: list[tuple[int, str, str]] = []
    for story_index, story in enumerate(stories):
        story_path = f"{label}.stories[{story_index}]"
        if not isinstance(story, dict):
            errors.append(f"{story_path}: expected an object")
            continue
        slug = story.get("slug")
        story_id = story.get("id")
        if not isinstance(slug, str) or not SLUG_PATTERN.fullmatch(slug):
            errors.append(f"{story_path}.slug: expected lowercase ASCII kebab-case")
        elif slug in seen_slugs:
            errors.append(f"{story_path}.slug: duplicate {slug}")
        else:
            seen_slugs.add(slug)
        if story_id != slug:
            errors.append(f"{story_path}.id: must equal slug")

        story_type = story.get("type")
        if story_type not in STORY_TYPES:
            errors.append(f"{story_path}.type: unsupported story type")
        if not isinstance(story.get("category"), str) or not story["category"]:
            errors.append(f"{story_path}.category: expected a stable category key")
        brief = story.get("brief")
        if not isinstance(brief, str) or not brief.strip():
            errors.append(f"{story_path}.brief: expected a non-empty brief")
        else:
            for previous_index, previous_brief, previous_slug in seen_briefs:
                if briefs_are_near_duplicates(brief, previous_brief):
                    errors.append(
                        f"{story_path}.brief: near-duplicate story topic of "
                        f"{label}.stories[{previous_index}] ({previous_slug})"
                    )
                    break
            seen_briefs.append((story_index, brief, str(slug)))

        sources = story.get("sources")
        if not isinstance(sources, list):
            errors.append(f"{story_path}.sources: expected a list")
            sources = []
        if story_type in {"everyday", "dialog"} and sources:
            errors.append(f"{story_path}.sources: {story_type.upper()} stories cannot have sources")
        source_urls: set[str] = set()
        for source_index, source in enumerate(sources):
            source_path = f"{story_path}.sources[{source_index}]"
            if not isinstance(source, dict):
                errors.append(f"{source_path}: expected an object")
                continue
            for field in ("publisher", "title"):
                if not isinstance(source.get(field), str) or not source[field].strip():
                    errors.append(f"{source_path}.{field}: expected a non-empty string")
            url = source.get("url")
            if not _https_url(url):
                errors.append(f"{source_path}.url: expected a valid HTTPS URL")
            else:
                source_url = normalized_url(url)
                if source_url in source_urls or source_url in seen_source_urls:
                    errors.append(f"{source_path}.url: duplicate source URL")
                else:
                    source_urls.add(source_url)
                    seen_source_urls.add(source_url)

        meta = story.get("everydayMeta")
        if story_type in {"everyday", "dialog"}:
            if not isinstance(meta, dict):
                errors.append(f"{story_path}.everydayMeta: {story_type.upper()} scenario metadata is required")
            else:
                for field in ("domain", "scenario"):
                    if not isinstance(meta.get(field), str) or not meta[field].strip():
                        errors.append(f"{story_path}.everydayMeta.{field}: required")
                for field in ("lexicalThemes", "targetVocabulary"):
                    if not isinstance(meta.get(field), list) or not meta[field]:
                        errors.append(f"{story_path}.everydayMeta.{field}: expected a non-empty list")
        elif meta is not None:
            errors.append(f"{story_path}.everydayMeta: only EVERYDAY and DIALOG stories may have metadata")

        image = story.get("image")
        if image is not None:
            if story_type in {"everyday", "dialog"}:
                errors.append(f"{story_path}.image: {story_type.upper()} stories cannot use sourced images")
            elif not isinstance(image, dict):
                errors.append(f"{story_path}.image: expected an object or null")
            else:
                if not _https_url(image.get("url")):
                    errors.append(f"{story_path}.image.url: expected a valid HTTPS URL")
                image_source_url = image.get("sourceUrl")
                if not _https_url(image_source_url):
                    errors.append(f"{story_path}.image.sourceUrl: expected a valid HTTPS URL")
                elif normalized_url(image_source_url) not in source_urls:
                    errors.append(f"{story_path}.image.sourceUrl: must match a story source")
                if not isinstance(image.get("credit"), str) or not image["credit"].strip():
                    errors.append(f"{story_path}.image.credit: required")
                if not _https_url(image.get("rightsUrl")):
                    errors.append(f"{story_path}.image.rightsUrl: expected a valid HTTPS URL")
                if not isinstance(image.get("rightsLabel"), str) or not image["rightsLabel"].strip():
                    errors.append(f"{story_path}.image.rightsLabel: required")
                alt = image.get("alt")
                if not isinstance(alt, dict):
                    errors.append(f"{story_path}.image.alt: expected an object")
                else:
                    for locale in locales:
                        if not isinstance(alt.get(locale), str) or not alt[locale].strip():
                            errors.append(f"{story_path}.image.alt.{locale}: required")

        story_levels = story.get("levels")
        if not isinstance(story_levels, dict):
            errors.append(f"{story_path}.levels: expected an object")
            continue
        if set(story_levels) != set(level_ids):
            errors.append(f"{story_path}.levels: must exactly match availableLevels")
        for level_id in level_ids:
            level = story_levels.get(level_id)
            level_path = f"{story_path}.levels.{level_id}"
            if not isinstance(level, dict):
                errors.append(f"{level_path}: expected an object")
                continue
            _validate_units(level.get("title"), f"{level_path}.title", locales, errors)
            _validate_units(level.get("teaser"), f"{level_path}.teaser", locales, errors)
            paragraphs = level.get("paragraphs")
            if not isinstance(paragraphs, list) or not paragraphs:
                errors.append(f"{level_path}.paragraphs: expected a non-empty list")
            else:
                for paragraph_index, paragraph in enumerate(paragraphs):
                    _validate_units(paragraph, f"{level_path}.paragraphs[{paragraph_index}]", locales, errors)
                if not any(units_text(paragraph).strip() for paragraph in paragraphs if isinstance(paragraph, list)):
                    errors.append(f"{level_path}.paragraphs: text is empty")
            _validate_translation_coverage(level, level_path, locales, errors)
    return errors


def validate_repository(root: Path) -> list[str]:
    from .common import load_level_config, load_site_config

    site = load_site_config(root)
    levels = load_level_config(root)
    content_dir = root / "content"
    errors: list[str] = []
    issue_files = sorted(content_dir.glob("????-??-??.json"))
    if not issue_files:
        return ["content: no daily issue files found"]

    issues: dict[str, dict[str, Any]] = {}
    for issue_file in issue_files:
        try:
            issue = read_json(issue_file)
        except Exception as exc:  # JSON parser supplies precise details.
            errors.append(f"{issue_file.name}: invalid JSON ({exc})")
            continue
        issues[issue_file.stem] = issue
        errors.extend(validate_issue(issue, site, levels, issue_file.name))
        if issue.get("date") != issue_file.stem:
            errors.append(f"{issue_file.name}.date: must match filename")

    try:
        index = read_json(content_dir / "index.json")
    except Exception as exc:
        errors.append(f"index.json: invalid or missing ({exc})")
    else:
        dates = index.get("dates") if isinstance(index, dict) else None
        if not isinstance(dates, list):
            errors.append("index.json.dates: expected a list")
        else:
            indexed_dates = [item.get("date") for item in dates if isinstance(item, dict)]
            expected_dates = sorted(issues, reverse=True)
            if indexed_dates != expected_dates:
                errors.append("index.json.dates: must list every issue newest first")
            for item in dates:
                if not isinstance(item, dict) or item.get("date") not in issues:
                    continue
                if item.get("storyCount") != len(issues[item["date"]]["stories"]):
                    errors.append(f"index.json: storyCount mismatch for {item['date']}")
                if not isinstance(item.get("readingMinutes"), int) or item["readingMinutes"] < 1:
                    errors.append(f"index.json: readingMinutes must be positive for {item['date']}")
                else:
                    issue = issues[item["date"]]
                    preferred = site["defaultReadingLevel"]
                    level_id = preferred if preferred in issue["availableLevels"] else issue["availableLevels"][0]
                    expected_minutes = issue_minutes(issue, level_id, levels)
                    if item["readingMinutes"] != expected_minutes:
                        errors.append(f"index.json: readingMinutes mismatch for {item['date']}")

    try:
        history = read_json(content_dir / "everyday-history.json")
    except Exception as exc:
        errors.append(f"everyday-history.json: invalid or missing ({exc})")
    else:
        items = history.get("items") if isinstance(history, dict) else None
        if not isinstance(items, list):
            errors.append("everyday-history.json.items: expected a list")
        else:
            history_ids = {
                (item.get("date"), item.get("storyId"))
                for item in items
                if isinstance(item, dict)
            }
            for issue in issues.values():
                for story in issue.get("stories", []):
                    history_key = (issue.get("date"), story.get("id"))
                    if story.get("type") in {"everyday", "dialog"} and history_key not in history_ids:
                        errors.append(f"everyday-history.json: missing {story.get('id')}")
    return errors
