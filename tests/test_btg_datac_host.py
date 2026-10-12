from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sdk.datachip.application import sign_bundle,SCHEMA
from sdk.datachip.formula_chip import pack_formula_bytes
from sdk.datachip.host import resolve_host_application
from sdk.datachip.rights import issue_grant,issue_revocation_snapshot


def pub(key):
    return key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)


class DataChipNativeHostTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.chipfile=self.root/"trail.edcf"
        self.chip=pack_formula_bytes(b"SYNTHETIC BC TRAILS. NOT FOR FIELD NAVIGATION."*300,
                                     self.chipfile)
        self.filehash=hashlib.sha256(self.chipfile.read_bytes()).hexdigest()
        self.signer=Ed25519PrivateKey.generate()
        self.granter=Ed25519PrivateKey.generate()
        self.status=Ed25519PrivateKey.generate()
        self.releasekeys={"release":pub(self.signer)}
        self.rightskeys={"rights-delegated":pub(self.granter)}
        self.statuskeys={"revocation":pub(self.status)}
        self.now=1791820000
        self.snapshot=issue_revocation_snapshot(self.status,
            authority_key_id="revocation",issued_at=self.now-60,
            valid_until=self.now+1200,
            covered_rights_keys=("rights-delegated",))
        self.grant=issue_grant(self.granter,authority_key_id="rights-delegated",
            chip_id=self.chip["chip_id"],subject="authorized-user",
            audience="HuntAR",rights_passport_ref="rp:synthetic:field",
            not_before=self.now-60,expires_at=self.now+1200)
        self.body={"schema":SCHEMA,"app_id":"HuntAR","release_id":"test-001",
            "signer_id":"release","host_abi":1,"platforms":["ios","android","windows"],
            "modules":[{"name":"trails","kind":"geographic",
                        "chip_id":self.chip["chip_id"],"sha256":self.filehash,
                        "requires":[],"data_right":"grant-required"}]}

    def resolve(self,**kw):
        arg=dict(signed_bundle=sign_bundle(self.signer,self.body),
                 app_id="HuntAR",platform="ios",
                 trusted_bundle_keys=self.releasekeys,
                 chip_paths={self.chip["chip_id"]:self.chipfile},
                 authenticated_subject="authorized-user",
                 rights_grants={self.chip["chip_id"]:self.grant},
                 revocation_snapshots={self.chip["chip_id"]:self.snapshot},
                 pinned_rights_keys=self.rightskeys,
                 pinned_revocation_keys=self.statuskeys,
                 now=self.now)
        arg.update(kw)
        return resolve_host_application(**arg)

    def test_signed_bundle_and_delegated_right_both_required(self):
        result=self.resolve()
        self.assertTrue(result["signed_bundle_verified"])
        self.assertEqual(result["module_names_available_for_use"],["trails"])
        self.assertEqual(result["delegated_grants_verified"][0]["grant_id"],
                         self.grant["body"]["grant_id"])
        self.assertFalse(result["native_permissions_granted"])
        self.assertTrue(result["all_exports_require_use_time_authorization"])

    def test_shared_chip_does_not_transfer_rights_across_apps(self):
        other_body={**self.body,"app_id":"HikeAR"}
        with self.assertRaises(PermissionError):
            self.resolve(signed_bundle=sign_bundle(self.signer,other_body),
                         app_id="HikeAR")

    def test_missing_grant_fails_closed(self):
        with self.assertRaises(PermissionError):
            self.resolve(rights_grants={})

    def test_stale_revocation_fails_closed(self):
        with self.assertRaises(PermissionError):
            self.resolve(now=self.now+1300)

    def test_wrong_authenticated_user_fails_closed(self):
        with self.assertRaises(PermissionError):
            self.resolve(authenticated_subject="other-user")

    def test_status_must_cover_grant_authority(self):
        other=issue_revocation_snapshot(self.status,authority_key_id="revocation",
             issued_at=self.now-60,valid_until=self.now+1200,
             covered_rights_keys=("a-different-issuer",))
        with self.assertRaises(PermissionError):
            self.resolve(revocation_snapshots={self.chip["chip_id"]:other})

    def test_corrupt_chip_fails_before_rights_validation(self):
        corrupted=self.root/"tampered.edcf"
        corrupted.write_bytes(self.chipfile.read_bytes()+b"x")
        with self.assertRaises(ValueError):
            self.resolve(chip_paths={self.chip["chip_id"]:corrupted})


if __name__=="__main__":
    unittest.main()
