"""Keep existing lexical/planning fixtures readable after the storage migration.

New edition integration tests use the public schema directly.
These views let the older tests continue to exercise their original contracts.
"""
from src.common import read_json
from src.generate_issue import generate


def legacy_view(value):
    if not isinstance(value, dict) or value.get("schemaVersion") != 2:
        return value
    if "dates" in value:
        return {"schemaVersion": 1, "dates": [
            {"date": item["date"], **next(iter(item["editions"].values()))}
            for item in value["dates"]]}
    stories = {}
    for level_id, edition in value["editions"].items():
        for article in edition["stories"]:
            story = stories.setdefault(article["topicId"], {
                **{key: item for key, item in article.items() if key not in {"topicId", "content"}},
                "levels": {},
            })
            story["levels"][level_id] = article["content"]
    return {**{key: item for key, item in value.items() if key != "editions"},
            "schemaVersion": 1, "stories": list(stories.values())}


def read_legacy_view(path):
    return legacy_view(read_json(path))


def generate_legacy_view(*args, **kwargs):
    return legacy_view(generate(*args, **kwargs))
