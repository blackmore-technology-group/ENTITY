from __future__ import annotations
from copy import deepcopy
from typing import Any
import hashlib, json

PACKAGE_VERSION="1.0"
GLOBAL_PROFILE="entity-profile:global@1.0"

def _sha(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def _mapping(standard:str,fields:dict[str,str])->dict:
    return {"standard":standard,"mapping_version":"1.0","field_map":dict(fields),
            "normative_equivalence_claimed":False,"external_standard_not_redefined":True}

COMMON_DEFAULTS={
    "fail_closed":True,
    "custody_is_not_authority":True,
    "evidence_does_not_establish_objective_truth":True,
    "profile_is_not_regulatory_compliance":True,
    "economic_value_invented":False,
    "developer_configures_not_redesigns":True,
}

PACKAGE_SPECS={
    "healthcare":{
        "profile_refs":[GLOBAL_PROFILE,"entity-profile:healthcare@1.0"],
        "required_config":["organization","jurisdiction","authority_source","privacy_policy"],
        "object_types":{"clinical_dataset":"DATASET","clinical_document":"DOCUMENT","diagnostic_model":"MODEL","medical_device":"DEVICE"},
        "rights":["INSPECT","READ","DERIVE"],
        "evidence_types":["DOCUMENT","REGISTRY_RECORD"],
        "mappings":[_mapping("HL7-FHIR",{"resourceType":"descriptor.fhir_resource_type","id":"descriptor.external_id","meta.versionId":"descriptor.external_version"}),
                    _mapping("DICOM",{"SOPInstanceUID":"descriptor.dicom_sop_instance_uid","StudyInstanceUID":"descriptor.dicom_study_instance_uid","Modality":"descriptor.modality"})],
        "privacy":{"default":"RESTRICTED_DISCLOSURE","minimum_data":True,"purpose_bound":True},
    },
    "finance":{
        "profile_refs":[GLOBAL_PROFILE,"entity-profile:finance@1.0"],
        "required_config":["organization","jurisdiction","authority_source","settlement_policy"],
        "object_types":{"instrument":"FINANCIAL_INSTRUMENT","trade_record":"DOCUMENT","settlement_record":"DOCUMENT","market_dataset":"DATASET"},
        "rights":["INSPECT","READ","DERIVE","COMMERCIALIZE"],
        "evidence_types":["PAYMENT_RECORD","REGISTRY_RECORD","DOCUMENT"],
        "mappings":[_mapping("ISO-20022",{"MsgId":"descriptor.message_id","CreDtTm":"descriptor.created_at","TxId":"descriptor.transaction_id"}),
                    _mapping("FIX",{"11":"descriptor.cl_ord_id","17":"descriptor.exec_id","55":"descriptor.symbol"}),
                    _mapping("LEI",{"lei":"descriptor.legal_entity_identifier"})],
        "privacy":{"default":"SELECTIVE_DISCLOSURE","minimum_data":True,"purpose_bound":True},
    },
    "manufacturing":{
        "profile_refs":[GLOBAL_PROFILE,"entity-profile:manufacturing@1.0"],
        "required_config":["organization","jurisdiction","authority_source","asset_namespace"],
        "object_types":{"machine":"PHYSICAL_ASSET","digital_twin":"DIGITAL_TWIN","firmware":"SOFTWARE","telemetry":"DATASET","maintenance_record":"DOCUMENT"},
        "rights":["INSPECT","READ","DERIVE","CONTROL"],
        "evidence_types":["SENSOR_OBSERVATION","DOCUMENT"],
        "mappings":[_mapping("OPC-UA",{"NodeId":"descriptor.opcua_node_id","BrowseName":"descriptor.opcua_browse_name","DataType":"descriptor.opcua_data_type"}),
                    _mapping("ASSET-ADMINISTRATION-SHELL",{"id":"descriptor.aas_id","idShort":"descriptor.aas_id_short","assetInformation.globalAssetId":"descriptor.global_asset_id"})],
        "privacy":{"default":"RESTRICTED_DISCLOSURE","minimum_data":True,"purpose_bound":True},
    },
    "ai":{
        "profile_refs":[GLOBAL_PROFILE,"entity-profile:ai@1.0"],
        "required_config":["organization","jurisdiction","authority_source","model_governance_policy"],
        "object_types":{"training_dataset":"DATASET","corpus":"DATASET","model":"MODEL","weights":"MODEL","evaluation":"DOCUMENT","agent":"AI_AGENT","output":"DOCUMENT"},
        "rights":["INSPECT","READ","DERIVE","TRAIN","INFER","EXECUTE"],
        "evidence_types":["DOCUMENT","REGISTRY_RECORD","OTHER"],
        "mappings":[_mapping("SPDX-3",{"name":"descriptor.component_name","version":"descriptor.component_version","license":"descriptor.license_expression"}),
                    _mapping("CYCLONEDX",{"bom-ref":"descriptor.bom_ref","name":"descriptor.component_name","version":"descriptor.component_version"}),
                    _mapping("NIST-AI-RMF",{"risk_category":"descriptor.risk_category","control":"descriptor.control_ref"})],
        "privacy":{"default":"SELECTIVE_DISCLOSURE","minimum_data":True,"purpose_bound":True},
    },
    "robotics":{
        "profile_refs":[GLOBAL_PROFILE,"entity-profile:robotics@1.0"],
        "required_config":["organization","jurisdiction","authority_source","safety_policy"],
        "object_types":{"robot":"DEVICE","controller":"DEVICE","model":"MODEL","software":"SOFTWARE","telemetry":"DATASET","action_record":"DOCUMENT"},
        "rights":["INSPECT","READ","INFER","EXECUTE","CONTROL"],
        "evidence_types":["SENSOR_OBSERVATION","DOCUMENT","OTHER"],
        "mappings":[_mapping("ROS-2",{"topic":"descriptor.ros_topic","type":"descriptor.ros_type","node":"descriptor.ros_node"}),
                    _mapping("OPEN-RMF",{"fleet_name":"descriptor.rmf_fleet","robot_name":"descriptor.rmf_robot","task_id":"descriptor.rmf_task"})],
        "privacy":{"default":"RESTRICTED_DISCLOSURE","minimum_data":True,"purpose_bound":True},
    },
    "defence-public":{
        "profile_refs":[GLOBAL_PROFILE,"entity-profile:defence-public@1.0"],
        "required_config":["organization","jurisdiction","authority_source","release_policy"],
        "object_types":{"public_asset":"PHYSICAL_ASSET","public_dataset":"DATASET","software":"SOFTWARE","device":"DEVICE","model":"MODEL","custody_record":"DOCUMENT"},
        "rights":["INSPECT","READ","DERIVE"],
        "evidence_types":["DOCUMENT","REGISTRY_RECORD"],
        "mappings":[_mapping("PUBLIC-DATA-GOVERNANCE",{"asset_id":"descriptor.public_asset_id","release":"descriptor.release_status","originator":"descriptor.originator_ref"}),
                    _mapping("ORIGINATOR-CONTROL",{"originator":"descriptor.originator_ref","dissemination":"descriptor.dissemination_rule"})],
        "privacy":{"default":"RESTRICTED_DISCLOSURE","minimum_data":True,"purpose_bound":True,"classified_material_prohibited":True},
    },
}

class IndustryImplementationPackageRegistry:
    """Executable industry package semantics layered on the one ENTITY Global Passport."""
    def list_packages(self)->list[str]: return sorted(PACKAGE_SPECS)
    def get(self,name:str)->dict:
        key=str(name).lower()
        if key not in PACKAGE_SPECS: raise KeyError("industry package missing")
        spec=deepcopy(PACKAGE_SPECS[key]); spec["name"]=key; spec["version"]=PACKAGE_VERSION
        spec["package_sha256"]=_sha(spec); spec.update(COMMON_DEFAULTS)
        return spec

    def validate_configuration(self,name:str,config:dict)->dict:
        spec=self.get(name); cfg=dict(config or {})
        missing=[k for k in spec["required_config"] if not str(cfg.get(k) or "").strip()]
        if missing: raise ValueError("missing configuration: "+",".join(missing))
        if name=="defence-public" and str(cfg.get("classification","")).upper() not in {"","PUBLIC","UNCLASSIFIED"}:
            raise ValueError("defence-public package cannot ingest classified material")
        return {"valid":True,"package":name,"configuration_sha256":_sha(cfg),"profile_refs":spec["profile_refs"],
                "configuration_does_not_create_authority":True,"legal_compliance_not_implied":True}
    def template(self,name:str,asset_kind:str)->dict:
        spec=self.get(name); kind=str(asset_kind)
        if kind not in spec["object_types"]: raise ValueError("unsupported package asset kind")
        return {"schema":"entity-v3-industry-asset-template-v1","package":name,"package_version":spec["version"],
                "asset_kind":kind,"object_type":spec["object_types"][kind],"profile_refs":spec["profile_refs"],
                "default_right_actions":spec["rights"],"required_evidence_types":spec["evidence_types"],
                "privacy_defaults":spec["privacy"],"economic_value_invented":False,"profile_is_not_authority":True}

    def map_external(self,name:str,standard:str,record:dict)->dict:
        spec=self.get(name); mapping=next((m for m in spec["mappings"] if m["standard"].upper()==str(standard).upper()),None)
        if not mapping: raise ValueError("standard mapping unavailable")
        source=dict(record or {}); descriptor={}
        for external,target in mapping["field_map"].items():
            current:Any=source
            for part in external.split("."):
                if not isinstance(current,dict) or part not in current: current=None; break
                current=current[part]
            if current is not None: descriptor[target.removeprefix("descriptor.")]=current
        return {"schema":"entity-v3-industry-mapping-result-v1","package":name,"standard":mapping["standard"],
                "mapping_version":mapping["mapping_version"],"descriptor":descriptor,"source_sha256":_sha(source),
                "normative_equivalence_claimed":False,"external_standard_not_redefined":True}

    def deployment_plan(self,name:str,config:dict,asset_kind:str)->dict:
        validated=self.validate_configuration(name,config); template=self.template(name,asset_kind); spec=self.get(name)
        return {"schema":"entity-v3-industry-deployment-plan-v1","package":name,"package_version":spec["version"],
                "configuration_sha256":validated["configuration_sha256"],"profile_refs":template["profile_refs"],
                "object_type":template["object_type"],"rights_actions":template["default_right_actions"],
                "evidence_types":template["required_evidence_types"],"privacy":template["privacy_defaults"],
                "steps":["validate_configuration","connect_source","ingest_content","issue_evidence","issue_rights_passport","issue_global_passport","verify_passport","run_conformance"],
                "developer_configures_not_redesigns":True,"core_semantics_changed":False,"legal_compliance_not_implied":True}
