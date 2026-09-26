from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\HUNT_AR\HuntAR_v4.3.0\mobile\android\app\build.gradle.kts")
s=p.read_text(encoding="utf-8")
anchor='        buildConfigField("boolean", "BSIE_COMMISSIONING_INCLUDED", "true")\n'
insert='''        buildConfigField("String", "ENTITY_APPLICATION_ALIAS", "\\\"huntar.entity\\\"")\n        buildConfigField("String", "ENTITY_APPLICATION_ID", "\\\"ent2-vkesuqie2o5ldzvon6zro2c5rilor4u6x5lsqrrsw5ypxni73qba\\\"")\n        buildConfigField("String", "ENTITY_BTG_ID", "\\\"ent2-kkov66eoh23h3zgr4pe4njsbkayn2kxad6vfyirqvuqrty52clpa\\\"")\n        buildConfigField("String", "ENTITY_PLATFORM_ID", "\\\"ent2-m3nofxtv3zwldhwuonw3h67hqjh2zambrhj4kaaulncpt4amkcua\\\"")\n        buildConfigField("String", "ENTITY_SDK_PROFILE", "\\\"ENTITY_OPEN_SDK_v1.1\\\"")\n'''
if anchor not in s: raise SystemExit("gradle anchor not found")
s=s.replace(anchor,anchor+insert,1)
p.write_text(s,encoding="utf-8")
print("HUNTAR gradle patched")
