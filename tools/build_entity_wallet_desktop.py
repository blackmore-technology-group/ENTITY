from __future__ import annotations
from pathlib import Path
import os, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/"tools"/"entity_wallet_desktop.py"
FILES=[
  "src/01_Core_Runtime/identity/canonical_identity.py",
  "src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py",
  "src/31_Profiles/exchange_protocol.py",
  "src/42_ENTITY_Wallet/canonical_wallet.py",
  "src/42_ENTITY_Wallet/asset_ingest.py",
]

def main():
    sep=os.pathsep
    cmd=[sys.executable,"-m","PyInstaller","--noconfirm","--clean","--windowed",
         "--name","ENTITY-Wallet",
         "--hidden-import","cryptography.hazmat.primitives.asymmetric.ed25519",
         "--hidden-import","cryptography.hazmat.primitives.serialization"]
    for rel in FILES:
        src=ROOT/rel; dest=str(Path(rel).parent)
        cmd += ["--add-data",f"{src}{sep}{dest}"]
    cmd.append(str(ENTRY))
    subprocess.run(cmd,cwd=ROOT,check=True)
    print(ROOT/"dist")

if __name__=="__main__": main()
