"""Experimental BTG DataChip native-host authorization planning.

Only returns a validated resource plan, never opens hardware, exports content,
runs code or alters application binaries. Host supplies independently authenticated
subject and pin sets; a signed EDC grant is not a full ENTITY Rights Passport.
"""
from __future__ import annotations
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .application import verify_bundle
from .rights import verify_grant


def resolve_host_application(signed_bundle: dict[str,Any], *,
                             app_id:str, platform:str,
                             trusted_bundle_keys:Mapping[str,bytes],
                             chip_paths:Mapping[str,str|Path],
                             authenticated_subject:str,
                             rights_grants:Mapping[str,dict[str,Any]],
                             revocation_snapshots:Mapping[str,dict[str,Any]],
                             pinned_rights_keys:Mapping[str,bytes],
                             pinned_revocation_keys:Mapping[str,bytes],
                             now:int) -> dict[str,Any]:
    """Independently check signed bundle, DataChip integrity and each gated right.

    Only a session/context independently established by the *native* host should
    supply authenticated_subject. Calling with an arbitrary string does not
    authenticate an end user. No automatic fallback to data-only permission.
    """
    result=verify_bundle(signed_bundle,
                         trusted_bundle_keys=trusted_bundle_keys,
                         expected_app=app_id,expected_platform=platform,
                         available_chips=chip_paths)
    modules=result["modules"]
    ready=list(result["available_public_modules"])
    gated=[]
    for name in result["rights_locked_modules"]:
        cid=modules[name]["chip_id"]
        if cid not in rights_grants or cid not in revocation_snapshots:
            raise PermissionError("missing current delegated rights proof for "+name)
        grant=rights_grants[cid]
        status=revocation_snapshots[cid]
        verified=verify_grant(grant,status,
                     pinned_rights_keys=pinned_rights_keys,
                     pinned_revocation_keys=pinned_revocation_keys,
                     trusted_subject=authenticated_subject,
                     trusted_audience=app_id,
                     expected_chip_id=cid,
                     now=now)
        gated.append({"name":name,"grant_id":verified["grant_id"],
                      "rights_passport_ref":verified["rights_passport_ref"],
                      "valid_until":verified["valid_until"]})
        ready.append(name)
    # Authorization is scoped to this verification result. An actual read/export
    # must re-check entitlement, revocation/time and resource digest at use-time.
    return {"schema":"btg-datac-host-resource-plan-v0.1",
            "app_id":app_id,"platform":platform,
            "release_id":result["release_id"],
            "signed_bundle_verified":True,
            "modules_in_dependency_order":result["module_order"],
            "module_names_available_for_use":ready,
            "delegated_grants_verified":gated,
            "rights_passport_state_independently_synced":False,
            "native_permissions_granted":False,
            "all_exports_require_use_time_authorization":True}
