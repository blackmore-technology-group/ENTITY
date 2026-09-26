from __future__ import annotations
from pathlib import Path
import hashlib,json,subprocess

HERE=Path(__file__).resolve().parent
TOOL=HERE/'c2patool-v0.27.22'/'c2patool'/'c2patool.exe'

class CanonicalC2paVerifier:
    """Real c2patool-backed provenance verifier with explicit trust/truth separation."""
    def __init__(self,tool_path:str|Path|None=None):
        self.tool=Path(tool_path or TOOL)
        if not self.tool.is_file(): raise FileNotFoundError(str(self.tool))
    def verify(self,asset_path:str|Path)->dict:
        asset=Path(asset_path).resolve()
        if not asset.is_file(): raise FileNotFoundError(str(asset))
        run=subprocess.run([str(self.tool),str(asset)],capture_output=True,text=True)
        if run.returncode!=0: raise RuntimeError((run.stderr or run.stdout).strip())
        report=json.loads(run.stdout); active=(report.get('validation_results') or {}).get('activeManifest') or {}
        success={str(x.get('code')) for x in active.get('success') or []}; failure={str(x.get('code')) for x in active.get('failure') or []}
        provenance_valid=report.get('validation_state')=='Valid' and 'claimSignature.validated' in success and 'assertion.dataHash.match' in success
        signer_trusted='signingCredential.untrusted' not in failure and not any('untrusted' in x.lower() for x in failure)
        return {'schema':'entity-c2pa-verification-v1','asset_path':str(asset),'asset_sha256':hashlib.sha256(asset.read_bytes()).hexdigest(),'tool_path':str(self.tool),'validation_state':report.get('validation_state'),'provenance_valid':bool(provenance_valid),'signer_trusted':bool(signer_trusted),'factual_truth_established':False,'ownership_established':False,'success_codes':sorted(success),'failure_codes':sorted(failure)}
    def status(self): return {'ready':True,'tool':str(self.tool),'real_c2pa_tooling':True,'provenance_separate_from_trust_truth_ownership':True}
