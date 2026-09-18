from __future__ import annotations
from pathlib import Path
import json, time

STATES={'NORMAL','LOCAL_ONLY','PARTIALLY_REACHABLE','RELAY_REQUIRED','DEGRADED','OFFLINE',
        'RESOLUTION_CONFLICT','STALE_STATE','PROVIDER_UNAVAILABLE','RECOVERY','COMPROMISED_NODE'}

ALLOWED={
 'NORMAL':STATES-{'NORMAL'},
 'LOCAL_ONLY':{'NORMAL','PARTIALLY_REACHABLE','OFFLINE','PROVIDER_UNAVAILABLE','RECOVERY'},
 'PARTIALLY_REACHABLE':{'NORMAL','LOCAL_ONLY','RELAY_REQUIRED','DEGRADED','OFFLINE','PROVIDER_UNAVAILABLE'},
 'RELAY_REQUIRED':{'NORMAL','PARTIALLY_REACHABLE','DEGRADED','OFFLINE','PROVIDER_UNAVAILABLE'},
 'DEGRADED':{'NORMAL','PARTIALLY_REACHABLE','RELAY_REQUIRED','OFFLINE','RECOVERY','COMPROMISED_NODE'},
 'OFFLINE':{'LOCAL_ONLY','PARTIALLY_REACHABLE','NORMAL','RECOVERY','PROVIDER_UNAVAILABLE'},
 'RESOLUTION_CONFLICT':{'NORMAL','STALE_STATE','DEGRADED'},
 'STALE_STATE':{'NORMAL','RESOLUTION_CONFLICT','RECOVERY'},
 'PROVIDER_UNAVAILABLE':{'LOCAL_ONLY','PARTIALLY_REACHABLE','OFFLINE','RECOVERY','NORMAL'},
 'RECOVERY':{'NORMAL','LOCAL_ONLY','DEGRADED'},
 'COMPROMISED_NODE':{'RECOVERY','DEGRADED','NORMAL'},
}

class DomainFailureStateMachine:
    def __init__(self,state_dir,domain_id):
        self.path=Path(state_dir)/'sovereign_domain'/f'{domain_id}.failure_state.json'
        self.path.parent.mkdir(parents=True,exist_ok=True); self.domain_id=str(domain_id)
        if not self.path.exists(): self._write({'domain_id':self.domain_id,'state':'NORMAL','history':[]})
    def _read(self): return json.loads(self.path.read_text(encoding='utf-8'))
    def _write(self,data): self.path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    def transition(self,new_state,reason,*,evidence=None):
        new=str(new_state).upper()
        if new not in STATES: raise ValueError('unknown domain failure state')
        data=self._read(); old=data['state']
        if new!=old and new not in ALLOWED.get(old,set()): raise RuntimeError(f'illegal transition {old}->{new}')
        event={'from':old,'to':new,'reason':str(reason),'evidence':dict(evidence or {}),
               'at_ms':int(time.time()*1000),'entity_or_name_reassigned':False,'economic_state_mutated':False}
        data['state']=new; data['history'].append(event); self._write(data); return event
    def current(self): return self._read()['state']
    def history(self): return list(self._read().get('history') or [])
    def status(self):
        data=self._read(); return {'ready':True,'domain_id':self.domain_id,'state':data['state'],
            'events':len(data.get('history') or []),'outage_reassigns_identity':False,
            'infrastructure_failure_mutates_economic_rights':False,'states':sorted(STATES)}
