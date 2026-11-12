"""Offline, lossless migration from shared adaptations to separate editions."""
from __future__ import annotations

import argparse
from pathlib import Path

from .common import ROOT, load_level_config, load_site_config, read_json
from .editions import build_index, to_editions
from .generate_issue import _transactional_write
from .validation import validate_issue, validate_repository


def migrate(root: Path, *, write: bool = False) -> dict[str, int]:
    errors = validate_repository(root)
    if errors:
        raise ValueError("Cannot migrate invalid content:\n" + "\n".join(errors))
    site, levels = load_site_config(root), load_level_config(root)
    issues, changes = {}, {}
    article_count = 0
    for path in sorted((root / "content").glob("????-??-??.json")):
        original = read_json(path)
        issue = to_editions(original)
        errors = validate_issue(issue, site, levels, path.name)
        if errors:
            raise ValueError("Invalid migrated issue:\n" + "\n".join(errors))
        issues[issue["date"]] = issue
        article_count += sum(len(edition["stories"]) for edition in issue["editions"].values())
        if original != issue:
            changes[path] = issue
    issue_changes = len(changes)
    index_path = root / "content" / "index.json"
    index = build_index(issues, levels)
    if read_json(index_path) != index:
        changes[index_path] = index
    if write and changes:
        _transactional_write(changes)
    return {"issues": len(issues), "articles": article_count,
            "changedIssues": issue_changes, "changedFiles": len(changes)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true", help="Apply migration; otherwise only validate and report.")
    args = parser.parse_args()
    result = migrate(args.root.resolve(), write=args.write)
    print(f"{'Applied' if args.write else 'Dry run'}: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
