"""Synthetic, safe cross-application DataChip trial: not for navigation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
from time import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sdk.datachip.formula_chip import pack_formula_bytes
from sdk.datachip.application import sign_bundle, SCHEMA
from sdk.datachip.host import resolve_host_application
from sdk.datachip.rights import issue_grant,issue_revocation_snapshot


def pub(key):
    return key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)


def main():
    sample=b"SYNTHETIC BC TRAIL,DO NOT NAVIGATE,LAT=0,LON=0\n"*1200
    release=Ed25519PrivateKey.generate()
    rights=Ed25519PrivateKey.generate()
    status=Ed25519PrivateKey.generate()
    now=int(time())
    summary={}
    with tempfile.TemporaryDirectory(prefix="btg-datac-pilot-") as folder:
        path=Path(folder)/"trail.edcf"
        chip=pack_formula_bytes(sample,path)
        artifact_hash=hashlib.sha256(path.read_bytes()).hexdigest()
        module={"name":"bc-trails-synthetic","kind":"geographic",
                "chip_id":chip["chip_id"],"sha256":artifact_hash,
                "requires":[],"data_right":"grant-required"}
        snapshots=issue_revocation_snapshot(status,authority_key_id="btg-status-demo",
            issued_at=now,valid_until=now+600,
            covered_rights_keys=("btg-rights-demo",))
        grants={}
        bodies={}
        for app in ("HuntAR","HikeAR"):
            body={"schema":SCHEMA,"app_id":app,"release_id":"synthetic-pilot-001",
                  "signer_id":"btg-release-demo","host_abi":1,
                  "platforms":["ios","windows","android","linux"],"modules":[module]}
            bodies[app]=sign_bundle(release,body)
            grants[app]=issue_grant(rights,authority_key_id="btg-rights-demo",
                chip_id=chip["chip_id"],subject="demo-operator",audience=app,
                rights_passport_ref="rp:synthetic:trails",not_before=now-30,
                expires_at=now+600)
        for app in ("HuntAR","HikeAR"):
            resolved=resolve_host_application(
                bodies[app],app_id=app,platform="ios",
                trusted_bundle_keys={"btg-release-demo":pub(release)},
                chip_paths={chip["chip_id"]:path},
                authenticated_subject="demo-operator",
                rights_grants={chip["chip_id"]:grants[app]},
                revocation_snapshots={chip["chip_id"]:snapshots},
                pinned_rights_keys={"btg-rights-demo":pub(rights)},
                pinned_revocation_keys={"btg-status-demo":pub(status)},
                now=now)
            assert resolved["module_names_available_for_use"]==["bc-trails-synthetic"]
            summary[app]={"signed_bundle":resolved["signed_bundle_verified"],
                          "scoped_rights_grant":resolved["delegated_grants_verified"][0]["grant_id"],
                          "native_permissions_granted":resolved["native_permissions_granted"]}
        try:
            resolve_host_application(
                bodies["HikeAR"],app_id="HikeAR",platform="ios",
                trusted_bundle_keys={"btg-release-demo":pub(release)},
                chip_paths={chip["chip_id"]:path},
                authenticated_subject="demo-operator",
                rights_grants={chip["chip_id"]:grants["HuntAR"]},
                revocation_snapshots={chip["chip_id"]:snapshots},
                pinned_rights_keys={"btg-rights-demo":pub(rights)},
                pinned_revocation_keys={"btg-status-demo":pub(status)},now=now)
            raise AssertionError("HuntAR rights erroneously accepted by HikeAR")
        except PermissionError:
            summary["cross_app_rights_leak"]="REJECTED"
        summary["chip_id"]=chip["chip_id"]
        summary["logical_bytes"]=len(sample)
        summary["chip_file_bytes"]=path.stat().st_size
        summary["same_physical_chip_reused"]=True
        summary["synthetic_only"]=True
    print(json.dumps(summary,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
