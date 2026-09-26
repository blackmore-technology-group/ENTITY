from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "v501_source_audit_qualification"
WHEEL_DIR = ROOT / "artifacts" / "wheel_v501"
PACKAGES = [f"adam_v{version}" for version in range(41, 51)]


def main() -> int:
    shutil.rmtree(WHEEL_DIR, ignore_errors=True)
    WHEEL_DIR.mkdir(parents=True, exist_ok=True)
    build_log = OUT / "wheel_build.log"
    install_log = OUT / "wheel_install.log"
    build = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "-w", str(WHEEL_DIR)],
        cwd=ROOT, text=True, capture_output=True,
    )
    build_log.write_text(build.stdout + build.stderr, encoding="utf-8")
    if build.returncode != 0:
        raise SystemExit(build.returncode)
    wheels = sorted(WHEEL_DIR.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected one wheel, found {len(wheels)}")
    wheel = wheels[0]
    with tempfile.TemporaryDirectory(prefix="adam-v501-wheel-") as temp:
        target = Path(temp) / "site"
        install = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target), str(wheel)],
            cwd=ROOT, text=True, capture_output=True,
        )
        install_log.write_text(install.stdout + install.stderr, encoding="utf-8")
        if install.returncode != 0:
            raise SystemExit(install.returncode)
        code = "import " + ", ".join(PACKAGES) + "; print('IMPORT_SMOKE_PASS')"
        smoke = subprocess.run([sys.executable, "-c", code], cwd=Path(temp),
                               env={"PYTHONPATH": str(target)}, text=True, capture_output=True)
        if smoke.returncode != 0 or "IMPORT_SMOKE_PASS" not in smoke.stdout:
            raise RuntimeError(smoke.stdout + smoke.stderr)
    payload = {
        "format": "ADAM-v0.50.1-wheel-qualification",
        "version": "0.50.1.dev4",
        "wheel": str(wheel.relative_to(ROOT)),
        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "build": "PASS",
        "install_to_isolated_target": "PASS",
        "package_imports": PACKAGES,
        "import_smoke": "PASS",
        "note": "Built without build isolation or dependency downloads; locally installed setuptools satisfied the build backend.",
    }
    path = OUT / "ADAM_V0501_WHEEL_QUALIFICATION.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
