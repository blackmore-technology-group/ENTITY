from __future__ import annotations
from pathlib import Path
import base64, hashlib, json, os, subprocess
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HERE=Path(__file__).resolve().parent
TPM_SCRIPT=HERE/"tpm_cng.ps1"
PROVIDER="Microsoft Platform Crypto Provider"

def _run(action:str,key_name:str,data:bytes|None=None)->dict:
    cmd=["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",str(TPM_SCRIPT),"-Action",action,"-KeyName",str(key_name)]
    if data is not None: cmd += ["-DataB64",base64.b64encode(data).decode("ascii")]
    run=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
    if run.returncode!=0: raise RuntimeError((run.stderr or run.stdout).strip())
    lines=[x.strip() for x in run.stdout.splitlines() if x.strip()]
    if not lines: raise RuntimeError("TPM helper returned no result")
    return json.loads(lines[-1])

class WindowsTpmProtector:
    """TPM-backed non-exportable RSA wrapping key using Windows Platform Crypto Provider."""
    def __init__(self,key_name:str="ENTITY-ROOT-RECOVERY-PROTECTOR-v1"):
        self.key_name=str(key_name); _run("ensure",self.key_name)
    def probe(self)->dict:
        out=_run("probe",self.key_name)
        out["hardware_backed_required"]=True
        out["provider_expected"]=PROVIDER
        return out
    def wrap(self,raw:bytes)->bytes:
        out=_run("wrap",self.key_name,bytes(raw)); return base64.b64decode(out["wrapped_b64"])
    def unwrap(self,cipher:bytes)->bytes:
        out=_run("unwrap",self.key_name,bytes(cipher)); return base64.b64decode(out["plain_b64"])
    def delete(self)->None: _run("delete",self.key_name)

class PortableRecoveryEscrow:
    """Explicit user-held AES key escrow so sovereign recovery is not coupled to one TPM."""
    @staticmethod
    def seal(raw:bytes,recovery_secret:bytes,*,context:str)->dict:
        key=hashlib.sha256(bytes(recovery_secret)).digest(); nonce=os.urandom(12)
        aad=str(context).encode("utf-8"); cipher=AESGCM(key).encrypt(nonce,bytes(raw),aad)
        return {"schema":"entity-portable-recovery-escrow-v1","context":str(context),"nonce_b64":base64.b64encode(nonce).decode(),"ciphertext_b64":base64.b64encode(cipher).decode(),"cipher":"AES-256-GCM","recovery_secret_stored":False}
    @staticmethod
    def open(envelope:dict,recovery_secret:bytes)->bytes:
        key=hashlib.sha256(bytes(recovery_secret)).digest(); nonce=base64.b64decode(envelope["nonce_b64"]); cipher=base64.b64decode(envelope["ciphertext_b64"])
        return AESGCM(key).decrypt(nonce,cipher,str(envelope["context"]).encode("utf-8"))

def commissioning_status(key_name:str="ENTITY-ROOT-RECOVERY-PROTECTOR-v1")->dict:
    p=WindowsTpmProtector(key_name); out=p.probe()
    out["commissioned"]=bool(out.get("ready") and out.get("private_export_blocked") and out.get("provider")==PROVIDER)
    out["sovereign_portable_escrow_supported"]=True
    return out
