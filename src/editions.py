"""Versioned storage and single-edition views for reading and generation."""
from __future__ import annotations

import copy
import json
import re
from typing import Any

from .common import issue_minutes


def edition_route(level_id: str) -> str:
    return re.sub(r"(?<!^)([A-Z])", r"-\1", level_id).lower()


def to_editions(issue: dict[str, Any]) -> dict[str, Any]:
    """Split legacy adaptations without changing any lexical units or metadata."""
    if issue.get("schemaVersion") == 2:
        return copy.deepcopy(issue)
    if issue.get("schemaVersion") != 1:
        raise ValueError("Unsupported issue schema version")
    result = {key: copy.deepcopy(value) for key, value in issue.items() if key != "stories"}
    result["schemaVersion"] = 2
    result["editions"] = {}
    for level_id in issue["availableLevels"]:
        articles = []
        for story in issue["stories"]:
            original = story.get("_editionStories", {}).get(level_id, story)
            content = original.get("levels", {}).get(level_id)
            if content is None:
                continue
            article = {key: copy.deepcopy(value) for key, value in original.items()
                       if key != "levels" and not key.startswith("_")}
            article["topicId"] = story.get("topicId", story["id"])
            article["content"] = copy.deepcopy(content)
            articles.append(article)
        if articles:
            result["editions"][level_id] = {"stories": articles}
    result["availableLevels"] = list(result["editions"])
    return result


def edition_issue(issue: dict[str, Any], level_id: str) -> dict[str, Any]:
    """Project one edition into the existing lexical validation/rendering contract."""
    if issue.get("schemaVersion") == 1:
        stories = [{**{key: value for key, value in story.items() if key != "levels"},
                    "levels": {level_id: story["levels"][level_id]}}
                   for story in issue["stories"] if level_id in story.get("levels", {})]
    else:
        stories = [{**{key: value for key, value in article.items() if key != "content"},
                    "levels": {level_id: article["content"]}}
                   for article in issue["editions"].get(level_id, {}).get("stories", [])]
    return {**{key: value for key, value in issue.items() if key not in {"editions", "stories"}},
            "schemaVersion": 1, "availableLevels": [level_id], "stories": stories}


def topic_records(issue: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return distinct topic/scenario metadata, without loading Hebrew into prompts."""
    if not issue:
        return []
    if issue.get("schemaVersion") != 2:
        return issue.get("stories", [])
    records = []
    seen = set()
    for edition in issue["editions"].values():
        for article in edition["stories"]:
            key = (article["topicId"], article["brief"],
                   json.dumps(article.get("everydayMeta"), sort_keys=True, ensure_ascii=False),
                   json.dumps(article.get("shortItems"), sort_keys=True, ensure_ascii=False))
            if key not in seen:
                seen.add(key)
                records.append({key: value for key, value in article.items() if key != "content"})
    return records


def build_index(issues: dict[str, dict[str, Any]], levels: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schemaVersion": 2, "dates": [
        {"date": day, "editions": {
            level_id: {"storyCount": len(view["stories"]),
                       "readingMinutes": issue_minutes(view, level_id, levels)}
            for level_id in issue["availableLevels"]
            for view in [edition_issue(issue, level_id)]
        }}
        for day, issue in sorted(issues.items(), reverse=True)
    ]}


def edition_index(index: dict[str, Any], level_id: str) -> dict[str, Any]:
    return {"schemaVersion": 1, "dates": [
        {"date": item["date"], **item["editions"][level_id]}
        for item in index["dates"] if level_id in item.get("editions", {})
    ]}
