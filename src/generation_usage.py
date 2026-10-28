"""Observed API usage and dated cost estimates; never a billing ledger."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import json
from typing import Any, Callable, Iterator

# Standard USD rates checked 2026-10-28: https://developers.openai.com/api/docs/pricing
RATES_DATE = "2026-10-28"
LUNA_RATES = (0.10, 0.01, 0.50)  # uncached input, cached input, output, per million
WEB_SEARCH_USD = 0.01
_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens", "web_search_calls")
_current: ContextVar[list[dict[str, Any]] | None] = ContextVar("generation_usage", default=None)


def _count(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def usage_record(model: str, phase: str, response: dict[str, Any] | None) -> dict[str, Any]:
    data = response or {}
    usage = data.get("usage") or {}
    usage = usage if isinstance(usage, dict) else {}
    inputs = _count(usage.get("input_tokens"))
    outputs = _count(usage.get("output_tokens"))
    input_details = usage.get("input_tokens_details") or {}
    output_details = usage.get("output_tokens_details") or {}
    cached = _count(input_details.get("cached_tokens")) if isinstance(input_details, dict) else None
    reasoning = _count(output_details.get("reasoning_tokens")) if isinstance(output_details, dict) else None
    items = data.get("output")
    searches = sum(isinstance(item, dict) and item.get("type") == "web_search_call" for item in items) if isinstance(items, list) else None
    actual_model = data.get("model") or model
    tier = data.get("service_tier") or "default"  # requests explicitly use default
    estimate = None
    if (actual_model == "gpt-6-luna" and tier == "default"
            and inputs is not None and outputs is not None and cached is not None
            and cached <= inputs and searches is not None):
        input_rate, cache_rate, output_rate = LUNA_RATES
        if inputs > 272_000:
            input_rate *= 2
            cache_rate *= 2
            output_rate *= 1.5
        estimate = ((inputs - cached) * input_rate + cached * cache_rate + outputs * output_rate) / 1_000_000 + searches * WEB_SEARCH_USD
    return {
        "phase": phase, "requested_model": model, "model": actual_model, "service_tier": tier,
        "input_tokens": inputs, "cached_input_tokens": cached, "output_tokens": outputs,
        "reasoning_tokens": reasoning, "web_search_calls": searches,
        "estimated_usd": round(estimate, 8) if estimate is not None else None,
        "rates_date": RATES_DATE,
    }


def record_usage(model: str, phase: str, response: dict[str, Any] | None, log: Callable[[str], None]) -> None:
    record = usage_record(model, phase, response)
    records = _current.get()
    if records is not None:
        records.append(record)
    log("API usage: " + json.dumps(record, ensure_ascii=True))


@contextmanager
def usage_run(log: Callable[[str], None]) -> Iterator[None]:
    records: list[dict[str, Any]] = []
    token = _current.set(records)
    try:
        yield
    finally:
        _current.reset(token)
        summary: dict[str, Any] = {"requests": len(records), "rates_date": RATES_DATE}
        for field in _FIELDS:
            known = [record[field] for record in records if record[field] is not None]
            summary[field + "_observed"] = sum(known)
            summary[field + "_unknown_requests"] = len(records) - len(known)
        costs = [r["estimated_usd"] for r in records if r["estimated_usd"] is not None]
        summary["estimated_usd_observed"] = round(sum(costs), 8)
        summary["unpriced_requests"] = len(records) - len(costs)
        summary["estimate_complete_for_observed_requests"] = len(costs) == len(records)
        summary["usage_complete"] = all(all(r[f] is not None for f in _FIELDS) for r in records)
        summary["note"] = "Observed estimates only; exclude unreported cache writes and SDK-internal retry usage. Reasoning is included in output. OpenAI billing is authoritative."
        log("API usage total: " + json.dumps(summary, ensure_ascii=True))
