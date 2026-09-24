from __future__ import annotations

PROFILE_ALIASES={
    "global":"entity-profile:global@1.0","healthcare":"entity-profile:healthcare@1.0","finance":"entity-profile:finance@1.0",
    "manufacturing":"entity-profile:manufacturing@1.0","ai":"entity-profile:ai@1.0","robotics":"entity-profile:robotics@1.0",
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
                      previous_object_id:str|None=None,version:str="1.0")->dict:
        stack=self.compose_profiles(*profiles)
        result=self.ingestion.ingest_file(path,controller_entity_id,stack["profile_refs"],logical_path=logical_path,
                                          previous_object_id=previous_object_id,version=version)
        return {"object_id":result["object"]["object_id"],"content_sha256":result["object"]["content_sha256"],
                "rights_passport_id":result["rights_passport"]["passport_id"],
                "global_passport_id":result["global_passport"]["passport_id"],
                "global_passport_sha256":result["global_passport"]["body_sha256"],
                "evidence_id":result["evidence"]["evidence_id"],"profile_refs":stack["profile_refs"],
                "custody_is_not_authority":True,"economic_value_invented":False}

    def package_plan(self,package:str,config:dict,asset_kind:str)->dict:
        if self.industry_packages is None: raise RuntimeError("industry package registry not configured")
        return self.industry_packages.deployment_plan(package,config,asset_kind)

    def map_external(self,package:str,standard:str,record:dict)->dict:
        if self.industry_packages is None: raise RuntimeError("industry package registry not configured")
        return self.industry_packages.map_external(package,standard,record)

    def ingest_package_file(self,path,controller_entity_id:str,package:str,config:dict,asset_kind:str,**kwargs)->dict:
        plan=self.package_plan(package,config,asset_kind)
        result=self.ingestion.ingest_file(path,controller_entity_id,plan["profile_refs"],
                                          rights_actions=plan["rights_actions"],**kwargs)
        return {"deployment_plan":plan,"object_id":result["object"]["object_id"],
                "global_passport_id":result["global_passport"]["passport_id"],
                "content_sha256":result["object"]["content_sha256"],"economic_value_invented":False}
    def verify_passport(self,passport_or_id)->dict:
        passport=self.passports.get(passport_or_id) if isinstance(passport_or_id,str) else passport_or_id
        return self.passports.verify(passport)

    @staticmethod
    def capability_status()->dict:
        return {"schema":"entity-v3-global-passport-sdk-status-v1","sdk_does_not_create_authority":True,
                "profile_is_not_regulatory_compliance":True,"external_standards_are_mapped_not_redefined":True,
                "continuous_provenance_supported":True,"industry_packages_supported":True,
                "developer_configures_not_redesigns":True,"built_in_profile_aliases":sorted(PROFILE_ALIASES)}
