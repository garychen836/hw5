"""Append-only audit trail for every agent-loop step.

output/audit_trail.json is one JSON array. Each call to record() adds one
entry and rewrites the file with the old entries kept in order; nothing is
ever removed, so a new run never wipes an old one. The same entries are kept
in memory so the backend can stream recent events to the dashboard.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

AUDIT_PATH = Path(os.getenv("AUDIT_PATH", Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"))
MAX_TEXT = 2_000  # long tool results are cut so the file stays readable

_lock = threading.Lock()
_recent: list[dict] = []
_seq = 0


def _clip(value: Any) -> Any:
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + f"... [{len(text) - MAX_TEXT} more chars]"


def _load() -> list[dict]:
    if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
        return []
    try:
        data = json.loads(AUDIT_PATH.read_text())
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        # Never destroy a damaged trail: keep it beside the new one.
        AUDIT_PATH.rename(AUDIT_PATH.with_suffix(f".broken-{datetime.now():%Y%m%d%H%M%S}.json"))
        return []


def record(event: str, *, run_id: str, ticket_id: int | None, agent: str, chain: list[str] | None = None,
           **data: Any) -> dict:
    """Append one audit entry and return it."""
    global _seq
    entry = {
        "ts": datetime.now().isoformat(timespec="milliseconds"),
        "run_id": run_id,
        "ticket_id": ticket_id,
        "agent": agent,
        "chain": " > ".join(chain or [agent]),
        "event": event,
        **{k: (_clip(v) if k in ("args", "result", "text", "output", "error") else v) for k, v in data.items()},
    }
    with _lock:
        trail = _load()
        _seq = max(_seq, len(trail)) + 1  # keeps seq unique across restarts
        entry["seq"] = _seq
        trail.append(entry)
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = AUDIT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(trail, indent=2, default=str))
        tmp.replace(AUDIT_PATH)
        _recent.append(entry)
        del _recent[:-2_000]
    return entry


def recent(since_seq: int = 0, run_id: str | None = None) -> list[dict]:
    """Entries recorded by this process after since_seq (for the dashboard)."""
    with _lock:
        return [e for e in _recent if e["seq"] > since_seq and (run_id is None or e["run_id"] == run_id)]
