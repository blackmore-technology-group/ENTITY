from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\recovery\test_phase1_full_destructive_sovereignty.py")
s=p.read_text(encoding="utf-8")
s=s.replace('policy=polm.PolicyConsentEngine(state,ids); p=policy.create_policy(grantor,"Phase1",{"VIEW":"PERMIT","AI_TRAINING":"PROHIBIT"})','policy=polm.PolicyConsentEngine(state,ids); p=policy.create_policy(grantor,"Phase1",{"VIEW":"PERMIT","AI_TRAINING":"PROHIBIT"}); consent=policy.grant_consent(grantor,p["policy_id"],purpose="research",asset_scope=["phase1-scope"],counterparty_entity_id=licensee)')
s=s.replace('assert policy2.evaluate(p["policy_id"],"VIEW")["allowed"] is True','assert policy2.evaluate(p["policy_id"],"VIEW")["allowed"] is True; assert policy2.authorize_consent(consent["consent_id"],counterparty_entity_id=licensee,purpose="research",asset_scope=["phase1-scope"],action="VIEW")["allowed"] is True')
p.write_text(s,encoding="utf-8")
print("patched",p)
