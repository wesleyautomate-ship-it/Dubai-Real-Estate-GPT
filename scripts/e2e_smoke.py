"""
End-to-end smoke tester for RealEstateGPT backend.
Runs a minimal set of API calls and prints a compact summary.
Default base URL: http://localhost:8787
"""

from __future__ import annotations

import os
import sys
import json
import time
from typing import Any, Dict, Optional

import requests

BASE_URL = os.getenv("BASE_URL", "http://localhost:8787")
TIMEOUT = float(os.getenv("SMOKE_TIMEOUT", "10"))
PROVIDER = os.getenv("SMOKE_PROVIDER", "gemini")
SKIP_SEARCH = os.getenv("SMOKE_SKIP_SEARCH", "").lower() in {"1", "true", "yes"}
SKIP_CHAT = os.getenv("SMOKE_SKIP_CHAT", "").lower() in {"1", "true", "yes"}
SKIP_CMA = os.getenv("SMOKE_SKIP_CMA", "").lower() in {"1", "true", "yes"}
SKIP_ALERTS = os.getenv("SMOKE_SKIP_ALERTS", "").lower() in {"1", "true", "yes"}
SKIP_HYGIENE = os.getenv("SMOKE_SKIP_HYGIENE", "").lower() in {"1", "true", "yes"}
SKIP_PORTFOLIO = os.getenv("SMOKE_SKIP_PORTFOLIO", "").lower() in {"1", "true", "yes"}


def log(msg: str) -> None:
    print(msg, flush=True)


def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    resp = requests.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    resp = requests.post(url, json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def run() -> int:
    summary: Dict[str, Any] = {}
    started = time.time()

    try:
        summary["health"] = api_get("/health")
        log(f"health: {summary['health'].get('status')}")
    except Exception as exc:
        log(f"health request failed: {exc}")
        return 1

    try:
        summary["stats"] = api_get("/api/stats")
        log(f"stats: properties={summary['stats'].get('total_properties')}")
    except Exception as exc:
        log(f"stats failed: {exc}")

    try:
        summary["alias_map"] = api_get("/api/tools/alias_map")
        log(
            f"alias_map: communities={len(summary['alias_map'].get('communities', {}))} "
            f"buildings={len(summary['alias_map'].get('buildings', {}))}"
        )
    except Exception as exc:
        log(f"alias_map failed: {exc}")

    if not SKIP_SEARCH:
        try:
            summary["search"] = api_get(
                "/api/search",
                params={
                    "q": "2 bedroom in Downtown",
                    "limit": 3,
                    "provider": PROVIDER,
                },
            )
            log(f"search: total={summary['search'].get('total')} fallback={summary['search'].get('used_fallback')}")
        except Exception as exc:
            log(f"search failed: {exc}")
    else:
        log("search: skipped")

    try:
        payload = {"unit": "905", "building": "Castleton", "provider": PROVIDER}
        summary["owner"] = api_post("/api/tools/current_owner", payload)
        log(f"owner: found={summary['owner'].get('found')} request_id={summary['owner'].get('request_id')}")
    except Exception as exc:
        log(f"current_owner failed: {exc}")

    try:
        payload = {"unit": "905", "building": "Castleton", "limit": 5, "provider": PROVIDER}
        summary["history"] = api_post("/api/tools/transaction_history", payload)
        log(f"history: found={summary['history'].get('found')} count={len(summary['history'].get('history', []))}")
    except Exception as exc:
        log(f"transaction_history failed: {exc}")

    if not SKIP_PORTFOLIO:
        try:
            payload = {"name": "Test Owner", "provider": PROVIDER}
            summary["portfolio"] = api_post("/api/tools/owner_portfolio", payload)
            log(f"portfolio: found={summary['portfolio'].get('found')} total={summary['portfolio'].get('total_properties')}")
        except Exception as exc:
            log(f"owner_portfolio failed: {exc}")
    else:
        log("portfolio: skipped")

    if not SKIP_CMA:
        try:
            payload = {"community": "Downtown Dubai", "bedrooms": 2, "size_sqft": 1500, "provider": PROVIDER}
            summary["cma"] = api_post("/api/tools/cma", payload)
            log(f"cma: found={summary['cma'].get('found')} comps={len(summary['cma'].get('comparables', []))}")
        except Exception as exc:
            log(f"cma failed: {exc}")
    else:
        log("cma: skipped")

    if not SKIP_ALERTS:
        try:
            payload = {"query": "Notify me for Downtown", "community": "Downtown Dubai", "notify_email": "test@example.com"}
            summary["alert_save"] = api_post("/api/tools/alerts", payload)
            summary["alerts"] = api_get("/api/tools/alerts")
            log(f"alerts: total={summary['alerts'].get('total')}")
        except Exception as exc:
            log(f"alerts failed: {exc}")
    else:
        log("alerts: skipped")

    if not SKIP_HYGIENE:
        try:
            summary["hygiene"] = api_get("/api/tools/portfolio_hygiene")
            log(f"hygiene: duplicates={summary['hygiene'].get('total_duplicates')}")
        except Exception as exc:
            log(f"hygiene failed: {exc}")
    else:
        log("hygiene: skipped")

    if not SKIP_CHAT:
        try:
            payload = {
                "history": [],
                "message": "Who owns unit 905 in Castleton?",
                "provider": PROVIDER,
                "user_ctx": {},
            }
            summary["chat"] = api_post("/api/chat", payload)
            meta = summary["chat"].get("meta", {})
            log(f"chat: latency_ms={meta.get('latency_ms')} provider={meta.get('provider')}")
        except Exception as exc:
            log(f"chat failed: {exc}")
    else:
        log("chat: skipped")

    elapsed = round((time.time() - started), 2)
    log(f"done in {elapsed}s")
    # Print compact JSON summary for CI/debug
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(run())
