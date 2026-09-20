from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json
PIN=Path(__file__).resolve().parents[1]/"src"/"11_ADAM"/"full_runtime"/"ADAM_REFERENCE_PIN.json"
def main():
 p=argparse.ArgumentParser(); p.add_argument("package",type=Path); a=p.parse_args(); pin=json.loads(PIN.read_text(encoding="utf-8")); actual=hashlib.sha256(a.package.read_bytes()).hexdigest(); expected=pin["authoritative_inner_sha256"]; print(json.dumps({"package":str(a.package),"actual_sha256":actual,"expected_sha256":expected,"valid":actual==expected},indent=2)); return 0 if actual==expected else 1
if __name__=="__main__": raise SystemExit(main())
