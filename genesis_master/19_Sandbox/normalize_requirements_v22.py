from pathlib import Path
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network')
changed=[]
for p in ROOT.glob('[0-1][0-9]_*\\ENTITY_REQUIREMENTS.md'):
    if p.parts[-2]=='10_NIKI': continue
    text=p.read_text(encoding='utf-8')
    lines=text.splitlines()
    for i,line in enumerate(lines):
        if line.startswith('Source: SERS-ENTITY-'):
            lines[i]='Source: SERS-ENTITY-003 Complete Master Engineering Design v2.2'
            break
    new='\n'.join(lines)+'\n'
    if new!=text:
        p.write_text(new,encoding='utf-8'); changed.append(str(p))
print('\n'.join(changed)); print('CHANGED',len(changed))
