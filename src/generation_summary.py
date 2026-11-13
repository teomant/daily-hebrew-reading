"""Small run reports without prompts, article text, or API credentials."""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
import html
import json
import os
from pathlib import Path
from time import monotonic

from .generation_state import SEARCH_LIMIT, DISCOVERY_LIMIT, HISTORY_RESEARCH_RESERVE, DISCOVERY_LATER_PASS_RESERVE

_current = ContextVar("generation_summary", default=None)
EVENT_LIMIT = 20
TEXT_LIMIT = 350


def observe(message: str) -> None:
    report = _current.get()
    if report is not None:
        report.observe(message)


def record_targets(**targets) -> None:
    report = _current.get()
    if report is not None:
        report.data["targets"] = targets


class GenerationSummary:
    def __init__(self, target_date, additional, resume, model):
        self.started = monotonic()
        self.data = {
            "schemaVersion": 1, "date": target_date, "model": model,
            "additionalStories": additional, "resume": resume,
            "runId": os.environ.get("GITHUB_RUN_ID"),
            "runAttempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "sha": os.environ.get("GITHUB_SHA"),
            "startedAt": datetime.now(UTC).isoformat(), "status": "running",
            "targets": {}, "editions": {}, "research": [], "diagnostics": [], "omissions": [],
            "eventCounts": {}, "omittedEvents": {}, "usage": None,
            "researchRequests": [], "budget": None,
        }

    def observe(self, message):
        if message.startswith("API usage total: "):
            self.data["usage"] = json.loads(message.removeprefix("API usage total: "))
            return
        if message.startswith("API usage: "):
            record = json.loads(message.removeprefix("API usage: "))
            if record["phase"].startswith(("Sourced discovery", "HISTORY research")):
                self.data["researchRequests"].append(record)
            return
        # Only operational messages reach this observer; prompt logging bypasses it.
        if message.startswith(("Sourced discovery", "HISTORY research")):
            if any(text in message for text in ("started with model", "response received", "completed after")):
                return
            group = "research"
        elif "omitting" in message or "writing requests exhausted" in message:
            group = "omissions"
        elif any(text in message for text in (
            "omitting", "exhausted", "failed", "quality warning", "below the target",
            "Preparing ", "Planning completed", "Restored completed issue",
        )):
            group = "diagnostics"
        else:
            return
        counts = self.data["eventCounts"]
        counts[group] = counts.get(group, 0) + 1
        if len(self.data[group]) < EVENT_LIMIT:
            self.data[group].append(message[:TEXT_LIMIT])
        else:
            omitted = self.data["omittedEvents"]
            omitted[group] = omitted.get(group, 0) + 1

    def finish(self, issue, state):
        self.data["status"] = "success" if issue is not None else "no-change"
        if issue is not None:
            for level, edition in issue.get("editions", {}).items():
                stories = edition["stories"]
                self.data["editions"][level] = {
                    "total": len(stories), "counts": dict(Counter(s["type"] for s in stories)),
                    "historyIds": [s["id"] for s in stories if s["type"] == "history"],
                }
        self.budget(state)

    def budget(self, state):
        self.data["budget"] = {
            "usedOrReserved": state.data["searches"], "limit": SEARCH_LIMIT,
            "discoveryUsedOrReserved": state.data["discoverySearches"], "discoveryLimit": DISCOVERY_LIMIT,
            "historyResearchReserve": HISTORY_RESEARCH_RESERVE,
            "laterDiscoveryPassReserve": DISCOVERY_LATER_PASS_RESERVE,
        }

    def markdown(self):
        def safe(value):
            return html.escape(str(value)).replace("\n", " ").replace("|", "&#124;")

        data = self.data
        lines = [f"## Generation summary: {data['date']}", "",
                 f"Status: **{data['status']}**. Model: {safe(data['model'])}. Resume: {data['resume']}.",
                 "This report describes generation only; later build, commit, and deployment steps have separate results.",
                 ""]
        if data.get("errorType"):
            lines += [f"Failure: {safe(data['errorType'])}. See the job log for the exception details.", ""]
        if data["targets"]:
            lines += [f"Requested targets: {safe(json.dumps(data['targets']))}.", ""]
        lines += ["Counts describe the complete resulting issue, including earlier articles on append runs.", "",
                  "| Edition | Total | CURRENT | HISTORY | EVERYDAY | DIALOG | SHORTS | VERBS |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for level, edition in data["editions"].items():
            counts = edition["counts"]
            cells = [safe(level), str(edition["total"])] + [str(counts.get(kind, 0)) for kind in
                     ("current", "history", "everyday", "dialog", "shorts", "verbs")]
            lines.append("| " + " | ".join(cells) + " |")
        for level, edition in data["editions"].items():
            lines += ["", f"HISTORY ({safe(level)}): {safe(', '.join(edition['historyIds']) or 'none')}."]
        if data["budget"]:
            budget = data["budget"]
            lines += ["", f"Web calls used or reserved: {budget['usedOrReserved']}/{budget['limit']}; "
                      f"discovery: {budget['discoveryUsedOrReserved']}/{budget['discoveryLimit']}.",
                      f"Discovery protects {budget['historyResearchReserve']} calls for history research and "
                      f"{budget['laterDiscoveryPassReserve']} calls for each later discovery pass."]
        usage = data["usage"]
        if usage is not None:
            lines += ["", f"This invocation: {usage['requests']} API requests; "
                      f"{usage['input_tokens_observed']} input tokens; {usage['output_tokens_observed']} output tokens; "
                      f"{usage['web_search_calls_observed']} observed web calls; "
                      f"estimated cost **${usage['estimated_usd_observed']:.4f}**.",
                      f"Unpriced requests: {usage['unpriced_requests']}; complete usage: {usage['usage_complete']}.",
                      "Resumed runs exclude previous invocations from usage and cost; the budget includes saved reservations.",
                      safe(usage["note"])]
        if data["researchRequests"]:
            lines += ["", "| Research request | Observed web calls | Estimated USD |",
                      "| --- | ---: | ---: |"]
            for record in data["researchRequests"]:
                calls, cost = record["web_search_calls"], record["estimated_usd"]
                lines.append(f"| {safe(record['phase'])} | {calls if calls is not None else 'unknown'} | "
                             f"{f'{cost:.4f}' if cost is not None else 'unknown'} |")
        for group in ("research", "omissions", "diagnostics"):
            lines += ["", f"### {group.capitalize()}", ""]
            lines += [f"- {safe(event)}" for event in data[group]] or ["No events recorded."]
            if data["omittedEvents"].get(group):
                lines += [f"- {data['omittedEvents'][group]} additional events omitted; see the full log."]
        return "\n".join(lines) + "\n"


@contextmanager
def summary_run(root: Path, target_date, additional, resume, model):
    # Validate before using the date as a filename, including failed invocations.
    from datetime import date
    date.fromisoformat(target_date)
    report = GenerationSummary(target_date, additional, resume, model)
    token = _current.set(report)
    try:
        yield report
    except BaseException as exc:
        report.data["status"] = "failed"
        report.data["errorType"] = type(exc).__name__
        raise
    finally:
        _current.reset(token)
        report.data["durationSeconds"] = round(monotonic() - report.started, 2)
        report.data["finishedAt"] = datetime.now(UTC).isoformat()
        folder = root / "build/generation-summary"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            for suffix, content in (("json", json.dumps(report.data, ensure_ascii=False, indent=2) + "\n"),
                                    ("md", report.markdown())):
                path = folder / f"{target_date}.{suffix}"
                temporary = path.with_suffix(path.suffix + ".tmp")
                temporary.write_text(content, encoding="utf-8")
                temporary.replace(path)
        except OSError as exc:
            # Reporting must not turn a saved issue into a failed generation.
            print(f"Generation summary could not be saved ({type(exc).__name__})", flush=True)
