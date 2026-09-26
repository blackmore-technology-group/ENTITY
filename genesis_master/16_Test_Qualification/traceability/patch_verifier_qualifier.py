from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\ten_of_ten\qualify_independent_verifier.py")
s=p.read_text(encoding="utf-8")
s=s.replace('TESTS=[ROOT/"16_Test_Qualification"/"unit"/"test_independent_verifier.py",ROOT/"16_Test_Qualification"/"corporate_capital"/"test_section170_corporate_capital_golden.py"]','TESTS=[ROOT/"16_Test_Qualification"/"unit"/"test_independent_verifier.py",ROOT/"16_Test_Qualification"/"unit"/"test_independent_verifier_licence_usage.py",ROOT/"16_Test_Qualification"/"corporate_capital"/"test_section170_corporate_capital_golden.py"]')
p.write_text(s,encoding="utf-8")
print("patched",p)
