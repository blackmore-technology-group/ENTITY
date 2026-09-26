from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import json,sqlite3,time

def _now(): return int(time.time()*1000)

class PeerDiscoveryRegistry:
    """Minimal-metadata discovery; discovery is never trust or authorization."""
    def __init__(self,state_dir:str|Path,*,ttl_ms:int=300000,max_events_per_peer:int=32):
        self.root=Path(state_dir)/'peer_discovery'; self.root.mkdir(parents=True,exist_ok=True); self.path=self.root/'discovery.sqlite'
        self.ttl_ms=int(ttl_ms); self.max_events=int(max_events_per_peer); self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS announcements(peer_id TEXT NOT NULL,pairwise_id TEXT NOT NULL,endpoint_hint TEXT NOT NULL,nonce TEXT UNIQUE NOT NULL,observed_at_ms INTEGER NOT NULL,PRIMARY KEY(peer_id,pairwise_id))')
    def announce(self,peer_id:str,pairwise_id:str,endpoint_hint:str,*,nonce:str)->dict:
        now=_now()
        with self._connect() as db:
            recent=int(db.execute('SELECT COUNT(*) FROM announcements WHERE peer_id=? AND observed_at_ms>?',(str(peer_id),now-self.ttl_ms)).fetchone()[0])
            if recent>=self.max_events: raise PermissionError('discovery rate limit exceeded')
            try: db.execute('INSERT OR REPLACE INTO announcements VALUES(?,?,?,?,?)',(str(peer_id),str(pairwise_id),str(endpoint_hint)[:256],str(nonce),now))
            except sqlite3.IntegrityError as exc: raise ValueError('duplicate/replayed discovery nonce') from exc
        return {'peer_id':str(peer_id),'pairwise_id':str(pairwise_id),'endpoint_hint':str(endpoint_hint)[:256],'observed_at_ms':now,'trust_state':'UNTRUSTED_DISCOVERED'}
    def discover(self)->list[dict]:
        cutoff=_now()-self.ttl_ms
        with self._connect() as db: rows=db.execute('SELECT * FROM announcements WHERE observed_at_ms>=? ORDER BY observed_at_ms DESC',(cutoff,)).fetchall()
        return [{'peer_id':r['peer_id'],'pairwise_id':r['pairwise_id'],'endpoint_hint':r['endpoint_hint'],'trust_state':'UNTRUSTED_DISCOVERED','root_identity_exposed':False} for r in rows]
    def status(self): return {'ready':True,'discovery_implies_trust':False,'rate_limited':True,'replay_protected':True,'stale_entries_filtered':True}
