from pathlib import Path
p=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network\17_Release\ten_of_ten\evaluate_release.py')
s=p.read_text(encoding='utf-8')
old='''    passed=sum(1 for x in gates if x["pass"]); total=len(gates)\n    internal_gates=[x for x in gates if not x.get("external_only")]\n    internal_chaos_ready=all(x["pass"] for x in internal_gates)\n    rtm_path=ROOT/"16_Test_Qualification"/"traceability"/"MASTER_RTM.json"\n    rtm=load(rtm_path) or {}\n'''
new='''    rtm_path=ROOT/"16_Test_Qualification"/"traceability"/"MASTER_RTM.json"\n    rtm=load(rtm_path) or {}\n    rtm_ok=rtm.get("full_internal_requirements_closed") is True and rtm.get("active_internal_unclosed_count")==0 and rtm.get("state_counts",{}).get("QUALIFIED")==rtm.get("requirement_count")==1997 and rtm.get("master_source_mirrored") is True\n    gates.append(gate("master_rtm_closure",rtm_ok,"PASS" if rtm_ok else "rtm_not_fully_closed",str(rtm_path)))\n    passed=sum(1 for x in gates if x["pass"]); total=len(gates)\n    internal_gates=[x for x in gates if not x.get("external_only")]\n    internal_chaos_ready=all(x["pass"] for x in internal_gates)\n'''
assert old in s
p.write_text(s.replace(old,new),encoding='utf-8')
print('master RTM release gate added')