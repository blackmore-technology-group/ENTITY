from pathlib import Path
import importlib.util, json, sys
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

@pytest.fixture
def projection(tmp_path):
    mod=load("v2_projection",ROOT/"01_Core_Runtime"/"information_projection"/"canonical_projection.py")
    return mod.InformationProjectionEngine(tmp_path/"state")

@pytest.fixture
def evidence():
    return load("v2_evidence",ROOT/"04_Entity_Registry"/"evidence_assertions"/"canonical_evidence.py")


def base_request(**changes):
    req={"requesting_subsystem":"NIKI","actor":"agent-1","purpose":"explain","target":"local-model",
         "classification":"PRIVATE","requested_fields":["name","summary"],"minimum_fields":["summary"],
         "capability":{"metadata_read":True,"content_read":True},
         "policy":{"external_disclosure_allowed":False,"rights_authorized":True,"consent_authorized":True},
         "external_transmission":False,"content_requested":True,"authority_refs":["cap-1","pol-1"]}
    req.update(changes); return req

def test_projection_enforces_minimum_fields_without_logging_raw_content(projection):
    out=projection.decide(base_request(),{"name":"Alice","summary":"Allowed","secret":"never"})
    assert out["decision"]["outcome"]=="ALLOW"
    assert out["projection"]=={"summary":"Allowed"}
    assert out["decision"]["raw_sensitive_content_logged"] is False
    assert out["decision"]["disclosed_fields"]==["summary"]


def test_metadata_permission_does_not_escalate_to_content(projection):
    req=base_request(capability={"metadata_read":True,"content_read":False})
    out=projection.decide(req,{"summary":"private"})
    assert out["decision"]["outcome"]=="DENY"
    assert out["decision"]["reason"]=="metadata_permission_does_not_grant_content"
    assert out["projection"]=={}


def test_restricted_external_disclosure_fails_closed(projection):
    req=base_request(classification="RESTRICTED",external_transmission=True,
                     policy={"external_disclosure_allowed":True,"rights_authorized":True,"consent_authorized":True})
    out=projection.decide(req,{"summary":"sensitive"})
    assert out["decision"]["outcome"]=="DENY"


def test_unknown_rights_requires_review(projection):
    req=base_request(policy={"external_disclosure_allowed":False,"rights_authorized":None,"consent_authorized":True})
    assert projection.decide(req,{"summary":"x"})["decision"]["outcome"]=="REVIEW_REQUIRED"

def test_evidence_unknown_and_inference_cannot_overstate_verification(evidence):
    with pytest.raises(ValueError):
        evidence.EvidenceAssertionFactory.create("x",claimant="ent",evidence_origin="UNKNOWN",verification_level="VERIFIED")
    with pytest.raises(ValueError):
        evidence.EvidenceAssertionFactory.create("x",claimant="ent",evidence_origin="DERIVED_INFERENCE",verification_level="VERIFIED")
    inferred=evidence.EvidenceAssertionFactory.create("likely",claimant="ent",evidence_origin="DERIVED_INFERENCE",confidence=.7)
    assert evidence.EvidenceAssertionFactory.display_label(inferred)=="INFERRED"


def test_evidence_transition_requires_qualifying_origin(evidence):
    original=evidence.EvidenceAssertionFactory.create("creator claim",claimant="ent",evidence_origin="ENTITY_ASSERTION",verification_level="SELF_ASSERTED")
    with pytest.raises(ValueError):
        evidence.EvidenceAssertionFactory.transition(original,verification_level="VERIFIED",evidence_origin="DERIVED_INFERENCE",evidence_reference="model-output")
    verified=evidence.EvidenceAssertionFactory.transition(original,verification_level="VERIFIED",evidence_origin="EXTERNAL_AUTHORITATIVE_RECORD",evidence_reference="registry-42")
    assert verified["verification_level"]=="VERIFIED" and verified["supersedes"]==original["claim_id"]


def test_rights_ontology_contains_full_v2_required_vocabulary():
    ontology=json.loads((ROOT/"04_Entity_Registry"/"rights_ontology"/"ENTITY_RIGHTS_ONTOLOGY_v1.json").read_text(encoding="utf-8"))
    required={"AUTHOR","CREATOR","COPYRIGHT_CLAIMANT","COPYRIGHT_OWNER","CONTROLLER","CUSTODIAN","PERSONAL_DATA_SUBJECT","DEPICTED_PERSON","TRADEMARK_INTEREST","PATENT_INTEREST","CONFIDENTIALITY_INTEREST","LICENSEE","LICENSOR","ROYALTY_PARTICIPANT","COLLECTIVE_OWNER","GUARDIAN","ESTATE","PLATFORM_LICENSE_HOLDER","AUTHORIZED_AGENT"}
    assert required.issubset(set(ontology["stakeholder_right_types"]))
    assert set(ontology["verification_states"]).isdisjoint(set(ontology["dispute_states"]))

def test_rights_ontology_runtime_loader_validates_vocabulary():
    mod=load("v2_ontology",ROOT/"04_Entity_Registry"/"rights_ontology"/"canonical_ontology.py")
    ontology=mod.RightsOntology()
    assert ontology.validate_right_type("copyright_owner")=="COPYRIGHT_OWNER"
    assert ontology.status()["state_separation"] is True
    with pytest.raises(ValueError): ontology.validate_right_type("MAGICAL_OWNER")
