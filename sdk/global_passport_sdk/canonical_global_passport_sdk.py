from __future__ import annotations

PROFILE_ALIASES={
    "global":"entity-profile:global@1.0","healthcare":"entity-profile:healthcare@1.0","finance":"entity-profile:finance@1.0",
    "manufacturing":"entity-profile:manufacturing@1.0","ai":"entity-profile:ai@1.0",
    "software":"entity-profile:software-engineering@1.0","software-engineering":"entity-profile:software-engineering@1.0",
    "engineering":"entity-profile:software-engineering@1.0","robotics":"entity-profile:robotics@1.0",
    "defence":"entity-profile:defence-public@1.0","defense":"entity-profile:defence-public@1.0",
}

class EntityGlobalPassportSDK:
    """Public v3.4 facade. SDK convenience never creates authority, truth or regulatory status."""
    def __init__(self,profile_registry,global_passports,continuous_ingestion,industry_packages=None):
        self.profiles=profile_registry
        self.passports=global_passports
        self.ingestion=continuous_ingestion
        self.industry_packages=industry_packages

    @staticmethod
    def profile_ref(name:str)->str:
        key=str(name).strip().lower()
        if key not in PROFILE_ALIASES: raise KeyError("unknown built-in profile alias")
        return PROFILE_ALIASES[key]

    def compose_profiles(self,*names_or_refs:str)->dict:
        refs=[]
        if not any(str(x).startswith("entity-profile:global@") or str(x).lower()=="global" for x in names_or_refs):
            refs.append(PROFILE_ALIASES["global"])
        for item in names_or_refs:
            text=str(item); refs.append(text if text.startswith("entity-profile:") else self.profile_ref(text))
        return self.profiles.resolve_stack(refs)
    def register_file(self,path,controller_entity_id:str,*profiles:str,logical_path:str|None=None,
                      previous_object_id:str|None=None,version:str="1.0",btdu_binding:dict|None=None,**kwargs)->dict:
        stack=self.compose_profiles(*profiles)
        result=self.ingestion.ingest_file(path,controller_entity_id,stack["profile_refs"],logical_path=logical_path,
                                          previous_object_id=previous_object_id,version=version,btdu_binding=btdu_binding,**kwargs)
        return {"object_id":result["object"]["object_id"],"content_sha256":result["object"]["content_sha256"],
                "rights_passport_id":result["rights_passport"]["passport_id"],
                "global_passport_id":result["global_passport"]["passport_id"],
                "global_passport_sha256":result["global_passport"]["body_sha256"],
                "evidence_id":result["evidence"]["evidence_id"],"profile_refs":stack["profile_refs"],
                "protocol_origin":result["global_passport"].get("protocol_origin"),"btdu_binding":result["global_passport"].get("btdu_binding"),
                "custody_is_not_authority":True,"economic_value_invented":False}

    def package_plan(self,package:str,config:dict,asset_kind:str)->dict:
        if self.industry_packages is None: raise RuntimeError("industry package registry not configured")
        return self.industry_packages.deployment_plan(package,config,asset_kind)

    def map_external(self,package:str,standard:str,record:dict)->dict:
        if self.industry_packages is None: raise RuntimeError("industry package registry not configured")
        return self.industry_packages.map_external(package,standard,record)

    def ingest_package_file(self,path,controller_entity_id:str,package:str,config:dict,asset_kind:str,**kwargs)->dict:
        plan=self.package_plan(package,config,asset_kind)
        options=dict(kwargs)
        options.setdefault("object_type",plan["object_type"])
        extra_profiles=list(options.pop("additional_profile_refs",[]) or [])
        profile_stack=self.profiles.resolve_stack(list(plan["profile_refs"])+extra_profiles)
        extra_actions={str(x).upper() for x in (options.pop("additional_rights_actions",[]) or []) if str(x)}
        rights_actions=sorted(set(plan["rights_actions"])|extra_actions)
        context=dict(options.pop("industry_context",{}) or {})
        context.update({"industry_package":plan["package"],"asset_kind":str(asset_kind),
                        "configuration_sha256":plan["configuration_sha256"],
                        "primary_domain_profile":next((x for x in plan["profile_refs"] if "entity-profile:global@" not in x),None),
                        "associated_profile_refs":[x for x in profile_stack["profile_refs"] if x not in plan["profile_refs"]]})
        options["industry_context"]=context
        result=self.ingestion.ingest_file(path,controller_entity_id,profile_stack["profile_refs"],
                                          rights_actions=rights_actions,**options)
        return {"deployment_plan":plan,"object_id":result["object"]["object_id"],
                "global_passport_id":result["global_passport"]["passport_id"],
                "content_sha256":result["object"]["content_sha256"],
                "protocol_origin":result["global_passport"].get("protocol_origin"),"btdu_binding":result["global_passport"].get("btdu_binding"),"economic_value_invented":False}
    def verify_passport(self,passport_or_id)->dict:
        passport=self.passports.get(passport_or_id) if isinstance(passport_or_id,str) else passport_or_id
        return self.passports.verify(passport)

    @staticmethod
    def capability_status()->dict:
        return {"schema":"entity-v3-global-passport-sdk-status-v1","sdk_does_not_create_authority":True,
                "profile_is_not_regulatory_compliance":True,"external_standards_are_mapped_not_redefined":True,
                "continuous_provenance_supported":True,"industry_packages_supported":True,
                "protocol_origin_lineage_supported":True,"btdu_binding_supported":True,"user_asset_provenance_separate":True,
                "developer_configures_not_redesigns":True,"built_in_profile_aliases":sorted(PROFILE_ALIASES)}
