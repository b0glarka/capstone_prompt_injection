"""JSONL append-log cache for inference runs.

Each line is one JSON object representing one prediction. Files are append-only
so a crash mid-run does not lose completed work; on resume, callers pass the
already-completed keys to skip.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def append_records(cache_path: str | Path, records: Iterable[dict]) -> int:
    """Append records to a JSONL file. Creates parent dirs if missing. Returns count written."""
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with cache_path.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def load_records(cache_path: str | Path) -> list[dict]:
    """Load all records from a JSONL file. Returns empty list if file does not exist."""
    cache_path = Path(cache_path)
    if not cache_path.exists():
        return []
    records = []
    with cache_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def existing_keys(cache_path: str | Path, key: str = "prompt_idx") -> set:
    """Return the set of values for `key` already present in the cache."""
    return {r[key] for r in load_records(cache_path) if key in r}
