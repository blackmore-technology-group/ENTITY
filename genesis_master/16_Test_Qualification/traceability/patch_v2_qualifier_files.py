from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\ten_of_ten\qualify_v2_assurance_core.py")
s=p.read_text(encoding="utf-8")
old=' ROOT/"04_Entity_Registry"/"rights_ontology"/"ENTITY_RIGHTS_ONTOLOGY_v1.json",\n ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py",'
new=' ROOT/"04_Entity_Registry"/"rights_ontology"/"ENTITY_RIGHTS_ONTOLOGY_v1.json",\n ROOT/"04_Entity_Registry"/"rights_ontology"/"canonical_ontology.py",\n ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py",'
if old not in s: raise SystemExit("qualifier FILES target not found")
p.write_text(s.replace(old,new),encoding="utf-8")
