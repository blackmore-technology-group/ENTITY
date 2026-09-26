from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLog:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.hmac_key = os.getenv("BECP_AUDIT_HMAC_KEY", "").encode()
        self.previous_hash = self._last_hash()

    def _last_hash(self) -> str:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return "GENESIS"
        try:
            last = self.path.read_text(encoding="utf-8").splitlines()[-1]
            return json.loads(last).get("record_hash", "GENESIS")
        except Exception:
            return "UNREADABLE_PREVIOUS_RECORD"

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "previous_hash": self.previous_hash,
            **event,
        }
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        record_hash = hashlib.sha256(canonical).hexdigest()
        record["record_hash"] = record_hash
        if self.hmac_key:
            record["record_hmac"] = hmac.new(
                self.hmac_key, record_hash.encode(), hashlib.sha256
            ).hexdigest()
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        self.previous_hash = record_hash
        return record
