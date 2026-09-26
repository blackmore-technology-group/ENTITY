from pathlib import Path
import sys
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
RUNTIME=ROOT/"10_NIKI"/"sovereign_adapted"/"Blackmore_Central_Intelligence_Advanced_NIKI_ADAM_BSIE_v0.6.1_AR_INTELLIGENCE_COMPLETE"/"central_runtime"
sys.path.insert(0,str(RUNTIME))
from blackmore_ci.entity_platform_bindings import EntityPlatformBindingResolver
from blackmore_ci.system_completion_matrix import EntitySystemCompletionMatrix
r=EntityPlatformBindingResolver(ROOT)
m,q=EntitySystemCompletionMatrix(r).write(ROOT/"10_NIKI"/"ENTITY_SYSTEM_COMPLETION_MATRIX.json",ROOT/"10_NIKI"/"ENTITY_CANONICAL_READY_QUEUE.json")
print(m["canonical_ready_count"],m["authority_count"])
print([x["authority"] for x in m["authorities"] if x["canonical_ready"]])
