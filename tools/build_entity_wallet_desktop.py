from __future__ import annotations
from pathlib import Path
import ast, importlib.util, os, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/"tools"/"entity_wallet_desktop.py"

DATA_PATHS=[
  "ENTITY_CURRENT_RELEASE_ORIGIN.json",
  "protocol/origin",
  "protocol/profiles",
  "tools/entity_v3_4_cli.py",
  "src/01_Core_Runtime/identity/canonical_identity.py",
  "src/11_ADAM/full_runtime",
  "src/22_Sovereign_Domain",
  "genesis_master/04_Entity_Registry/relationships/canonical_sovereign_authority.py",
  "src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py",
  "src/31_Profiles/exchange_protocol.py",
  "src/36_Adoption_Layer",
  "src/37_Verifiable_Reality",
  "src/38_Global_Passports",
  "src/39_Implementation_Packages",
  "src/40_BTDU",
  "src/42_ENTITY_Wallet",
  "src/45_ENTITY_Market",
  "sdk/global_passport_sdk",
]

def _python_sources():
    yield ENTRY
    for rel in DATA_PATHS:
        p=ROOT/rel
        if p.is_file() and p.suffix.lower()==".py":
            yield p
        elif p.is_dir():
            yield from p.rglob("*.py")

def discover_hidden_imports():
    """Collect importable dependencies referenced by modules shipped as runtime data.

    PyInstaller cannot see imports inside files loaded later via importlib, so
    those dependencies must be made explicit at build time.
    """
    modules={"hmac","cryptography.hazmat.primitives.asymmetric.ed25519",
             "cryptography.hazmat.primitives.serialization"}
    for path in _python_sources():
        try:
            tree=ast.parse(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node,ast.ImportFrom) and node.level==0 and node.module:
                modules.add(node.module)
    available=[]
    for name in sorted(modules):
        try:
            if importlib.util.find_spec(name) is not None:
                available.append(name)
        except (ImportError,AttributeError,ModuleNotFoundError,ValueError):
            pass
    return available

def main():
    sep=os.pathsep
    cmd=[sys.executable,"-m","PyInstaller","--noconfirm","--clean","--windowed",
         "--name","ENTITY-Wallet"]
    for module in discover_hidden_imports():
        cmd += ["--hidden-import",module]
    for rel in DATA_PATHS:
        src=ROOT/rel; dest=str(Path(rel).parent if src.is_file() else Path(rel))
        cmd += ["--add-data",f"{src}{sep}{dest}"]
    cmd.append(str(ENTRY))
    subprocess.run(cmd,cwd=ROOT,check=True)
    print(ROOT/"dist")

if __name__=="__main__": main()
