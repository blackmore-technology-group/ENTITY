from __future__ import annotations

import hashlib
import json
import re
from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
DIRECT = ["cryptography", "msgpack", "numpy", "Pillow", "sympy", "coverage", "pytest", "setuptools", "pip"]


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def distribution_tree_hash(dist: metadata.Distribution) -> str:
    rows: list[tuple[str, str]] = []
    for file in dist.files or ():
        path = dist.locate_file(file)
        if not path.is_file() or str(file).endswith((".pyc", ".pyo")):
            continue
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
        rows.append((str(file).replace("\\", "/"), digest))
    encoded = json.dumps(sorted(rows), separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    installed = {normalized(dist.metadata["Name"]): dist for dist in metadata.distributions() if dist.metadata.get("Name")}
    queue = [normalized(name) for name in DIRECT]
    selected: dict[str, metadata.Distribution] = {}
    while queue:
        name = queue.pop(0)
        if name in selected or name not in installed:
            continue
        dist = installed[name]
        selected[name] = dist
        for raw in dist.requires or ():
            try:
                requirement = Requirement(raw)
            except Exception:
                continue
            if requirement.marker and not requirement.marker.evaluate():
                continue
            queue.append(normalized(requirement.name))

    components = []
    lock_lines = ["# ADAM v1.0 RC2 exact Python dependency constraints", "# Installed-tree hashes are evidence for this qualification host, not PyPI wheel hashes."]
    for name, dist in sorted(selected.items()):
        version = dist.version
        tree_hash = distribution_tree_hash(dist)
        lock_lines.append(f"{dist.metadata['Name']}=={version}  # installed-tree-sha256={tree_hash}")
        components.append({
            "type": "library",
            "name": dist.metadata["Name"],
            "version": version,
            "purl": f"pkg:pypi/{normalized(dist.metadata['Name'])}@{version}",
            "hashes": [{"alg": "SHA-256", "content": tree_hash}],
            "properties": [{"name": "adam:hash-kind", "value": "qualified-host-installed-tree"}],
        })

    wheel = next((ROOT / "dist").glob("*.whl"))
    wheel_hash = hashlib.sha256(wheel.read_bytes()).hexdigest()
    components.insert(0, {
        "type": "application",
        "name": "adam-v1-complete-software-reference",
        "version": "1.0.0rc2",
        "hashes": [{"alg": "SHA-256", "content": wheel_hash}],
        "purl": "pkg:pypi/adam-v1-complete-software-reference@1.0.0rc2",
    })
    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": "urn:uuid:" + hashlib.sha256(json.dumps(components, sort_keys=True).encode()).hexdigest()[:32],
        "version": 1,
        "metadata": {"component": components[0]},
        "components": components,
    }
    (ROOT / "ADAM_V1_RC2_SOURCE_SBOM.cdx.json").write_text(json.dumps(bom, indent=2, sort_keys=True) + "\n", "utf-8")
    (ROOT / "PYTHON_DEPENDENCY_LOCK_V1_RC2.txt").write_text("\n".join(lock_lines) + "\n", "utf-8")
    print(json.dumps({"components": len(components), "wheel_sha256": wheel_hash}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
