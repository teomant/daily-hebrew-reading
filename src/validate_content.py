from __future__ import annotations

import argparse
from pathlib import Path

from .common import ROOT
from .validation import validate_repository


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate all magazine content.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = validate_repository(args.root.resolve())
    if errors:
        print("Content validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Content validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
