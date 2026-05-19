import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class JsonlStore:
    """Append-only JSONL store for human-readable operational logs."""

    def __init__(self, log_dir: str | Path = "data_folder/output/jsonl"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def append(self, stream: str, payload: Dict[str, Any]):
        record = dict(payload)
        record.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        path = self.log_dir / f"{stream}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str))
            handle.write("\n")

    def read_all(self, stream: str) -> list[dict]:
        path = self.log_dir / f"{stream}.jsonl"
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows
