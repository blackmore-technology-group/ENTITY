from __future__ import annotations
from pathlib import Path
from threading import RLock
from contextlib import contextmanager
import fnmatch, json, sqlite3, time, uuid

SOURCE_MODES = {"OFF", "OBSERVE", "INDEX", "PROVENANCE", "MANAGED"}

# Hard safety boundary. Matching is case-insensitive and applies before enrollment policy.
DEFAULT_NEVER_TOUCH = [
    "*/windows/*", "*/system32/*", "*/programdata/microsoft/credentials/*",
    "*/appdata/local/microsoft/credentials/*", "*/appdata/roaming/microsoft/credentials/*",
    "*/appdata/local/google/chrome/user data/*/login data*",
    "*/appdata/local/microsoft/edge/user data/*/login data*",
    "*/secrets/*", "*/pki/*", "*/private_keys/*", "*/credentials/*",
    "*.pfx", "*.p12", "*.jks", "*.keystore", "*.key",
]


def _now() -> int:
    return int(time.time() * 1000)


def _norm(path: str | Path) -> str:
    return str(Path(path).resolve()).replace("\\", "/").lower()


class DataSourceGateway:
    """Default-deny source enrollment and least-privilege data access policy."""
    def __init__(self, state_dir: str | Path):
        self.root = Path(state_dir) / "data_source_gateway"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "sources.sqlite"
        self._lock = RLock()
        self._init_db()
    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS sources(source_id TEXT PRIMARY KEY, controller_entity_id TEXT NOT NULL, root_path TEXT NOT NULL UNIQUE, mode TEXT NOT NULL, discovery_allowed INTEGER NOT NULL, content_allowed INTEGER NOT NULL, economic_allowed INTEGER NOT NULL, niki_content_allowed INTEGER NOT NULL, default_classification TEXT NOT NULL, default_licensable INTEGER NOT NULL, created_at_ms INTEGER NOT NULL, updated_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS exclusions(exclusion_id TEXT PRIMARY KEY, source_id TEXT, pattern TEXT NOT NULL, reason TEXT NOT NULL, hard INTEGER NOT NULL, created_at_ms INTEGER NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_source_controller ON sources(controller_entity_id)")
            count = db.execute("SELECT COUNT(*) FROM exclusions WHERE hard=1 AND source_id IS NULL").fetchone()[0]
            if not count:
                now = _now()
                for pattern in DEFAULT_NEVER_TOUCH:
                    db.execute("INSERT INTO exclusions(exclusion_id,source_id,pattern,reason,hard,created_at_ms) VALUES(?,?,?,?,?,?)", ("exc1-"+uuid.uuid4().hex,None,pattern,"default never-touch boundary",1,now))

    @staticmethod
    def _mode_ceiling(mode: str) -> dict:
        mode = str(mode or "OFF").upper()
        if mode not in SOURCE_MODES:
            raise ValueError(f"unsupported source mode: {mode}")
        return {
            "OFF": {"discover":False,"content":False,"provenance":False,"managed":False},
            "OBSERVE": {"discover":True,"content":False,"provenance":False,"managed":False},
            "INDEX": {"discover":True,"content":True,"provenance":False,"managed":False},
            "PROVENANCE": {"discover":True,"content":True,"provenance":True,"managed":False},
            "MANAGED": {"discover":True,"content":True,"provenance":True,"managed":True},
        }[mode]
    def enroll_source(self, controller_entity_id: str, root_path: str | Path, *, mode: str,
                      discovery_allowed: bool = True, content_allowed: bool = False,
                      economic_allowed: bool = False, niki_content_allowed: bool = False,
                      default_classification: str = "PRIVATE",
                      default_licensable: bool = False) -> dict:
        resolved = Path(root_path).resolve()
        ceiling = self._mode_ceiling(mode)
        mode = str(mode).upper()
        if not resolved.exists():
            raise FileNotFoundError(str(resolved))
        if discovery_allowed and not ceiling["discover"]:
            raise PermissionError("source mode does not permit discovery")
        if content_allowed and not ceiling["content"]:
            raise PermissionError("source mode does not permit content access")
        if niki_content_allowed and not content_allowed:
            raise PermissionError("NIKI content access requires content permission")
        if economic_allowed and mode != "MANAGED":
            raise PermissionError("economic rights require MANAGED mode")
        if default_licensable and not economic_allowed:
            raise PermissionError("licensable default requires explicit economic permission")
        source_id = "src1-" + uuid.uuid4().hex
        now = _now()
        with self._lock, self._connect() as db:
            db.execute("INSERT INTO sources(source_id,controller_entity_id,root_path,mode,discovery_allowed,content_allowed,economic_allowed,niki_content_allowed,default_classification,default_licensable,created_at_ms,updated_at_ms) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(root_path) DO UPDATE SET controller_entity_id=excluded.controller_entity_id,mode=excluded.mode,discovery_allowed=excluded.discovery_allowed,content_allowed=excluded.content_allowed,economic_allowed=excluded.economic_allowed,niki_content_allowed=excluded.niki_content_allowed,default_classification=excluded.default_classification,default_licensable=excluded.default_licensable,updated_at_ms=excluded.updated_at_ms", (source_id,controller_entity_id,str(resolved),mode,int(discovery_allowed),int(content_allowed),int(economic_allowed),int(niki_content_allowed),str(default_classification).upper()[:32],int(default_licensable),now,now))
            row = db.execute("SELECT * FROM sources WHERE root_path=?", (str(resolved),)).fetchone()
        return self._view(row)

    @staticmethod
    def _view(row) -> dict:
        out = dict(row)
        for key in ("discovery_allowed","content_allowed","economic_allowed","niki_content_allowed","default_licensable"):
            out[key] = bool(out[key])
        return out
    def add_exclusion(self, pattern: str, *, source_id: str | None = None,
                      reason: str = "owner exclusion", hard: bool = False) -> dict:
        pattern = str(pattern or "").strip().lower().replace("\\", "/")
        if not pattern:
            raise ValueError("exclusion pattern required")
        exclusion_id = "exc1-" + uuid.uuid4().hex
        with self._connect() as db:
            if source_id and not db.execute("SELECT 1 FROM sources WHERE source_id=?", (source_id,)).fetchone():
                raise KeyError("source not found")
            db.execute("INSERT INTO exclusions(exclusion_id,source_id,pattern,reason,hard,created_at_ms) VALUES(?,?,?,?,?,?)", (exclusion_id,source_id,pattern,str(reason)[:512],int(hard),_now()))
        return {"exclusion_id":exclusion_id,"source_id":source_id,"pattern":pattern,"reason":reason,"hard":bool(hard)}

    def list_sources(self, controller_entity_id: str | None = None) -> list[dict]:
        with self._connect() as db:
            if controller_entity_id:
                rows = db.execute("SELECT * FROM sources WHERE controller_entity_id=? ORDER BY root_path", (controller_entity_id,)).fetchall()
            else:
                rows = db.execute("SELECT * FROM sources ORDER BY root_path").fetchall()
        return [self._view(r) for r in rows]

    def _matching_source(self, path: Path):
        target = _norm(path)
        matches = []
        with self._connect() as db:
            for row in db.execute("SELECT * FROM sources WHERE mode!='OFF'").fetchall():
                root = _norm(row["root_path"])
                if target == root or target.startswith(root.rstrip("/") + "/"):
                    matches.append(row)
        if not matches:
            return None
        return max(matches, key=lambda r: len(_norm(r["root_path"])))

    def _excluded(self, path: Path, source_id: str | None) -> dict | None:
        target = _norm(path)
        with self._connect() as db:
            rows = db.execute("SELECT * FROM exclusions WHERE source_id IS NULL OR source_id=? ORDER BY hard DESC", (source_id,)).fetchall()
        for row in rows:
            pattern = str(row["pattern"]).lower()
            if fnmatch.fnmatch(target, pattern) or fnmatch.fnmatch(path.name.lower(), pattern):
                return dict(row)
        return None
    def assess_path(self, path: str | Path, *, purpose: str = "discover") -> dict:
        target = Path(path).resolve()
        source = self._matching_source(target)
        if not source:
            return {"allowed":False,"reason":"source_not_enrolled","path":str(target),"purpose":purpose}
        exclusion = self._excluded(target, source["source_id"])
        if exclusion:
            return {"allowed":False,"reason":"excluded","path":str(target),"purpose":purpose,"source_id":source["source_id"],"exclusion":{"pattern":exclusion["pattern"],"reason":exclusion["reason"],"hard":bool(exclusion["hard"])}}
        view = self._view(source)
        ceiling = self._mode_ceiling(view["mode"])
        purpose = str(purpose or "discover").lower()
        allowed = False
        if purpose in {"discover","metadata"}:
            allowed = view["discovery_allowed"] and ceiling["discover"]
        elif purpose in {"content","read"}:
            allowed = view["content_allowed"] and ceiling["content"]
        elif purpose in {"hash","provenance"}:
            allowed = view["content_allowed"] and ceiling["provenance"]
        elif purpose == "niki_content":
            allowed = view["niki_content_allowed"] and view["content_allowed"] and ceiling["content"]
        elif purpose in {"economic","license","market"}:
            allowed = view["economic_allowed"] and ceiling["managed"]
        return {"allowed":bool(allowed),"reason":"policy","path":str(target),"purpose":purpose,"source":view}

    def roots_for_provenance(self, controller_entity_id: str) -> list[Path]:
        roots=[]
        for source in self.list_sources(controller_entity_id):
            if self._mode_ceiling(source["mode"])["provenance"] and source["content_allowed"]:
                roots.append(Path(source["root_path"]))
        return roots

    def status(self) -> dict:
        sources = self.list_sources()
        return {
            "ready":True,
            "default_deny":True,
            "source_count":len(sources),
            "modes":sorted(SOURCE_MODES),
            "permissions_independent":["discovery","content","economic","niki_content"],
            "new_data_default":"PRIVATE_NON_LICENSABLE",
            "never_touch_boundary":True,
            "database":str(self.path),
        }
