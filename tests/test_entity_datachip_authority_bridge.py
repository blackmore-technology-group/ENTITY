"""Read-only real ENTITY RightsPassportRegistry wiring, synthetic keys and state."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sdk.datachip.authority_bridge import (
    inspect_active_passport, issue_authorized_datachip_grant,
)
from sdk.datachip.rights import public_key_bytes, issue_revocation_snapshot,verify_grant


class SyntheticIdentity:
    """Only for tests; production registry receives a real ENTITY identity."""
    def load_manifest(self, controller):
        if controller != "issuer.entity":
            raise PermissionError("unknown identity")
        return {"id":controller}
    def sign(self, controller, body):
        return {"digest":hashlib.sha256(
            controller.encode()+json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()}
    def verify_signature(self, manifest, body, signature):
        return signature==self.sign(manifest["id"],body)


def real_registry(root):
    path=ROOT/"src"/"36_Adoption_Layer"/"rights_passport.py"
    if not path.exists():
        path=ROOT/"production"/"rights_passport_reference.py"
    spec=importlib.util.spec_from_file_location("datachip_rights_registry",path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod.RightsPassportRegistry(root,SyntheticIdentity())


class AuthorityBridgeTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory(prefix="entity-rights-bridge-")
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        self.registry=real_registry(self.root)
        self.controller="issuer.entity"
        self.object="object:synthetic-004"
        self.rights=[{"effect":"ALLOW","actions":["EXPORT"],
                      "conditions":{},"obligations":[]}]
        self.passport=self.registry.issue(
            self.controller,self.object,self.rights,version="1.0")
        self.signer=Ed25519PrivateKey.generate()
        self.now=1791820000
        self.chip_id="edc:formula:sha256:"+"a"*64

    def inspect(self,pid=None):
        return inspect_active_passport(self.registry,pid or self.passport["passport_id"],
                                      expected_object_id=self.object,
                                      expected_controller=self.controller)

    def authorize(self,**changes):
        args=dict(registry=self.registry,
            passport_id=self.passport["passport_id"],
            object_id=self.object,
            controller_entity_id=self.controller,chip_id=self.chip_id,
            authenticated_subject="approved-user",audience="HuntAR",
            issuer_private_key=self.signer,
            issuer_key_id="issuer-key",now=self.now,
            authenticated_request_authorized=lambda **kw:
                kw["controller_entity_id"]=="issuer.entity"
                and kw["subject"]=="approved-user" and kw["app_id"]=="HuntAR")
        args.update(changes)
        return issue_authorized_datachip_grant(**args)

    def test_real_registry_issue_get_verify_and_readonly_bridge(self):
        record=self.inspect()
        self.assertTrue(record["active_verified"])
        self.assertEqual(record["passport_sha256"],self.passport["passport_sha256"])

    def test_issuer_only_mints_narrow_delegated_grant(self):
        grant=self.authorize()
        status_signer=Ed25519PrivateKey.generate()
        revocations=issue_revocation_snapshot(status_signer,
             authority_key_id="rev-key",issued_at=self.now-10,
             valid_until=self.now+900,covered_rights_keys=("issuer-key",))
        result=verify_grant(grant,revocations,
             pinned_rights_keys={"issuer-key":public_key_bytes(self.signer)},
             pinned_revocation_keys={"rev-key":public_key_bytes(status_signer)},
             trusted_subject="approved-user",trusted_audience="HuntAR",
             expected_chip_id=self.chip_id,now=self.now)
        self.assertTrue(result["issuer_signature_valid"])
        self.assertLessEqual(result["valid_until"],self.now+900)

    def test_subject_denied_without_authentication(self):
        with self.assertRaises(PermissionError):
            self.authorize(authenticated_request_authorized=None)
        with self.assertRaises(PermissionError):
            self.authorize(authenticated_request_authorized=lambda **kw:False)

    def test_mismatched_controller_or_object(self):
        with self.assertRaises(PermissionError):
            self.authorize(object_id="object:other")
        with self.assertRaises(PermissionError):
            self.authorize(controller_entity_id="someone.else")

    def test_status_supersession_prevents_grant(self):
        newer=self.registry.issue(self.controller,self.object,self.rights,version="2.0")
        self.registry.supersede(self.controller,self.passport["passport_id"],newer["passport_id"])
        with self.assertRaises(PermissionError):
            self.authorize()
        self.assertTrue(self.inspect(newer["passport_id"])["active_verified"])

    def test_ambiguous_multiple_active_versions_denied(self):
        self.registry.issue(self.controller,self.object,self.rights,version="2.0")
        with self.assertRaises(PermissionError):
            self.authorize()

    def test_prohibit_overrides_allow(self):
        self.registry.issue(self.controller,"object:blocked",
            [{"effect":"ALLOW","actions":["EXPORT"]},
             {"effect":"PROHIBIT","actions":["EXPORT"]}],version="1.0")
        with self.assertRaises(PermissionError):
            inspect_active_passport(self.registry,
                self.registry.path.with_name("no-passport.sqlite").name,
                expected_object_id="object:blocked",expected_controller=self.controller)
        # The actual blocked passport should fail even with a good signature.
        with __import__("sqlite3").connect(self.registry.path) as db:
            pid=db.execute("SELECT passport_id FROM passports WHERE object_id=?",("object:blocked",)).fetchone()[0]
        with self.assertRaises(PermissionError):
            inspect_active_passport(self.registry,pid,
                expected_object_id="object:blocked",expected_controller=self.controller)

    def test_conditions_not_silently_ignored(self):
        p=self.registry.issue(self.controller,"object:conditional",
            [{"effect":"ALLOW","actions":["EXPORT"],
              "conditions":{"jurisdiction":"CA-BC"}}],version="1.0")
        with self.assertRaises(PermissionError):
            inspect_active_passport(self.registry,p["passport_id"],
                expected_object_id="object:conditional",
                expected_controller=self.controller)

    def test_missing_registry_fails_closed(self):
        self.registry.path.unlink()
        with self.assertRaises((PermissionError,FileNotFoundError)):
            self.authorize()

    def test_expiry_grant_bound(self):
        with self.assertRaises(PermissionError):
            self.authorize(valid_seconds=901)

if __name__=="__main__":
    unittest.main()
