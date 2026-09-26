from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[1]


def _default_manifest() -> Path:
    for name in ("SHA256SUMS_V1_RC2.txt", "SHA256SUMS_V1.txt"):
        candidate = ROOT / name
        if candidate.exists():
            return candidate
    return ROOT / "SHA256SUMS_V1_RC2.txt"


def verify_manifest(manifest: Path) -> int:
    if not manifest.exists():
        raise SystemExit(f"release manifest missing: {manifest}")
    checked = 0
    seen: set[str] = set()
    for line_number, raw in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            expected, relative = raw.split("  ", 1)
        except ValueError as exc:
            raise SystemExit(f"invalid manifest line {line_number}") from exc
        if relative in seen:
            raise SystemExit(f"duplicate manifest path: {relative}")
        seen.add(relative)
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"manifest file missing: {relative}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f"manifest mismatch: {relative}")
        checked += 1
    if checked == 0:
        raise SystemExit("release manifest contains no files")
    excluded = {
        manifest.resolve(),
        (ROOT / "ADAM_V1_RC2_MANIFEST_SIGNATURE.hex").resolve(),
    }
    actual = {
        path.resolve()
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.resolve() not in excluded
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
        and path.name != ".coverage"
        and not path.name.endswith(".pyc")
    }
    listed = {(ROOT / relative).resolve() for relative in seen}
    unexpected = sorted(str(path.relative_to(ROOT)) for path in actual - listed)
    if unexpected:
        preview = ", ".join(unexpected[:10])
        raise SystemExit(f"unmanifested release files detected: {preview}")
    return checked


def verify_signature(manifest: Path, public_key_path: Path, signature_path: Path) -> str:
    try:
        public_raw = bytes.fromhex(public_key_path.read_text("utf-8").strip())
        signature = bytes.fromhex(signature_path.read_text("utf-8").strip())
        Ed25519PublicKey.from_public_bytes(public_raw).verify(signature, manifest.read_bytes())
    except (OSError, ValueError, InvalidSignature) as exc:
        raise SystemExit("release manifest signature verification failed") from exc
    return hashlib.sha256(public_raw).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the ADAM v1 RC2 release manifest before imports execute")
    parser.add_argument("--manifest", type=Path, default=_default_manifest())
    parser.add_argument("--public-key", type=Path, default=ROOT / "ADAM_V1_RC2_RELEASE_PUBLIC_KEY.hex")
    parser.add_argument("--signature", type=Path, default=ROOT / "ADAM_V1_RC2_MANIFEST_SIGNATURE.hex")
    parser.add_argument("--expected-signer-sha256", help="required trusted release-signer fingerprint for production launchers")
    parser.add_argument("--allow-unsigned", action="store_true", help="development-only; never use for a sealed release")
    args = parser.parse_args(argv)
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    checked = verify_manifest(manifest)
    fingerprint = None
    if args.public_key.exists() and args.signature.exists():
        fingerprint = verify_signature(manifest, args.public_key, args.signature)
        if args.expected_signer_sha256 and fingerprint.lower() != args.expected_signer_sha256.lower():
            raise SystemExit("release signer fingerprint does not match trusted launcher pin")
    elif not args.allow_unsigned:
        raise SystemExit("sealed release signature files are missing")
    suffix = f" signer_sha256={fingerprint}" if fingerprint else " unsigned_development_mode=true"
    print(f"MANIFEST_PASS files={checked}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
