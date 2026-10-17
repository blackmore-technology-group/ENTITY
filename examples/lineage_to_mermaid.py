"""Render a bounded AssetProvenanceGraph.lineage() snapshot (ENTITY v3.4.3).

This non-normative display example verifies no signatures, claims or rights.
See lineage_to_mermaid.md for its input profile and limits.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

MAX_INPUT_BYTES = 1024 * 1024
MAX_EDGES = 128
MAX_LABEL_CHARS = 256


def _unique_fields(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def _label(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > MAX_LABEL_CHARS
        or not value.isprintable()
    ):
        raise ValueError(f"{field} must be 1..{MAX_LABEL_CHARS} printable characters")
    return value


def _mermaid_text(value: str) -> str:
    # Mermaid decimal entities protect delimiters, directives and HTML markup.
    # Encode '#' too, so a literal entity-looking ID stays literal.
    return "".join(
        char if char.isalnum() or char in " ._:/@+-" else f"#{ord(char)};"
        for char in value
    )


def render_lineage(snapshot: object) -> str:
    """Render the recorded one-hop relationships without assessing their claims."""
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be a JSON object")
    root = _label(snapshot.get("asset_id"), "asset_id")
    edges = []
    nodes = {root}
    for side in ("parents", "children"):
        records = snapshot.get(side)
        if not isinstance(records, list):
            raise ValueError(f"{side} must be an array")
        if len(edges) + len(records) > MAX_EDGES:
            raise ValueError(f"snapshot must have at most {MAX_EDGES} relationships")
        for record in records:
            if not isinstance(record, dict):
                raise ValueError(f"each {side} entry must be an object")
            parent = _label(record.get("parent_asset_id"), "parent_asset_id")
            child = _label(record.get("child_asset_id"), "child_asset_id")
            relation = _label(record.get("relation"), "relation")
            if (side == "parents" and child != root) or (
                side == "children" and parent != root
            ):
                raise ValueError(f"{side} entry does not meet asset_id")
            nodes.update((parent, child))
            edges.append((parent, child, relation))
    ids = {asset: f"n{index}" for index, asset in enumerate(sorted(nodes))}
    lines = [
        "flowchart LR",
        "    %% Recorded relationships only; truth and rights are not verified.",
    ]
    lines.extend(f'    {node}["{_mermaid_text(asset)}"]' for asset, node in ids.items())
    lines.extend(
        f'    {ids[parent]} -->|"{_mermaid_text(relation)}"| {ids[child]}'
        for parent, child, relation in sorted(edges)
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="public lineage JSON snapshot")
    args = parser.parse_args(argv)
    try:
        with args.snapshot.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError(f"input exceeds {MAX_INPUT_BYTES} bytes")
        snapshot = json.loads(
            raw.decode("utf-8-sig"),
            object_pairs_hook=_unique_fields,
            parse_constant=_reject_constant,
        )
        diagram = render_lineage(snapshot)
    except (OSError, ValueError, RecursionError) as error:
        print(f"Cannot render lineage: {error}", file=sys.stderr)
        return 1
    sys.stdout.buffer.write(diagram.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
