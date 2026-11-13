"""Bounded web research and explicit recovery of completed generation work."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date
from pathlib import Path


SEARCH_LIMIT = 25
RESPONSE_SEARCH_LIMIT = 8
HISTORY_RESEARCH_RESERVE = 8
DISCOVERY_LATER_PASS_RESERVE = 3
DISCOVERY_LIMIT = SEARCH_LIMIT - HISTORY_RESEARCH_RESERVE
current_state: ContextVar[GenerationState | None] = ContextVar("generation_state", default=None)


class ResearchBudgetExhausted(RuntimeError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


class GenerationState:
    def __init__(self, root: Path, target_date: str, additional: int, model: str, *, resume=False):
        date.fromisoformat(target_date)
        self.root = root
        self.path = root / "build/generation-state" / f"{target_date}.json"
        self.output_names = {f"{target_date}.json", "index.json", "everyday-history.json"}
        settings = {str(path.relative_to(root)): file_digest(path)
                    for folder in ("config", "prompts") for path in sorted((root / folder).glob("*"))
                    if path.is_file()}
        identity = {"date": target_date, "additional": additional, "model": model,
                    "settings": digest(settings), "searchLimit": SEARCH_LIMIT,
                    "discoveryLimit": DISCOVERY_LIMIT,
                    "laterDiscoveryReserve": DISCOVERY_LATER_PASS_RESERVE}
        if resume:
            if not self.path.exists():
                raise ValueError("No generation checkpoint exists for this date")
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            if self.data.get("version") != 1 or self.data.get("identity") != identity:
                raise ValueError("Generation checkpoint does not match the date, append count, model, or settings")
            if (any(type(self.data.get(key)) is not int or self.data[key] < 0
                    for key in ("searches", "discoverySearches"))
                    or self.data["discoverySearches"] > self.data["searches"]
                    or not isinstance(self.data.get("responses"), dict)
                    or not isinstance(self.data.get("failures"), dict)):
                raise ValueError("Invalid generation checkpoint budget or responses")
            self._check_content()
        else:
            self.data = {"version": 1, "identity": identity,
                         "baseline": {name: file_digest(root / "content" / name) for name in self.output_names},
                         "searches": 0, "discoverySearches": 0, "responses": {}, "failures": {}, "completed": None}
            self.save()

    def _check_content(self):
        completed = self.data.get("completed")
        if set(self.data.get("baseline", {})) != self.output_names:
            raise ValueError("Invalid checkpoint content manifest")
        if completed is not None and set(completed) != self.output_names:
            raise ValueError("Invalid checkpoint completed-content manifest")
        for name, original in self.data["baseline"].items():
            path = self.root / "content" / name
            if file_digest(path) == original:
                continue
            if completed is not None and path.exists() and json.loads(path.read_text()) == completed[name]:
                continue
            raise ValueError(f"Cannot resume: content/{name} changed since the checkpoint")

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, self.path)

    def cached(self, key):
        return copy.deepcopy(self.data["responses"].get(key))

    def remember(self, key, result):
        self.data["responses"][key] = copy.deepcopy(result)
        self.data["failures"].pop(key, None)
        # Replay earlier failed branches only after later progress was saved.
        # Terminal failures remain retryable when the run is resumed.
        self.data["failures"] = {failed: True for failed in self.data["failures"]}
        self.save()

    def remember_failure(self, key):
        self.data["failures"][key] = False
        self.save()

    def reserve(self, phase, *, discovery_attempts_remaining=0):
        discovery = phase.startswith("Sourced discovery")
        remaining = SEARCH_LIMIT - self.data["searches"]
        if discovery:
            # Keep a research batch and useful later discovery passes available.
            remaining = min(remaining - HISTORY_RESEARCH_RESERVE,
                            DISCOVERY_LIMIT - self.data["discoverySearches"])
            remaining -= discovery_attempts_remaining * DISCOVERY_LATER_PASS_RESERVE
        allowance = min(RESPONSE_SEARCH_LIMIT, remaining)
        if allowance <= 0:
            raise ResearchBudgetExhausted("Research web-tool budget exhausted")
        self.data["searches"] += allowance
        if discovery:
            self.data["discoverySearches"] += allowance
        self.save()  # An interrupted or uncertain request keeps its reservation.
        return allowance

    def settle(self, phase, allowance, response):
        items = response.get("output")
        if not isinstance(items, list):
            return
        used = sum(isinstance(item, dict) and item.get("type") == "web_search_call" for item in items)
        self.data["searches"] += used - allowance
        if phase.startswith("Sourced discovery"):
            self.data["discoverySearches"] += used - allowance
        self.save()
        return used

    def stage(self, payloads):
        if {path.name for path in payloads} != self.output_names:
            raise ValueError("Unexpected checkpoint output files")
        self.data["completed"] = {path.name: payload for path, payload in payloads.items()}
        self.save()


@contextmanager
def generation_session(root, target_date, additional, model, *, resume=False):
    state = GenerationState(root, target_date, additional, model, resume=resume)
    token = current_state.set(state)
    try:
        yield state
    finally:
        current_state.reset(token)
