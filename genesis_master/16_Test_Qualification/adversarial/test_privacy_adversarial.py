from pathlib import Path
import importlib.util, sys
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
RUNTIME=ROOT/"10_NIKI"/"sovereign_adapted"/"Blackmore_Central_Intelligence_Advanced_NIKI_ADAM_BSIE_v0.6.1_AR_INTELLIGENCE_COMPLETE"/"central_runtime"
sys.path.insert(0,str(RUNTIME))

from blackmore_ci.data_source_gateway import DataSourceGateway
from blackmore_ci.entity_context_adapter import EntityContextProjectionAdapter
from blackmore_ci.niki_disclosure_guard import NikiDisclosureGuard
from blackmore_ci.event_projection import _safe_metadata


def _identity_module():
    path=ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py"
    spec=importlib.util.spec_from_file_location("privacy_identity",path)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class _World:
    def context(self,*args,**kwargs):
        return {"entity_id":"ent-public","local_path":"D:/private/file.txt","nested":{"secret":"nope","ok":"yes"}}

class _Data:
    def summary(self,*args,**kwargs):
        return {"asset_count":1,"vault_locator":"vault://secret","raw_content":"private body"}


def test_sources_are_default_deny_and_never_touch_wins(tmp_path):
    root=tmp_path/"source"; root.mkdir(); normal=root/"note.txt"; normal.write_text("ok")
    secret=root/"root.key"; secret.write_text("private")
    gateway=DataSourceGateway(tmp_path/"state")
    assert gateway.assess_path(normal,purpose="content")["allowed"] is False
    source=gateway.enroll_source("ent-test",root,mode="PROVENANCE",discovery_allowed=True,content_allowed=True,niki_content_allowed=False)
    assert gateway.assess_path(normal,purpose="content")["allowed"] is True
    assert gateway.assess_path(normal,purpose="niki_content")["allowed"] is False
    blocked=gateway.assess_path(secret,purpose="content")
    assert blocked["allowed"] is False and blocked["reason"]=="excluded" and blocked["exclusion"]["hard"] is True
    assert source["default_licensable"] is False


def test_external_sensitive_disclosure_fails_closed():
    guard=NikiDisclosureGuard()
    denied=guard.evaluate(ai_permissions=["AI_CONTENT_READ","AI_REASON_OVER"],classification="RESTRICTED",
        provider="EXTERNAL_LLM",purpose="analysis",external_disclosure_policy="UNKNOWN",
        content_requested=True,projection={"summary":"private"})
    assert denied["decision"]=="DENY" and denied["projection"]=={} and denied["mutation_authority"] is False
    allowed=guard.evaluate(ai_permissions=["AI_CONTENT_READ","AI_REASON_OVER","AI_DISCLOSE"],classification="RESTRICTED",
        provider="EXTERNAL_LLM",purpose="analysis",external_disclosure_policy="ALLOW",
        content_requested=True,projection={"summary":"minimum"})
    assert allowed["decision"]=="ALLOW" and allowed["projection"]=={"summary":"minimum"}


def test_niki_projection_is_metadata_only_and_recursively_redacts():
    adapter=EntityContextProjectionAdapter(_World(),_Data())
    with pytest.raises(PermissionError): adapter.project("ent-public",ai_permissions=set())
    projection=adapter.project("ent-public",ai_permissions={"AI_METADATA_READ"},metadata={"request_asset_content":True})
    text=repr(projection)
    assert "D:/private/file.txt" not in text and "private body" not in text and "vault://secret" not in text
    assert projection["raw_content_included"] is False and projection["vault_content_accessed"] is False
    assert projection["content_request"]["supplied"] is False


def test_pairwise_identifier_does_not_expose_root_identifier(tmp_path):
    mod=_identity_module(); identity=mod.EntityIdentityVault(tmp_path/"state")
    entity_id=identity.create("Privacy Entity","person")["entity_id"]
    a=identity.pairwise_id(entity_id,"peer-a"); b=identity.pairwise_id(entity_id,"peer-b")
    assert a!=b and entity_id not in a and entity_id not in b
    assert identity.pairwise_id(entity_id,"peer-a")==a


def test_shared_event_metadata_removes_sensitive_fields_recursively():
    safe=_safe_metadata({"purpose":"audit","content":"raw","local_path":"D:/secret.txt",
        "nested":{"token":"abc","ok":7},"items":[{"private_key":"x","kept":"yes"}],"blob":b"123"})
    rendered=repr(safe)
    for forbidden in ("raw","D:/secret.txt","abc","private_key"):
        assert forbidden not in rendered
    assert safe["nested"]["ok"]==7 and safe["items"][0]["kept"]=="yes" and safe["blob"]=="<binary-redacted>"
