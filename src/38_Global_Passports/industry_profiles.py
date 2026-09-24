from __future__ import annotations
import hashlib, json

def _sha(name:str)->str: return hashlib.sha256(("ENTITY-v3.4-profile:"+name).encode()).hexdigest()
def _std(name:str,role:str="MAPPING")->dict: return {"standard":name,"role":role,"normative_equivalence_claimed":False}

BUILTIN_PROFILES={
"entity-profile:global@1.0":{"kind":"GLOBAL","standards":[],"parents":[],"objects":["DATASET","DOCUMENT","MODEL","SOFTWARE","DEVICE","FINANCIAL_INSTRUMENT","PHYSICAL_ASSET","OTHER"],"evidence":["DOCUMENT"]},
"entity-profile:healthcare@1.0":{"kind":"INDUSTRY","standards":[_std("HL7-FHIR"),_std("DICOM")],"parents":["entity-profile:global@1.0"],"objects":["DATASET","DOCUMENT","MODEL","DEVICE"],"evidence":["DOCUMENT","REGISTRY_RECORD"]},
"entity-profile:finance@1.0":{"kind":"INDUSTRY","standards":[_std("ISO-20022"),_std("FIX"),_std("LEI")],"parents":["entity-profile:global@1.0"],"objects":["FINANCIAL_INSTRUMENT","DOCUMENT","DATASET","SOFTWARE"],"evidence":["DOCUMENT","PAYMENT_RECORD","REGISTRY_RECORD"]},
"entity-profile:manufacturing@1.0":{"kind":"INDUSTRY","standards":[_std("OPC-UA"),_std("ASSET-ADMINISTRATION-SHELL")],"parents":["entity-profile:global@1.0"],"objects":["DEVICE","PHYSICAL_ASSET","DIGITAL_TWIN","DATASET","SOFTWARE"],"evidence":["SENSOR_OBSERVATION","DOCUMENT"]},
"entity-profile:ai@1.0":{"kind":"INDUSTRY","standards":[_std("NIST-AI-RMF"),_std("SPDX-3"),_std("CYCLONEDX")],"parents":["entity-profile:global@1.0"],"objects":["DATASET","MODEL","SOFTWARE","AI_AGENT","DOCUMENT"],"evidence":["DOCUMENT","OTHER","REGISTRY_RECORD"]},
"entity-profile:robotics@1.0":{"kind":"INDUSTRY","standards":[_std("ROS-2"),_std("OPEN-RMF")],"parents":["entity-profile:global@1.0"],"objects":["DEVICE","AI_AGENT","SOFTWARE","DATASET","PHYSICAL_ASSET"],"evidence":["SENSOR_OBSERVATION","OTHER","DOCUMENT"]},
"entity-profile:defence-public@1.0":{"kind":"INDUSTRY","standards":[_std("PUBLIC-DATA-GOVERNANCE"),_std("ORIGINATOR-CONTROL")],"parents":["entity-profile:global@1.0"],"objects":["DATASET","DOCUMENT","SOFTWARE","DEVICE","MODEL"],"evidence":["DOCUMENT","REGISTRY_RECORD"],"public_unclassified":True},
}

def definitions()->dict: return json.loads(json.dumps(BUILTIN_PROFILES))

def install_builtin_profiles(registry,issuer_entity_id:str)->dict:
    installed={}
    for ref,spec in BUILTIN_PROFILES.items():
        profile_id,version=ref.rsplit("@",1)
        policy={"industry_profile":profile_id.split(":")[-1],"technical_interoperability_not_regulatory_compliance":True,
                "external_standard_not_redefined":True,"profile_schema_version":"1.0"}
        p=registry.register(issuer_entity_id,profile_id,version,spec["kind"],schema_sha256=_sha(ref),
            standards=spec.get("standards"),parent_refs=spec.get("parents"),object_types=spec.get("objects"),
            required_evidence_types=spec.get("evidence"),policy=policy,public_unclassified=spec.get("public_unclassified",True))
        installed[ref]=p
    return installed
