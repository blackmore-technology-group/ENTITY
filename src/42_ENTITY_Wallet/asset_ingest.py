from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, shutil, time

INGEST_SCHEMA="entity-wallet-asset-ingest-v1"

def sha256_file(path:str|Path,chunk_size:int=1024*1024)->str:
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        while True:
            block=f.read(chunk_size)
            if not block: break
            h.update(block)
    return h.hexdigest()

class WalletAssetIngestor:
    """Create a Digital Commodity Object from user-selected data.

    Ingest is deliberately asset-first. It registers the asset and optional local
    custody copy, but never creates an EEP instrument, listing, price or licence.
    """
    def __init__(self,state_dir:str|Path,fabric):
        self.state=Path(state_dir)
        self.fabric=fabric
        self.vault=self.state/"wallet"/"asset_vault"
        self.vault.mkdir(parents=True,exist_ok=True)

    def ingest_file(self,controller_entity_id:str,file_path:str|Path,*,title:str|None=None,
                    commodity_class:str="DATA",measurement_unit:str="USE",
                    authority_basis:str="CREATOR_CONTROLLED",metadata:dict|None=None,
                    copy_to_local_vault:bool=True)->dict:
        source=Path(file_path).expanduser().resolve()
        if not source.is_file(): raise FileNotFoundError(str(source))
        digest=sha256_file(source)
        size=source.stat().st_size
        meta={
            "wallet_ingest_schema":INGEST_SCHEMA,
            "source_filename":source.name,
            "size_bytes":size,
            "authority_basis":str(authority_basis).upper(),
            "controller_asserted_registration_authority":True,
            "market_instruments_created_automatically":False,
            "market_value_created_by_ingest":False,
            **dict(metadata or {}),
        }
        obj=self.fabric.register_digital_commodity(
            controller_entity_id,
            str(title or source.name),
            digest,
            commodity_class=str(commodity_class).upper(),
            measurement_unit=str(measurement_unit).upper(),
            metadata=meta,
        )
        custody=None
        if copy_to_local_vault:
            target_dir=self.vault/obj["object_id"]
            target_dir.mkdir(parents=True,exist_ok=False)
            target=target_dir/source.name
            shutil.copy2(source,target)
            receipt={
                "schema":INGEST_SCHEMA,
                "object_id":obj["object_id"],
                "controller_entity_id":controller_entity_id,
                "title":str(title or source.name),
                "content_sha256":digest,
                "size_bytes":size,
                "source_filename":source.name,
                "custody":"LOCAL_WALLET_VAULT",
                "market_instruments_created":False,
                "created_at_ms":int(time.time()*1000),
            }
            (target_dir/"INGEST_RECEIPT.json").write_text(
                json.dumps(receipt,indent=2,sort_keys=True),encoding="utf-8")
            custody={"mode":"LOCAL_WALLET_VAULT","path":str(target),
                     "receipt_path":str(target_dir/"INGEST_RECEIPT.json")}
        return {
            "schema":INGEST_SCHEMA,
            "digital_asset":obj,
            "content_sha256":digest,
            "size_bytes":size,
            "custody":custody,
            "market_instruments_created":False,
            "listing_created":False,
            "price_created":False,
        }
