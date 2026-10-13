"""ENTITY's ACTUAL RightsPassportRegistry + separate execution/revocation authority.

All identities and signing keys are synthetic test fixtures. Never uses a wallet,
prod issuer or a production key. Existing EXPORT permission is not EXECUTE.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sdk.datachip.formula_chip import pack_formula_bytes
from sdk.datachip.execution_host import execute_verified_formula
from sdk.datachip.execution_rights import (
    active_execute_passport, issue_execution_grant, verify_execution_right,
    sign_revocation_from_authority, ExecutionDenied,
)

spec=importlib.util.spec_from_file_location("entity_true_passport",
    ROOT/"src"/"36_Adoption_Layer"/"rights_passport.py"
    if (ROOT/"src"/"36_Adoption_Layer"/"rights_passport.py").is_file()
    else ROOT/"src"/"rights_passport_reference.py")
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)

class SyntheticIdentity:
    def load_manifest(self,controller):
        if controller!="issuer.entity":raise PermissionError("unrecognized controller")
        return {"id":controller}
    def sign(self,controller,body):
        msg=json.dumps(body,sort_keys=True,separators=(",",":")).encode()
        return {"digest":hashlib.sha256(controller.encode()+msg).hexdigest()}
    def verify_signature(self,manifest,body,signature):
        return signature==self.sign(manifest["id"],body)

def key_bytes(private):
    return private.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)

class GenuineRegistryExecuteTests(unittest.TestCase):
    def setUp(self):
        ctx=tempfile.TemporaryDirectory(prefix="entity-execute-real-registry-")
        self.addCleanup(ctx.cleanup)
        self.root=Path(ctx.name)
        self.registry=module.RightsPassportRegistry(self.root,SyntheticIdentity())
        self.passport=self.registry.issue("issuer.entity","object:lab-01",
            [{"effect":"ALLOW","actions":["DATAPLANE:EXECUTE"]}],version="1.0")
        self.issuer=Ed25519PrivateKey.generate()
        self.revoker=Ed25519PrivateKey.generate()
        self.issuer_keys={"issuer.ex.01":key_bytes(self.issuer)}
        self.rev_keys={"revoker.ex.01":key_bytes(self.revoker)}
        self.now=int(time.time())
        self.chip_id="edc:formula:sha256:"+"a"*64
        self.content="b"*64
        self.assembly="c"*64
        self.issue_params=dict(registry=self.registry,passport_id=self.passport["passport_id"],
            object_id="object:lab-01",controller_id="issuer.entity",
            chip_id=self.chip_id,content_sha256=self.content,
            assembly_sha256=self.assembly,subject="lab.user",
            audience="fabric.lab",device_id="lab.device.win",
            authority_key_id="issuer.ex.01",grant_id="grant:lab-01",
            now=self.now,valid_seconds=600,
            controller_authorization=lambda **x: x.get("action")=="dataplane:execute",
            authorized_signer=self.issuer.sign,pinned_issuer_keys=self.issuer_keys)
        self.grant=issue_execution_grant(**self.issue_params)
        self.status={"complete":True,"sequence":5,
            "covered_rights_keys":["issuer.ex.01"],"revoked_rights_keys":[],
            "revoked_passport_ids":[],"revoked_grant_ids":[]}
        self.revocation=sign_revocation_from_authority(
            key_id="revoker.ex.01",sequence=5,now=self.now-5,valid_seconds=600,
            authoritative_status=lambda **_:self.status,
            authorized_signer=self.revoker.sign,pinned_revocation_keys=self.rev_keys)
        self.check=dict(grant=self.grant,snapshot=self.revocation,
            pinned_issuer_keys=self.issuer_keys,pinned_revocation_keys=self.rev_keys,
            subject="lab.user",audience="fabric.lab",device_id="lab.device.win",
            chip_id=self.chip_id,content_sha256=self.content,assembly_sha256=self.assembly,
            license_entitlement=lambda **x: x.get("action")=="dataplane:execute",
            device_identity=lambda **x: x.get("device_id")=="lab.device.win",
            protected_min_sequence=5,now=self.now,
            expected_passport_sha256=self.passport["passport_sha256"])
    def test_actual_signed_passport_and_execution_grant(self):
        result=verify_execution_right(**self.check)
        self.assertTrue(result["execution_right_verified"])
        self.assertFalse(result["export_right_verified"])
        self.assertFalse(result["production_ready"])
    def test_live_sqlite_status_after_passport_superseded(self):
        newer=self.registry.issue("issuer.entity","object:lab-01",
            [{"effect":"ALLOW","actions":["DATAPLANE:EXECUTE"]}],version="2.0")
        self.registry.supersede("issuer.entity",self.passport["passport_id"],newer["passport_id"])
        with self.assertRaises(ExecutionDenied):issue_execution_grant(**self.issue_params)
    def test_ambiguous_active_passport_denied(self):
        self.registry.issue("issuer.entity","object:lab-01",
            [{"effect":"ALLOW","actions":["DATAPLANE:EXECUTE"]}],version="2.0")
        with self.assertRaises(ExecutionDenied):issue_execution_grant(**self.issue_params)
    def test_export_only_not_execute(self):
        p=self.registry.issue("issuer.entity","object:export-only",
            [{"effect":"ALLOW","actions":["EXPORT"]}],version="1.0")
        with self.assertRaises(ExecutionDenied):active_execute_passport(self.registry,p["passport_id"],
            object_id="object:export-only",controller_id="issuer.entity")
    def test_prohibit_overrides_allow(self):
        p=self.registry.issue("issuer.entity","object:prohibit",
            [{"effect":"ALLOW","actions":["EXECUTE"]},
             {"effect":"PROHIBIT","actions":["EXECUTE"]}],version="1.0")
        with self.assertRaises(ExecutionDenied):active_execute_passport(self.registry,p["passport_id"],
            object_id="object:prohibit",controller_id="issuer.entity")
    def test_conditions_not_silently_granted(self):
        p=self.registry.issue("issuer.entity","object:conditional",
            [{"effect":"ALLOW","actions":["EXECUTE"],"conditions":{"jurisdiction":"CA-BC"}}],
            version="1.0")
        with self.assertRaises(ExecutionDenied):active_execute_passport(self.registry,p["passport_id"],
            object_id="object:conditional",controller_id="issuer.entity")
    def test_issuer_requires_controller_authentication(self):
        with self.assertRaises(ExecutionDenied):issue_execution_grant(
            **{**self.issue_params,"controller_authorization":lambda **_:False})
    def test_issuer_missing_key_denied(self):
        with self.assertRaises(ExecutionDenied):issue_execution_grant(
            **{**self.issue_params,"authorized_signer":None})
    def test_issuer_impostor_signing_denied(self):
        other=Ed25519PrivateKey.generate()
        with self.assertRaises(ExecutionDenied):issue_execution_grant(
            **{**self.issue_params,"authorized_signer":other.sign})
    def test_revocation_denies_grant(self):
        self.status["revoked_grant_ids"]=["grant:lab-01"]
        rev=sign_revocation_from_authority(
            key_id="revoker.ex.01",sequence=5,now=self.now-5,valid_seconds=600,
            authoritative_status=lambda **_:self.status,
            authorized_signer=self.revoker.sign,pinned_revocation_keys=self.rev_keys)
        with self.assertRaises(ExecutionDenied):verify_execution_right(**{**self.check,"snapshot":rev})
    def test_revocation_denies_passport(self):
        self.status["revoked_passport_ids"]=[self.passport["passport_id"]]
        rev=sign_revocation_from_authority(
            key_id="revoker.ex.01",sequence=5,now=self.now-5,valid_seconds=600,
            authoritative_status=lambda **_:self.status,
            authorized_signer=self.revoker.sign,pinned_revocation_keys=self.rev_keys)
        with self.assertRaises(ExecutionDenied):verify_execution_right(**{**self.check,"snapshot":rev})
    def test_revocation_denies_issuer(self):
        self.status["revoked_rights_keys"]=["issuer.ex.01"]
        rev=sign_revocation_from_authority(
            key_id="revoker.ex.01",sequence=5,now=self.now-5,valid_seconds=600,
            authoritative_status=lambda **_:self.status,
            authorized_signer=self.revoker.sign,pinned_revocation_keys=self.rev_keys)
        with self.assertRaises(ExecutionDenied):verify_execution_right(**{**self.check,"snapshot":rev})
    def test_revocation_checkpoint_rollback_denied(self):
        with self.assertRaises(ExecutionDenied):verify_execution_right(
            **{**self.check,"protected_min_sequence":6})
    def test_license_independently_denies(self):
        with self.assertRaises(ExecutionDenied):verify_execution_right(
            **{**self.check,"license_entitlement":lambda **_:False})
    def test_device_independently_denies(self):
        with self.assertRaises(ExecutionDenied):verify_execution_right(
            **{**self.check,"device_identity":lambda **_:False})
    def test_no_device_callback_denied(self):
        with self.assertRaises(ExecutionDenied):verify_execution_right(
            **{**self.check,"device_identity":None})
    def test_wrong_assembly_denied(self):
        with self.assertRaises(ExecutionDenied):verify_execution_right(
            **{**self.check,"assembly_sha256":"f"*64})
    def test_export_grant_envelope_denied(self):
        export_claim={"body":{"schema":"entity-edc-signed-rights-grant-v0.2"},"signature":"00"*64}
        with self.assertRaises(ExecutionDenied):verify_execution_right(
            **{**self.check,"grant":export_claim})
    def test_unsupported_grant_expiry(self):
        with self.assertRaises(ExecutionDenied):issue_execution_grant(
            **{**self.issue_params,"valid_seconds":901})
    def test_signed_revocation_requires_complete_external_ledger(self):
        with self.assertRaises(ExecutionDenied):sign_revocation_from_authority(
            key_id="revoker.ex.01",sequence=6,now=self.now,valid_seconds=600,
            authoritative_status=lambda **_:{ "complete":False,"sequence":6},
            authorized_signer=self.revoker.sign,pinned_revocation_keys=self.rev_keys)

    def _host_case(self,payload=b"BTG FABRIC VERIFIED EXECUTION"):
        file=self.root/"real.edcf"
        receipt=pack_formula_bytes(payload,file)
        self.issue_params["chip_id"]=receipt["chip_id"]
        self.issue_params["content_sha256"]=hashlib.sha256(payload).hexdigest()
        real_grant=issue_execution_grant(**self.issue_params)
        kw=dict(path=file,
            expected_archive_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
            expected_assembly_sha256=self.assembly,
            grant=real_grant,revocations=self.revocation,
            trusted_issuer_keys=self.issuer_keys,
            trusted_revocation_keys=self.rev_keys,
            authenticated_subject="lab.user",
            authenticated_audience="fabric.lab",
            authenticated_device="lab.device.win",
            licensed_entitlement=lambda **_:True,
            device_attestation=lambda **_:True,
            trusted_revocation_checkpoint=5,now=self.now)
        return kw,hashlib.sha256(payload.upper()).hexdigest()

    def test_genuine_formula_executes_without_export(self):
        kw,expected=self._host_case()
        result=execute_verified_formula(**kw)
        self.assertEqual(result["output_sha256"],expected)
        self.assertFalse(result["export_permission"])
        self.assertFalse(result["production_ready"])
    def test_genuine_formula_revoked_denied(self):
        kw,_=self._host_case()
        self.status["revoked_grant_ids"]=["grant:lab-01"]
        kw["revocations"]=sign_revocation_from_authority(
            key_id="revoker.ex.01",sequence=5,now=self.now-5,valid_seconds=600,
            authoritative_status=lambda **_:self.status,
            authorized_signer=self.revoker.sign,pinned_revocation_keys=self.rev_keys)
        with self.assertRaises(ExecutionDenied):execute_verified_formula(**kw)
    def test_genuine_formula_tamper_denied(self):
        kw,_=self._host_case()
        kw["path"].write_bytes(b"not an EDCF archive")
        with self.assertRaises(ExecutionDenied):execute_verified_formula(**kw)
    def test_genuine_formula_license_denied(self):
        kw,_=self._host_case()
        kw["licensed_entitlement"]=lambda **_:False
        with self.assertRaises(ExecutionDenied):execute_verified_formula(**kw)
    def test_genuine_formula_device_denied(self):
        kw,_=self._host_case()
        kw["device_attestation"]=lambda **_:False
        with self.assertRaises(ExecutionDenied):execute_verified_formula(**kw)
    def test_genuine_formula_operation_not_allowlisted(self):
        kw,_=self._host_case()
        kw["approved_operation"]="execute_python"
        with self.assertRaises(ExecutionDenied):execute_verified_formula(**kw)
    def test_genuine_formula_non_ascii_rejected(self):
        kw,_=self._host_case(payload=b"\xff \xfe")
        with self.assertRaises(ExecutionDenied):execute_verified_formula(**kw)
    def test_genuine_formula_archive_identity_bound(self):
        kw,_=self._host_case()
        kw["expected_archive_sha256"]="0"*64
        with self.assertRaises(ExecutionDenied):execute_verified_formula(**kw)

if __name__=="__main__":
    unittest.main(verbosity=2)
