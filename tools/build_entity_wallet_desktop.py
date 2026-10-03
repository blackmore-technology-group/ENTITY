from __future__ import annotations
from pathlib import Path
import os, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/"tools"/"entity_wallet_desktop.py"

DATA_PATHS=[
  "ENTITY_CURRENT_RELEASE_ORIGIN.json",
  "protocol/origin",
  "tools/entity_v3_4_cli.py",
  "src/01_Core_Runtime/identity/canonical_identity.py",
  "src/11_ADAM/full_runtime",
  "src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py",
  "src/31_Profiles/exchange_protocol.py",
  "src/36_Adoption_Layer",
  "src/37_Verifiable_Reality",
  "src/38_Global_Passports",
  "src/39_Implementation_Packages",
  "src/40_BTDU",
  "src/42_ENTITY_Wallet",
  "sdk/global_passport_sdk",
]

def main():
    sep=os.pathsep
    cmd=[sys.executable,"-m","PyInstaller","--noconfirm","--clean","--windowed",
         "--name","ENTITY-Wallet",
         "--hidden-import","cryptography.hazmat.primitives.asymmetric.ed25519",
         "--hidden-import","cryptography.hazmat.primitives.serialization"]
    for rel in DATA_PATHS:
        src=ROOT/rel; dest=str(Path(rel).parent if src.is_file() else Path(rel))
        cmd += ["--add-data",f"{src}{sep}{dest}"]
    cmd.append(str(ENTRY))
    subprocess.run(cmd,cwd=ROOT,check=True)
    print(ROOT/"dist")

if __name__=="__main__": main()
