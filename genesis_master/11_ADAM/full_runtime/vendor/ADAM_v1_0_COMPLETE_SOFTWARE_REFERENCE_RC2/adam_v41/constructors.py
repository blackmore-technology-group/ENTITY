from __future__ import annotations

import csv
import io
import json
from typing import Iterable

from .universe import AtomicUniverse


class Constructor:
    """Boundary materializer. Outputs are disposable and never authoritative."""

    def __init__(self, universe: AtomicUniverse):
        self.universe = universe

    def entity_json(self, entity_id: str, *, at_seq: int | None = None) -> str:
        return json.dumps(self.universe.entity_view(entity_id, at_seq=at_seq), sort_keys=True, ensure_ascii=False)

    def entities_csv(self, entity_ids: Iterable[str]) -> str:
        rows = [self.universe.entity_view(x) for x in entity_ids]
        if not rows:
            return ""
        fields = sorted({k for row in rows for k in row})
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    def entity_markdown(self, entity_id: str) -> str:
        view = self.universe.entity_view(entity_id)
        lines = [f"# {view['_type'].title()} {view['_key']}", ""]
        for key in sorted(k for k in view if not k.startswith("_")):
            lines.append(f"- **{key}:** {view[key]}")
        return "\n".join(lines) + "\n"
