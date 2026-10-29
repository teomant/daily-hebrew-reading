from __future__ import annotations

import copy
import re
from datetime import date
from pathlib import Path
from typing import Any

from .common import read_json, units_text


VERB_BATCH_SIZE = 10
VERB_BATCH_COUNT = 5
VERB_EPOCH = date(1, 1, 1)


def verb_batch_index(target_date: str) -> int:
    return (date.fromisoformat(target_date) - VERB_EPOCH).days % VERB_BATCH_COUNT


def load_verbs(root: Path) -> list[dict[str, Any]]:
    verbs = read_json(root / "config" / "common-verbs.json")["verbs"]
    if not isinstance(verbs, list) or len(verbs) != VERB_BATCH_SIZE * VERB_BATCH_COUNT:
        raise ValueError("common-verbs.json must contain exactly 50 verbs")
    seen = set()
    for rank, item in enumerate(verbs, 1):
        if (not isinstance(item, dict) or item.get("rank") != rank
                or not isinstance(item.get("verb"), str)
                or not re.fullmatch(r"[א-ת]+", item["verb"])
                or not isinstance(item.get("meaning"), str) or not item["meaning"].strip()
                or item["verb"] in seen):
            raise ValueError(f"common-verbs.json has an invalid or duplicate entry at rank {rank}")
        seen.add(item["verb"])
    return verbs


def daily_verbs(root: Path, target_date: str) -> list[dict[str, Any]]:
    start = verb_batch_index(target_date) * VERB_BATCH_SIZE
    return load_verbs(root)[start:start + VERB_BATCH_SIZE]


def uses_target_verb(paragraph: list[dict[str, Any]], verb: str) -> bool:
    # Ignore vowel/cantillation marks, but never accept a substring of another word.
    text = re.sub(r"[\u0591-\u05bd\u05bf\u05c1\u05c2\u05c4\u05c5\u05c7]", "", units_text(paragraph))
    return verb in re.findall(r"[א-ת]+", text)


def verb_seed(item: dict[str, Any], target_date: str) -> dict[str, Any]:
    story_id = f"verb-{item['rank']}-{target_date}"
    return {
        "id": story_id, "slug": story_id, "type": "everyday", "category": "everyday",
        "brief": (
            f"Create a fresh fictional everyday mini-situation for {target_date} centered on "
            f"the Hebrew verb {item['verb']} ({item['meaning']}). "
            "Invent one concrete action and its immediate result in two or three sentences. "
            "Use the assigned spelling naturally in the body, not as a heading or vocabulary list."
        ),
        "everydayMeta": {
            "domain": "verb_practice", "scenario": story_id,
            "lexicalThemes": [item["meaning"]], "targetVocabulary": [item["verb"]],
            "dialogSpeakers": [],
        },
        "sources": [], "image": None, "_shortItem": True, "_targetVerb": item["verb"],
    }


def verbs_page(
    items: list[dict[str, Any]], stories: list[dict[str, Any]], target_date: str,
    level_ids: list[str], locales: list[str],
) -> dict[str, Any] | None:
    if len(items) != VERB_BATCH_SIZE or len(stories) != VERB_BATCH_SIZE:
        return None

    def units(words: list[tuple[str, str, str]]) -> list[dict[str, Any]]:
        return [{"text": he, "type": "word",
                 "translations": {locale: ru if locale == "ru" else en for locale in locales}}
                for he, en, ru in words]

    page_id = f"common-verbs-{target_date}"
    return {
        "id": page_id, "slug": page_id, "type": "verbs", "category": "everyday",
        "brief": "Ten fictional mini-stories practicing today's batch from the fifty common Hebrew verbs.",
        "everydayMeta": None, "sources": [], "image": None,
        "verbItems": copy.deepcopy(items),
        "levels": {
            level_id: {
                "title": units([("50", "50", "50"), ("פעלים", "verbs", "глаголов"),
                                ("נפוצים", "common", "распространённых")]),
                "teaser": units([("עשרה", "ten", "десять"), ("פעלים", "verbs", "глаголов"),
                                 ("בסיפורים", "in stories", "в историях"),
                                 ("קצרים", "short", "коротких")])
                          + [{"text": ".", "type": "separator", "translations": {locale: "" for locale in locales}}],
                "paragraphs": [story["levels"][level_id]["paragraphs"][0] for story in stories],
            } for level_id in level_ids
        },
    }
