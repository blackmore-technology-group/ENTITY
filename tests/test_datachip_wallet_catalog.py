import importlib.util
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def loaded(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

CAT=loaded("catalog_test","src/42_ENTITY_Wallet/datachip_catalog.py")
GRAPH=loaded("catalog_graph_test","src/42_ENTITY_Wallet/datachip_graph.py")
OWNER="ent2-test-wallet"

def sample():
    return {"wallet":{"owner_entity_id":OWNER},"assets":[{
        "object_id":"obj3-fixture-123",
        "controller_entity_id":OWNER,
        "status":"ACTIVE",
        "title":"Boundary Terrain",
        "content_sha256":"a"*64,
        "object_type":"GEO_DATA",
        "commodity_class":"TERRAIN",
        "descriptor":{"digital_commodity":True}
    }]}

class DataChipWalletCatalogTests(unittest.TestCase):
    def test_valid_reference_does_not_gain_authority(self):
        record=CAT.owned_dco_catalog(sample(),OWNER)[0]
        interface=CAT.interface_for_dco(record)
        self.assertEqual(interface["outputs"][0]["type"],"entity.asset.reference")
        graph=GRAPH.Graph(OWNER)
        graph.add(graph.register(interface))
        plan=graph.compile()
        self.assertFalse(plan["security"]["execution_enabled"])
        self.assertFalse(plan["security"]["rights_authorized"])
        self.assertFalse(record["content_chip_verified"])

    def test_other_owner_fails(self):
        data=sample()
        data["wallet"]["owner_entity_id"]="ent2-other"
        with self.assertRaises(CAT.CatalogError):
            CAT.owned_dco_catalog(data,OWNER)

    def test_mixed_controller_fails(self):
        data=sample()
        data["assets"][0]["controller_entity_id"]="ent2-other"
        with self.assertRaises(CAT.CatalogError):
            CAT.owned_dco_catalog(data,OWNER)

    def test_inactive_asset_fails(self):
        data=sample()
        data["assets"][0]["status"]="REVOKED"
        with self.assertRaises(CAT.CatalogError):
            CAT.owned_dco_catalog(data,OWNER)

    def test_invalid_digest_fails(self):
        data=sample()
        data["assets"][0]["content_sha256"]="corrupted"
        with self.assertRaises(CAT.CatalogError):
            CAT.owned_dco_catalog(data,OWNER)

    def test_duplicate_object_fails(self):
        data=sample()
        data["assets"].append(dict(data["assets"][0]))
        with self.assertRaises(CAT.CatalogError):
            CAT.owned_dco_catalog(data,OWNER)

    def test_catalogue_reference_is_not_edcf(self):
        asset=CAT.owned_dco_catalog(sample(),OWNER)[0]
        graph=GRAPH.Graph(OWNER)
        a=graph.add(graph.register(CAT.interface_for_dco(asset)))
        b=graph.add("entity.geo.decode")
        with self.assertRaises(GRAPH.ComposerError):
            graph.connect(a,"asset_ref",b,"content")
