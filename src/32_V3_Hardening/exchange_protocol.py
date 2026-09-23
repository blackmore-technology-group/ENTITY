from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import hashlib, json, secrets, sqlite3, time

def now_ms(): return int(time.time()*1000)
def sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()).hexdigest()
def rid(prefix): return prefix+'-'+secrets.token_hex(12)
def require_sha256(v):
    if not isinstance(v,str) or v != v.lower() or len(v)!=64 or any(c not in '0123456789abcdef' for c in v):
        raise ValueError('canonical lowercase SHA-256 hex required')
    return v

def require_int(v,name,minimum=0):
    if type(v) is not int or v < minimum: raise ValueError(f'{name} must be an integer >= {minimum}')
    return v

def require_upper(v,name):
    if not isinstance(v,str) or not v or v != v.upper(): raise ValueError(f'{name} must be canonical uppercase text')
    return v

def require_id(v,name):
    if not isinstance(v,str) or not v: raise ValueError(f'{name} must be a non-empty string')
    return v

def validate_signed_wire(body):
    if type(body) is not dict:
        raise ValueError('signed record must be a JSON object')
    schema=body.get('schema')
    if type(schema) is not str:
        raise ValueError('signed record schema must be a string')
    def sid(name): require_id(body.get(name),name)
    def sint(name,minimum=0): require_int(body.get(name),name,minimum)
    def sup(name): require_upper(body.get(name),name)
    def sha256(name): require_sha256(body.get(name))
    common_time=lambda: sint('created_at_ms',0)
    if schema=='entity-eep-instrument-v1':
        for n in ('instrument_id','issuer','underlying_object_id'): sid(n)
        sup('instrument_class'); sup('settlement_currency'); sup('delivery_mode'); common_time(); sint('total_units',1)
        if type(body.get('transferable')) is not bool: raise ValueError('transferable must be boolean')
        d=body.get('duration_ms')
        if d is not None: require_int(d,'duration_ms',1)
        if body.get('status')!='ACTIVE' or body.get('bytes_are_not_the_traded_scarcity') is not True: raise ValueError('invalid instrument constants')
        rights=body.get('rights')
        if type(rights) is not dict: raise ValueError('rights must be an object')
        actions=rights.get('actions')
        if type(actions) is not list or not actions or any(type(a) is not str or not a or a!=a.upper() for a in actions): raise ValueError('rights.actions must be non-empty canonical uppercase strings')
        if actions!=sorted(set(actions)): raise ValueError('rights.actions must be sorted and unique')
    elif schema=='entity-eep-disclosure-v1':
        for n in ('disclosure_id','venue_id','instrument_id','publisher'): sid(n)
        sup('disclosure_type'); sha256('content_sha256'); common_time()
        if body.get('protected_data_included') is not False: raise ValueError('protected_data_included must be false')
    elif schema=='entity-eep-listing-v1':
        for n in ('listing_id','venue_id','instrument_id','lister'): sid(n)
        sint('min_lot',1); sint('tick_size',1); sha256('disclosure_sha256'); common_time()
        if body.get('status')!='ACTIVE': raise ValueError('listing status must be ACTIVE')
    elif schema=='entity-eep-order-v1':
        for n in ('order_id','venue_id','instrument_id','participant','nonce'): sid(n)
        sup('side'); sup('tif'); sint('quantity',1); sint('limit_price',0); common_time()
        if body['side'] not in {'BUY','SELL'} or body['tif'] not in {'GTC','IOC','DAY'}: raise ValueError('invalid canonical order enum')
    elif schema=='entity-eep-order-cancel-v1':
        for n in ('cancellation_id','order_id','participant','nonce'): sid(n)
        common_time()
    elif schema=='entity-eep-payment-attestation-v1':
        for n in ('attestation_id','trade_id','verifier_entity_id','settlement_ref','nonce'): sid(n)
        sha256('evidence_sha256'); common_time()
        if body.get('verification_is_attestation_not_absolute_truth') is not True: raise ValueError('payment attestation truth-boundary flag required')
    elif schema=='entity-eep-usage-v1':
        for n in ('usage_id','instrument_id','holder','nonce'): sid(n)
        sup('action'); sint('units',1); common_time()
    elif schema=='entity-eep-revenue-rule-set-v1':
        for n in ('rule_set_id','instrument_id','issuer','nonce'): sid(n)
        common_time(); allocations=body.get('allocations_bps')
        if type(allocations) is not dict: raise ValueError('allocations_bps must be an object')
        total=0
        for k,v in allocations.items():
            require_id(k,'allocation recipient'); require_int(v,f'allocation {k}',0); total+=v
        if total>10000: raise ValueError('revenue allocation exceeds 10000 bps')
    elif schema=='entity-eep-rfq-v1':
        for n in ('rfq_id','venue_id','instrument_id','requester','nonce'): sid(n)
        sup('side'); sint('quantity',1); sint('expires_at_ms',0); common_time()
        if body['side'] not in {'BUY','SELL'} or body['expires_at_ms']<=body['created_at_ms']: raise ValueError('invalid canonical RFQ')
    elif schema=='entity-eep-rfq-quote-v1':
        for n in ('quote_id','rfq_id','provider','nonce'): sid(n)
        sint('price',0); sint('expires_at_ms',0); common_time()
        if body['expires_at_ms']<=body['created_at_ms']: raise ValueError('quote expiry must follow creation')
    elif schema=='entity-eep-rfq-acceptance-v1':
        for n in ('acceptance_id','rfq_id','quote_id','requester','nonce'): sid(n)
        common_time()
    else:
        raise ValueError('unsupported signed EEP wire schema')
    return True

class ExchangeProtocol:
    EXECUTION_MODELS={'ORDER_BOOK','CALL_AUCTION','RFQ'}
    INSTRUMENT_CLASSES={'SPOT_LICENSE','SUBSCRIPTION','COMPUTE_TO_DATA','PROCUREMENT','CONTRIBUTION','SECONDARY_LICENSE'}
    SIDES={'BUY','SELL'}
    def __init__(self,root,identity,fabric):
        self.path=Path(root)/'entity_v3_exchange.sqlite'; self.identity=identity; self.fabric=fabric; self._init()
    @contextmanager
    def _db(self):
        db=sqlite3.connect(self.path); db.row_factory=sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback(); raise
        finally:
            db.close()
    def _init(self):
        with self._db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS venues(venue_id TEXT PRIMARY KEY,operator TEXT,name TEXT,jurisdiction TEXT,execution_models_json TEXT,policy_sha256 TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT);
            CREATE TABLE IF NOT EXISTS instruments(instrument_id TEXT PRIMARY KEY,issuer TEXT,underlying_object_id TEXT,instrument_class TEXT,rights_json TEXT,total_units INTEGER,transferable INTEGER,duration_ms INTEGER,settlement_currency TEXT,delivery_mode TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT);
            CREATE TABLE IF NOT EXISTS balances(instrument_id TEXT,holder TEXT,units INTEGER,PRIMARY KEY(instrument_id,holder));
            CREATE TABLE IF NOT EXISTS listings(listing_id TEXT PRIMARY KEY,venue_id TEXT,instrument_id TEXT,lister TEXT,min_lot INTEGER,tick_size INTEGER,disclosure_sha256 TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT);
            CREATE TABLE IF NOT EXISTS orders(order_id TEXT PRIMARY KEY,venue_id TEXT,instrument_id TEXT,participant TEXT,side TEXT,quantity INTEGER,remaining INTEGER,limit_price INTEGER,tif TEXT,status TEXT,nonce TEXT UNIQUE,created_at_ms INTEGER,received_at_ms INTEGER,signature_json TEXT);
            CREATE TABLE IF NOT EXISTS trades(trade_id TEXT PRIMARY KEY,venue_id TEXT,instrument_id TEXT,buy_order_id TEXT,sell_order_id TEXT,buyer TEXT,seller TEXT,quantity INTEGER,price INTEGER,execution_model TEXT,status TEXT,created_at_ms INTEGER);
            CREATE TABLE IF NOT EXISTS clearing(trade_id TEXT PRIMARY KEY,payer TEXT,payee TEXT,amount_units INTEGER,currency TEXT,status TEXT,payment_ref TEXT,external_verified INTEGER);
            CREATE TABLE IF NOT EXISTS entitlements(entitlement_id TEXT PRIMARY KEY,trade_id TEXT,instrument_id TEXT,holder TEXT,quantity INTEGER,rights_json TEXT,expires_at_ms INTEGER,created_at_ms INTEGER,signature_json TEXT);
            CREATE TABLE IF NOT EXISTS disclosures(disclosure_id TEXT PRIMARY KEY,venue_id TEXT,instrument_id TEXT,publisher TEXT,disclosure_type TEXT,content_sha256 TEXT,created_at_ms INTEGER,signature_json TEXT);
            CREATE TABLE IF NOT EXISTS usage(usage_id TEXT PRIMARY KEY,instrument_id TEXT,holder TEXT,action TEXT,units INTEGER,nonce TEXT UNIQUE,created_at_ms INTEGER,signature_json TEXT);
            CREATE TABLE IF NOT EXISTS revenue_rules(instrument_id TEXT,recipient TEXT,bps INTEGER,PRIMARY KEY(instrument_id,recipient));
            CREATE TABLE IF NOT EXISTS revenue_rule_sets(rule_set_id TEXT PRIMARY KEY,instrument_id TEXT NOT NULL,issuer TEXT NOT NULL,allocations_json TEXT NOT NULL,nonce TEXT NOT NULL UNIQUE,created_at_ms INTEGER NOT NULL,received_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS trade_revenue_bindings(trade_id TEXT PRIMARY KEY,instrument_id TEXT NOT NULL,rule_set_id TEXT,allocations_json TEXT NOT NULL,bound_at_ms INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS revenue_events(revenue_event_id TEXT PRIMARY KEY,trade_id TEXT,recipient TEXT,amount_units INTEGER,currency TEXT,created_at_ms INTEGER);
            CREATE TABLE IF NOT EXISTS surveillance(alert_id TEXT PRIMARY KEY,venue_id TEXT,instrument_id TEXT,participant TEXT,alert_type TEXT,evidence_json TEXT,created_at_ms INTEGER);
            CREATE TABLE IF NOT EXISTS rfqs(rfq_id TEXT PRIMARY KEY,venue_id TEXT,instrument_id TEXT,requester TEXT,side TEXT,quantity INTEGER,expires_at_ms INTEGER,status TEXT,created_at_ms INTEGER,nonce TEXT,received_at_ms INTEGER,signature_json TEXT);
            CREATE TABLE IF NOT EXISTS quotes(quote_id TEXT PRIMARY KEY,rfq_id TEXT,provider TEXT,price INTEGER,expires_at_ms INTEGER,status TEXT,created_at_ms INTEGER,nonce TEXT,received_at_ms INTEGER,signature_json TEXT);
            CREATE TABLE IF NOT EXISTS rfq_acceptances(acceptance_id TEXT PRIMARY KEY,rfq_id TEXT NOT NULL,quote_id TEXT NOT NULL,requester TEXT NOT NULL,nonce TEXT NOT NULL UNIQUE,created_at_ms INTEGER NOT NULL,received_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS order_cancellations(cancellation_id TEXT PRIMARY KEY,order_id TEXT NOT NULL,participant TEXT NOT NULL,nonce TEXT NOT NULL UNIQUE,created_at_ms INTEGER NOT NULL,received_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS settlement_verifiers(venue_id TEXT NOT NULL,verifier_entity_id TEXT NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL,PRIMARY KEY(venue_id,verifier_entity_id));
            CREATE TABLE IF NOT EXISTS payment_attestations(attestation_id TEXT PRIMARY KEY,trade_id TEXT NOT NULL,verifier_entity_id TEXT NOT NULL,settlement_ref TEXT NOT NULL,evidence_sha256 TEXT NOT NULL,nonce TEXT NOT NULL UNIQUE,created_at_ms INTEGER NOT NULL,received_at_ms INTEGER NOT NULL,authority_basis TEXT NOT NULL,signature_json TEXT NOT NULL);
            ''')
            columns={row[1] for row in db.execute('PRAGMA table_info(orders)').fetchall()}
            if 'received_at_ms' not in columns:
                db.execute('ALTER TABLE orders ADD COLUMN received_at_ms INTEGER')
                db.execute('UPDATE orders SET received_at_ms=created_at_ms WHERE received_at_ms IS NULL')
            for table in ('rfqs','quotes'):
                cols={row[1] for row in db.execute(f'PRAGMA table_info({table})').fetchall()}
                if 'nonce' not in cols: db.execute(f'ALTER TABLE {table} ADD COLUMN nonce TEXT')
                if 'received_at_ms' not in cols:
                    db.execute(f'ALTER TABLE {table} ADD COLUMN received_at_ms INTEGER')
                    db.execute(f'UPDATE {table} SET received_at_ms=created_at_ms WHERE received_at_ms IS NULL')
                if 'signature_json' not in cols: db.execute(f'ALTER TABLE {table} ADD COLUMN signature_json TEXT')
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_eep_rfq_nonce ON rfqs(nonce) WHERE nonce IS NOT NULL')
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_eep_quote_nonce ON quotes(nonce) WHERE nonce IS NOT NULL')
    def create_venue(self,operator,name,jurisdiction,execution_models,policy_sha256):
        self.identity.load_manifest(operator); models=sorted({str(m).upper() for m in execution_models})
        if not models or set(models)-self.EXECUTION_MODELS: raise ValueError('unsupported execution model')
        body={'schema':'entity-eep-venue-v1','venue_id':rid('venue3'),'operator':operator,'name':str(name)[:256],'jurisdiction':str(jurisdiction).upper(),'execution_models':models,'policy_sha256':require_sha256(policy_sha256),'status':'ACTIVE','created_at_ms':now_ms(),'venue_is_not_protocol_authority':True}; sig=self.identity.sign(operator,body)
        with self._db() as db: db.execute('INSERT INTO venues VALUES(?,?,?,?,?,?,?,?,?)',(body['venue_id'],operator,body['name'],body['jurisdiction'],json.dumps(models),body['policy_sha256'],'ACTIVE',body['created_at_ms'],json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)
    def _record_signed_instrument(self,body,signature):
        required={'schema','instrument_id','issuer','underlying_object_id','instrument_class','rights','total_units','transferable','duration_ms','settlement_currency','delivery_mode','status','created_at_ms','bytes_are_not_the_traded_scarcity'}
        validate_signed_wire(body)
        if set(body)!=required or body.get('schema')!='entity-eep-instrument-v1' or body.get('status')!='ACTIVE' or body.get('bytes_are_not_the_traded_scarcity') is not True: raise ValueError('invalid signed instrument shape')
        issuer=str(body['issuer']); instrument_class=str(body['instrument_class']); units=int(body['total_units']); created=int(body['created_at_ms'])
        if instrument_class not in self.INSTRUMENT_CLASSES or units<1 or created<0 or not str(body['instrument_id']): raise ValueError('invalid instrument')
        if str(body['settlement_currency'])!=str(body['settlement_currency']).upper() or str(body['delivery_mode'])!=str(body['delivery_mode']).upper(): raise ValueError('instrument enums must be canonical uppercase')
        rights=dict(body['rights']); actions={str(a).upper() for a in rights.get('actions') or []}
        if not actions: raise ValueError('rights actions required')
        obj=self.fabric.get_object(body['underlying_object_id'])
        if obj['controller_entity_id']!=issuer: raise PermissionError('underlying controller must issue instrument')
        manifest=self.identity.load_manifest(issuer)
        if not self.identity.verify_signature(manifest,body,signature): raise PermissionError('instrument signature invalid')
        try:
            with self._db() as db:
                db.execute('INSERT INTO instruments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(body['instrument_id'],issuer,body['underlying_object_id'],instrument_class,json.dumps(rights,sort_keys=True),units,int(bool(body['transferable'])),int(body['duration_ms']) if body['duration_ms'] is not None else None,body['settlement_currency'],body['delivery_mode'],'ACTIVE',created,json.dumps(signature,sort_keys=True)))
                db.execute('INSERT INTO balances VALUES(?,?,?)',(body['instrument_id'],issuer,units))
        except sqlite3.IntegrityError as exc: raise ValueError('duplicate/replayed instrument') from exc
        return dict(body,total_units=units,signature=signature)
    def submit_signed_instrument(self,instrument,signature):
        return self._record_signed_instrument(dict(instrument),dict(signature))
    def define_instrument(self,issuer,underlying_object_id,instrument_class,rights,total_units,settlement_currency,transferable=False,duration_ms=None,delivery_mode='ENTITLEMENT'):
        rights_doc=dict(rights); rights_doc['actions']=sorted({str(a).upper() for a in rights_doc.get('actions') or []})
        body={'schema':'entity-eep-instrument-v1','instrument_id':rid('inst3'),'issuer':issuer,'underlying_object_id':underlying_object_id,
              'instrument_class':str(instrument_class).upper(),'rights':rights_doc,'total_units':int(total_units),'transferable':bool(transferable),
              'duration_ms':int(duration_ms) if duration_ms is not None else None,'settlement_currency':str(settlement_currency).upper(),
              'delivery_mode':str(delivery_mode).upper(),'status':'ACTIVE','created_at_ms':now_ms(),'bytes_are_not_the_traded_scarcity':True}
        sig=self.identity.sign(issuer,body)
        return self._record_signed_instrument(body,sig)
    def balance(self,instrument_id,holder):
        with self._db() as db: row=db.execute('SELECT units FROM balances WHERE instrument_id=? AND holder=?',(instrument_id,holder)).fetchone()
        return int(row['units']) if row else 0
    def _record_signed_disclosure(self,body,signature):
        required={'schema','disclosure_id','venue_id','instrument_id','publisher','disclosure_type','content_sha256','created_at_ms','protected_data_included'}
        validate_signed_wire(body)
        if set(body)!=required or body.get('schema')!='entity-eep-disclosure-v1' or body.get('protected_data_included') is not False: raise ValueError('invalid signed disclosure shape')
        publisher=str(body['publisher']); created=int(body['created_at_ms']); content=require_sha256(body['content_sha256'])
        if created<0 or not str(body['disclosure_id']): raise ValueError('invalid disclosure identity/time')
        manifest=self.identity.load_manifest(publisher)
        if not self.identity.verify_signature(manifest,body,signature): raise PermissionError('disclosure signature invalid')
        with self._db() as db:
            venue=db.execute("SELECT 1 FROM venues WHERE venue_id=? AND status='ACTIVE'",(body['venue_id'],)).fetchone()
            inst=db.execute("SELECT 1 FROM instruments WHERE instrument_id=? AND status='ACTIVE'",(body['instrument_id'],)).fetchone()
        if not venue or not inst: raise KeyError('active venue/instrument required')
        try:
            with self._db() as db: db.execute('INSERT INTO disclosures VALUES(?,?,?,?,?,?,?,?)',(body['disclosure_id'],body['venue_id'],body['instrument_id'],publisher,str(body['disclosure_type']).upper(),content,created,json.dumps(signature,sort_keys=True)))
        except sqlite3.IntegrityError as exc: raise ValueError('duplicate/replayed disclosure') from exc
        return dict(body,disclosure_type=str(body['disclosure_type']).upper(),content_sha256=content,signature=signature)
    def submit_signed_disclosure(self,disclosure,signature):
        return self._record_signed_disclosure(dict(disclosure),dict(signature))
    def publish_disclosure(self,venue_id,instrument_id,publisher,disclosure_type,content_sha256):
        body={'schema':'entity-eep-disclosure-v1','disclosure_id':rid('disc3'),'venue_id':venue_id,'instrument_id':instrument_id,
              'publisher':publisher,'disclosure_type':str(disclosure_type).upper(),'content_sha256':require_sha256(content_sha256),
              'created_at_ms':now_ms(),'protected_data_included':False}
        sig=self.identity.sign(publisher,body)
        return self._record_signed_disclosure(body,sig)
    def _record_signed_listing(self,body,signature):
        required={'schema','listing_id','venue_id','instrument_id','lister','min_lot','tick_size','disclosure_sha256','status','created_at_ms'}
        validate_signed_wire(body)
        if set(body)!=required or body.get('schema')!='entity-eep-listing-v1' or body.get('status')!='ACTIVE': raise ValueError('invalid signed listing shape')
        lister=str(body['lister']); min_lot=max(1,int(body['min_lot'])); tick=max(1,int(body['tick_size'])); created=int(body['created_at_ms']); disclosure=require_sha256(body['disclosure_sha256'])
        if created<0 or not str(body['listing_id']): raise ValueError('invalid listing identity/time')
        manifest=self.identity.load_manifest(lister)
        if not self.identity.verify_signature(manifest,body,signature): raise PermissionError('listing signature invalid')
        with self._db() as db:
            venue=db.execute("SELECT * FROM venues WHERE venue_id=? AND status='ACTIVE'",(body['venue_id'],)).fetchone()
            inst=db.execute("SELECT * FROM instruments WHERE instrument_id=? AND status='ACTIVE'",(body['instrument_id'],)).fetchone()
            disc=db.execute('SELECT 1 FROM disclosures WHERE venue_id=? AND instrument_id=? AND content_sha256=?',(body['venue_id'],body['instrument_id'],disclosure)).fetchone()
        if not venue or not inst: raise KeyError('active venue/instrument required')
        if not disc: raise ValueError('listing disclosure has not been published for venue/instrument')
        if self.balance(body['instrument_id'],lister)<=0: raise PermissionError('lister has no entitlement')
        try:
            with self._db() as db: db.execute('INSERT INTO listings VALUES(?,?,?,?,?,?,?,?,?,?)',(body['listing_id'],body['venue_id'],body['instrument_id'],lister,min_lot,tick,disclosure,'ACTIVE',created,json.dumps(signature,sort_keys=True)))
        except sqlite3.IntegrityError as exc: raise ValueError('duplicate/replayed listing') from exc
        return dict(body,min_lot=min_lot,tick_size=tick,disclosure_sha256=disclosure,signature=signature)
    def submit_signed_listing(self,listing,signature):
        return self._record_signed_listing(dict(listing),dict(signature))
    def list_instrument(self,venue_id,instrument_id,lister,min_lot,tick_size,disclosure_sha256):
        body={'schema':'entity-eep-listing-v1','listing_id':rid('listing3'),'venue_id':venue_id,'instrument_id':instrument_id,
              'lister':lister,'min_lot':max(1,int(min_lot)),'tick_size':max(1,int(tick_size)),'disclosure_sha256':require_sha256(disclosure_sha256),
              'status':'ACTIVE','created_at_ms':now_ms()}
        sig=self.identity.sign(lister,body)
        return self._record_signed_listing(body,sig)
    def _listing(self,venue_id,instrument_id):
        with self._db() as db: return db.execute("SELECT * FROM listings WHERE venue_id=? AND instrument_id=? AND status='ACTIVE' ORDER BY created_at_ms DESC LIMIT 1",(venue_id,instrument_id)).fetchone()
    def _reserved_sell_db(self,db,instrument_id,participant):
        open_row=db.execute("SELECT COALESCE(SUM(remaining),0) q FROM orders WHERE instrument_id=? AND participant=? AND side='SELL' AND status IN ('OPEN','PARTIAL')",(instrument_id,participant)).fetchone()
        pending_row=db.execute("SELECT COALESCE(SUM(t.quantity),0) q FROM trades t JOIN clearing c ON c.trade_id=t.trade_id WHERE t.instrument_id=? AND t.seller=? AND c.status='PENDING' AND t.status IN ('EXECUTED','EXECUTED_UNSETTLED')",(instrument_id,participant)).fetchone()
        return int(open_row['q'])+int(pending_row['q'])
    def _reserved_sell(self,instrument_id,participant):
        with self._db() as db: return self._reserved_sell_db(db,instrument_id,participant)
    def _record_signed_order(self,body,signature):
        required={'schema','order_id','venue_id','instrument_id','participant','side','quantity','limit_price','tif','nonce','created_at_ms'}
        validate_signed_wire(body)
        if set(body)!=required or body.get('schema')!='entity-eep-order-v1': raise ValueError('invalid signed order shape')
        participant=str(body['participant']); side=str(body['side']).upper(); tif=str(body['tif']).upper(); qty=int(body['quantity']); price=int(body['limit_price']); created=int(body['created_at_ms'])
        if side not in self.SIDES or tif not in {'GTC','IOC','DAY'}: raise ValueError('invalid order')
        if not str(body['order_id']) or not str(body['nonce']) or created<0: raise ValueError('invalid order identity/time')
        listing=self._listing(body['venue_id'],body['instrument_id'])
        if not listing: raise KeyError('not listed')
        if qty<1 or qty%int(listing['min_lot']) or price<0 or price%int(listing['tick_size']): raise ValueError('lot/tick violation')
        manifest=self.identity.load_manifest(participant)
        if not self.identity.verify_signature(manifest,body,signature): raise PermissionError('order signature invalid')
        with self._db() as db: inst=db.execute("SELECT * FROM instruments WHERE instrument_id=? AND status='ACTIVE'",(body['instrument_id'],)).fetchone()
        if not inst: raise KeyError('active instrument required')
        if side=='SELL':
            if participant!=inst['issuer'] and not bool(inst['transferable']): raise PermissionError('secondary transfer prohibited')
            if self.balance(body['instrument_id'],participant)-self._reserved_sell(body['instrument_id'],participant)<qty: raise PermissionError('insufficient unreserved entitlement')
        received=now_ms()
        try:
            with self._db() as db:
                if side=='SELL':
                    db.execute('BEGIN IMMEDIATE')
                    bal=db.execute('SELECT units FROM balances WHERE instrument_id=? AND holder=?',(body['instrument_id'],participant)).fetchone()
                    available=(int(bal['units']) if bal else 0)-self._reserved_sell_db(db,body['instrument_id'],participant)
                    if available<qty: raise PermissionError('insufficient unreserved entitlement')
                db.execute('INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(
                    body['order_id'],body['venue_id'],body['instrument_id'],participant,side,qty,qty,price,tif,'OPEN',str(body['nonce']),created,received,json.dumps(signature,sort_keys=True)))
        except sqlite3.IntegrityError as exc: raise ValueError('duplicate/replayed order id or nonce') from exc
        recorded=dict(body,side=side,tif=tif,quantity=qty,limit_price=price,remaining=qty,status='OPEN',received_at_ms=received,signature=signature)
        self._surveillance_order(recorded)
        return recorded
    def submit_signed_order(self,order,signature):
        return self._record_signed_order(dict(order),dict(signature))
    def submit_order(self,venue_id,instrument_id,participant,side,quantity,limit_price,nonce,tif='GTC'):
        side=str(side).upper(); tif=str(tif).upper(); qty=int(quantity); price=int(limit_price)
        body={'schema':'entity-eep-order-v1','order_id':rid('ord3'),'venue_id':venue_id,'instrument_id':instrument_id,
              'participant':participant,'side':side,'quantity':qty,'limit_price':price,'tif':tif,
              'nonce':str(nonce),'created_at_ms':now_ms()}
        sig=self.identity.sign(participant,body)
        return self._record_signed_order(body,sig)
    def _surveillance_order(self,order):
        with self._db() as db:
            opposite='SELL' if order['side']=='BUY' else 'BUY'; crossing=db.execute("SELECT COUNT(*) n FROM orders WHERE venue_id=? AND instrument_id=? AND participant=? AND side=? AND status IN ('OPEN','PARTIAL')",(order['venue_id'],order['instrument_id'],order['participant'],opposite)).fetchone()['n']
            if crossing: db.execute('INSERT INTO surveillance VALUES(?,?,?,?,?,?,?)',(rid('alert3'),order['venue_id'],order['instrument_id'],order['participant'],'SELF_CROSS_RISK',json.dumps({'order_id':order['order_id'],'opposite_open_orders':int(crossing)}),now_ms()))
    def _eligible_orders(self,venue_id,instrument_id):
        with self._db() as db:
            buys=db.execute("SELECT * FROM orders WHERE venue_id=? AND instrument_id=? AND side='BUY' AND status IN ('OPEN','PARTIAL') ORDER BY limit_price DESC,received_at_ms ASC,order_id ASC",(venue_id,instrument_id)).fetchall(); sells=db.execute("SELECT * FROM orders WHERE venue_id=? AND instrument_id=? AND side='SELL' AND status IN ('OPEN','PARTIAL') ORDER BY limit_price ASC,received_at_ms ASC,order_id ASC",(venue_id,instrument_id)).fetchall()
        return buys,sells
    def match_order_book(self,venue_id,instrument_id,max_trades=100):
        trades=[]
        while len(trades)<int(max_trades):
            buys,sells=self._eligible_orders(venue_id,instrument_id)
            if not buys or not sells or int(buys[0]['limit_price'])<int(sells[0]['limit_price']): break
            buy,sell=buys[0],sells[0]
            if buy['participant']==sell['participant']:
                self._alert(venue_id,instrument_id,buy['participant'],'SELF_TRADE_BLOCKED',{'buy_order_id':buy['order_id'],'sell_order_id':sell['order_id']})
                with self._db() as db: db.execute("UPDATE orders SET status='CANCELLED',remaining=0 WHERE order_id=?",(sell['order_id'],))
                continue
            qty=min(int(buy['remaining']),int(sell['remaining'])); maker=sell if int(sell['received_at_ms'])<=int(buy['received_at_ms']) else buy; price=int(maker['limit_price']); trade=self._record_trade(venue_id,instrument_id,buy,sell,qty,price,'ORDER_BOOK');
            if trade is not None: trades.append(trade)
        return trades
    def _bind_trade_revenue(self,db,trade_id,instrument_id):
        row=db.execute('SELECT rule_set_id,allocations_json FROM revenue_rule_sets WHERE instrument_id=? ORDER BY received_at_ms DESC,rule_set_id DESC LIMIT 1',(instrument_id,)).fetchone()
        rule_set_id=row['rule_set_id'] if row else None; allocations=json.loads(row['allocations_json']) if row else {}
        db.execute('INSERT INTO trade_revenue_bindings VALUES(?,?,?,?,?)',(trade_id,instrument_id,rule_set_id,json.dumps(allocations,sort_keys=True),now_ms()))
    def trade_revenue_binding(self,trade_id):
        with self._db() as db: row=db.execute('SELECT * FROM trade_revenue_bindings WHERE trade_id=?',(trade_id,)).fetchone()
        if not row: raise KeyError('trade revenue binding not found')
        return {'trade_id':row['trade_id'],'instrument_id':row['instrument_id'],'rule_set_id':row['rule_set_id'],
                'allocations_bps':json.loads(row['allocations_json']),'bound_at_ms':int(row['bound_at_ms']),'bound_at_execution':True}
    def _record_trade(self,venue_id,instrument_id,buy,sell,qty,price,model):
        trade_id=rid('trade3'); created=now_ms()
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            buy=db.execute("SELECT * FROM orders WHERE order_id=? AND status IN ('OPEN','PARTIAL')",(buy['order_id'],)).fetchone()
            sell=db.execute("SELECT * FROM orders WHERE order_id=? AND status IN ('OPEN','PARTIAL')",(sell['order_id'],)).fetchone()
            if not buy or not sell: return None
            if buy['venue_id']!=venue_id or sell['venue_id']!=venue_id or buy['instrument_id']!=instrument_id or sell['instrument_id']!=instrument_id: return None
            if int(buy['limit_price'])<int(sell['limit_price']) or buy['participant']==sell['participant']: return None
            qty=min(int(buy['remaining']),int(sell['remaining'])); maker=sell if int(sell['received_at_ms'])<=int(buy['received_at_ms']) else buy; price=int(maker['limit_price'])
            inst=db.execute('SELECT * FROM instruments WHERE instrument_id=?',(instrument_id,)).fetchone(); amount=int(qty)*int(price)
            db.execute('INSERT INTO trades VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(trade_id,venue_id,instrument_id,buy['order_id'],sell['order_id'],buy['participant'],sell['participant'],qty,price,model,'EXECUTED',created))
            db.execute('INSERT INTO clearing VALUES(?,?,?,?,?,?,?,?)',(trade_id,buy['participant'],sell['participant'],amount,inst['settlement_currency'],'PENDING',None,0))
            self._bind_trade_revenue(db,trade_id,instrument_id)
            for row in (buy,sell):
                rem=int(row['remaining'])-qty; status='FILLED' if rem==0 else 'PARTIAL'; db.execute('UPDATE orders SET remaining=?,status=? WHERE order_id=?',(rem,status,row['order_id']))
        return {'trade_id':trade_id,'venue_id':venue_id,'instrument_id':instrument_id,'buyer':buy['participant'],'seller':sell['participant'],'quantity':qty,'price':price,'amount_units':amount,'currency':inst['settlement_currency'],'status':'EXECUTED','rights_not_bytes_traded':True}
    def _record_signed_cancellation(self,body,signature):
        required={'schema','cancellation_id','order_id','participant','nonce','created_at_ms'}
        validate_signed_wire(body)
        if set(body)!=required or body.get('schema')!='entity-eep-order-cancel-v1': raise ValueError('invalid signed cancellation shape')
        participant=str(body['participant']); created=int(body['created_at_ms'])
        if not str(body['cancellation_id']) or not str(body['nonce']) or created<0: raise ValueError('invalid cancellation identity/time')
        manifest=self.identity.load_manifest(participant)
        if not self.identity.verify_signature(manifest,body,signature): raise PermissionError('cancellation signature invalid')
        received=now_ms()
        try:
            with self._db() as db:
                row=db.execute('SELECT * FROM orders WHERE order_id=?',(body['order_id'],)).fetchone()
                if not row or row['participant']!=participant: raise PermissionError('order owner required')
                if row['status'] not in {'OPEN','PARTIAL'}: raise ValueError('order not cancelable')
                db.execute('INSERT INTO order_cancellations VALUES(?,?,?,?,?,?,?)',(body['cancellation_id'],body['order_id'],participant,str(body['nonce']),created,received,json.dumps(signature,sort_keys=True)))
                db.execute("UPDATE orders SET status='CANCELLED',remaining=0 WHERE order_id=?",(body['order_id'],))
        except sqlite3.IntegrityError as exc: raise ValueError('duplicate/replayed cancellation') from exc
        return dict(body,status='CANCELLED',received_at_ms=received,signature=signature)
    def submit_signed_cancellation(self,cancellation,signature):
        return self._record_signed_cancellation(dict(cancellation),dict(signature))
    def cancel_order(self,order_id,participant,nonce=None):
        body={'schema':'entity-eep-order-cancel-v1','cancellation_id':rid('cancel3'),'order_id':str(order_id),'participant':participant,'nonce':str(nonce or rid('nonce')),'created_at_ms':now_ms()}
        sig=self.identity.sign(participant,body)
        return self._record_signed_cancellation(body,sig)
    def authorize_settlement_verifier(self,venue_id,operator,verifier_entity_id):
        self.identity.load_manifest(verifier_entity_id)
        with self._db() as db:
            venue=db.execute("SELECT * FROM venues WHERE venue_id=? AND status='ACTIVE'",(venue_id,)).fetchone()
        if not venue or venue['operator']!=operator: raise PermissionError('venue operator required')
        body={'schema':'entity-eep-settlement-verifier-authorization-v1','venue_id':venue_id,'operator':operator,
              'verifier_entity_id':verifier_entity_id,'status':'ACTIVE','created_at_ms':now_ms()}
        sig=self.identity.sign(operator,body)
        with self._db() as db:
            db.execute('INSERT INTO settlement_verifiers VALUES(?,?,?,?,?) ON CONFLICT(venue_id,verifier_entity_id) DO UPDATE SET status=excluded.status,created_at_ms=excluded.created_at_ms,signature_json=excluded.signature_json',
                       (venue_id,verifier_entity_id,'ACTIVE',body['created_at_ms'],json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)
    def revoke_settlement_verifier(self,venue_id,operator,verifier_entity_id):
        with self._db() as db:
            venue=db.execute("SELECT * FROM venues WHERE venue_id=? AND status='ACTIVE'",(venue_id,)).fetchone()
            if not venue or venue['operator']!=operator: raise PermissionError('venue operator required')
            row=db.execute('SELECT 1 FROM settlement_verifiers WHERE venue_id=? AND verifier_entity_id=?',(venue_id,verifier_entity_id)).fetchone()
            if not row: raise KeyError('settlement verifier authorization not found')
            db.execute("UPDATE settlement_verifiers SET status='REVOKED' WHERE venue_id=? AND verifier_entity_id=?",(venue_id,verifier_entity_id))
        return {'venue_id':venue_id,'verifier_entity_id':verifier_entity_id,'status':'REVOKED'}
    def _payment_attestation_authority(self,trade,venue,verifier_entity_id):
        if verifier_entity_id==trade['buyer']: return 'PAYER_ATTESTATION'
        if verifier_entity_id==trade['seller']: return 'PAYEE_ATTESTATION'
        if verifier_entity_id==venue['operator']: return 'VENUE_OPERATOR_ATTESTATION'
        with self._db() as db:
            row=db.execute("SELECT status FROM settlement_verifiers WHERE venue_id=? AND verifier_entity_id=?",(trade['venue_id'],verifier_entity_id)).fetchone()
        if row and row['status']=='ACTIVE': return 'AUTHORIZED_SETTLEMENT_VERIFIER'
        raise PermissionError('verifier is not authorized for this venue trade')
    def _record_signed_payment_attestation(self,body,signature):
        required={'schema','attestation_id','trade_id','verifier_entity_id','settlement_ref','evidence_sha256','nonce','created_at_ms','verification_is_attestation_not_absolute_truth'}
        validate_signed_wire(body)
        if set(body)!=required or body.get('schema')!='entity-eep-payment-attestation-v1' or body.get('verification_is_attestation_not_absolute_truth') is not True: raise ValueError('invalid payment attestation shape')
        evidence=require_sha256(body['evidence_sha256']); verifier=str(body['verifier_entity_id']); created=int(body['created_at_ms'])
        if not str(body['attestation_id']) or not str(body['settlement_ref']) or not str(body['nonce']) or created<0: raise ValueError('invalid payment attestation identity/time')
        manifest=self.identity.load_manifest(verifier)
        if not self.identity.verify_signature(manifest,body,signature): raise PermissionError('payment attestation signature invalid')
        with self._db() as db:
            trade=db.execute('SELECT * FROM trades WHERE trade_id=?',(body['trade_id'],)).fetchone()
            venue=db.execute('SELECT * FROM venues WHERE venue_id=?',(trade['venue_id'],)).fetchone() if trade else None
        if not trade or not venue: raise KeyError('trade/venue not found')
        authority=self._payment_attestation_authority(trade,venue,verifier); received=now_ms()
        try:
            with self._db() as db:
                db.execute('INSERT INTO payment_attestations VALUES(?,?,?,?,?,?,?,?,?,?)',(
                    body['attestation_id'],body['trade_id'],verifier,str(body['settlement_ref']),evidence,str(body['nonce']),created,received,authority,json.dumps(signature,sort_keys=True)))
        except sqlite3.IntegrityError as exc: raise ValueError('duplicate/replayed payment attestation') from exc
        return dict(body,evidence_sha256=evidence,received_at_ms=received,verifier_authority_basis=authority,signature=signature)
    def submit_signed_payment_attestation(self,attestation,signature):
        return self._record_signed_payment_attestation(dict(attestation),dict(signature))
    def attest_payment(self,trade_id,verifier_entity_id,settlement_ref,evidence_sha256,nonce=None):
        body={'schema':'entity-eep-payment-attestation-v1','attestation_id':rid('payatt3'),'trade_id':str(trade_id),
              'verifier_entity_id':verifier_entity_id,'settlement_ref':str(settlement_ref),'evidence_sha256':require_sha256(evidence_sha256),
              'nonce':str(nonce or rid('nonce')),'created_at_ms':now_ms(),'verification_is_attestation_not_absolute_truth':True}
        sig=self.identity.sign(verifier_entity_id,body)
        return self._record_signed_payment_attestation(body,sig)
    def settle_trade(self,trade_id,payment_ref,external_verified=False,payment_attestation_id=None):
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            clr=db.execute("SELECT * FROM clearing WHERE trade_id=? AND status='PENDING'",(trade_id,)).fetchone()
            trade=db.execute("SELECT * FROM trades WHERE trade_id=? AND status='EXECUTED'",(trade_id,)).fetchone()
            if not clr or not trade: raise KeyError('pending trade missing')
            inst=db.execute('SELECT * FROM instruments WHERE instrument_id=?',(trade['instrument_id'],)).fetchone(); venue=db.execute('SELECT * FROM venues WHERE venue_id=?',(trade['venue_id'],)).fetchone()
            if not inst or not venue: raise KeyError('trade instrument/venue missing')
            if external_verified:
                if not payment_attestation_id: raise ValueError('payment attestation required for external verification')
                attestation=db.execute('SELECT * FROM payment_attestations WHERE attestation_id=? AND trade_id=? AND settlement_ref=?',(str(payment_attestation_id),trade_id,str(payment_ref))).fetchone()
                if not attestation: raise PermissionError('valid payment attestation required for external verification')
            bal=db.execute('SELECT units FROM balances WHERE instrument_id=? AND holder=?',(trade['instrument_id'],trade['seller'])).fetchone()
            if not bal or int(bal['units'])<int(trade['quantity']): raise PermissionError('seller entitlement no longer sufficient')
            db.execute('UPDATE balances SET units=units-? WHERE instrument_id=? AND holder=?',(trade['quantity'],trade['instrument_id'],trade['seller']))
            db.execute('INSERT INTO balances(instrument_id,holder,units) VALUES(?,?,?) ON CONFLICT(instrument_id,holder) DO UPDATE SET units=units+excluded.units',(trade['instrument_id'],trade['buyer'],trade['quantity']))
            expires=now_ms()+int(inst['duration_ms']) if inst['duration_ms'] is not None else None; rights=json.loads(inst['rights_json'])
            body={'schema':'entity-eep-entitlement-v1','entitlement_id':rid('ent3'),'trade_id':trade_id,'instrument_id':trade['instrument_id'],'holder':trade['buyer'],'quantity':int(trade['quantity']),'rights':rights,'expires_at_ms':expires,'created_at_ms':now_ms(),'instrument_issuer':inst['issuer'],'venue_operator':venue['operator'],'ownership_of_underlying_transferred':False,'venue_operator_is_not_underlying_owner':True}
            sig=self.identity.sign(venue['operator'],body)
            db.execute('INSERT INTO entitlements(entitlement_id,trade_id,instrument_id,holder,quantity,rights_json,expires_at_ms,created_at_ms,signature_json) VALUES(?,?,?,?,?,?,?,?,?)',(body['entitlement_id'],trade_id,trade['instrument_id'],trade['buyer'],trade['quantity'],json.dumps(rights,sort_keys=True),expires,body['created_at_ms'],json.dumps(sig,sort_keys=True)))
            revenue=self._distribute_revenue_db(db,trade_id,int(clr['amount_units']),clr['currency'])
            db.execute("UPDATE clearing SET status='SETTLED',payment_ref=?,external_verified=? WHERE trade_id=?",(str(payment_ref),int(bool(external_verified)),trade_id)); db.execute("UPDATE trades SET status='SETTLED' WHERE trade_id=?",(trade_id,))
        return {'trade_id':trade_id,'status':'SETTLED','payment_ref':str(payment_ref),'external_money_movement_verified':bool(external_verified),'payment_attestation_id':str(payment_attestation_id) if payment_attestation_id else None,'entitlement_attested_by':'VENUE_OPERATOR','entitlement':dict(body,signature=sig),'revenue_distribution':revenue}
    def _record_signed_revenue_rules(self,body,signature):
        required={'schema','rule_set_id','instrument_id','issuer','allocations_bps','nonce','created_at_ms'}
        validate_signed_wire(body)
        if set(body)!=required or body.get('schema')!='entity-eep-revenue-rule-set-v1': raise ValueError('invalid signed revenue rule shape')
        issuer=str(body['issuer']); created=int(body['created_at_ms']); allocations={str(k):int(v) for k,v in dict(body['allocations_bps']).items()}
        total=sum(allocations.values())
        if created<0 or not str(body['rule_set_id']) or not str(body['nonce']) or total<0 or total>10000 or any(v<0 for v in allocations.values()): raise ValueError('invalid revenue allocation')
        manifest=self.identity.load_manifest(issuer)
        canonical=dict(body,allocations_bps=dict(sorted(allocations.items())))
        if not self.identity.verify_signature(manifest,canonical,signature): raise PermissionError('revenue rule signature invalid')
        received=now_ms()
        try:
            with self._db() as db:
                inst=db.execute('SELECT * FROM instruments WHERE instrument_id=?',(body['instrument_id'],)).fetchone()
                if not inst or inst['issuer']!=issuer: raise PermissionError('instrument issuer required')
                db.execute('INSERT INTO revenue_rule_sets VALUES(?,?,?,?,?,?,?,?)',(
                    body['rule_set_id'],body['instrument_id'],issuer,json.dumps(dict(sorted(allocations.items())),sort_keys=True),str(body['nonce']),created,received,json.dumps(signature,sort_keys=True)))
                db.execute('DELETE FROM revenue_rules WHERE instrument_id=?',(body['instrument_id'],))
                for recipient,bps in sorted(allocations.items()): db.execute('INSERT INTO revenue_rules VALUES(?,?,?)',(body['instrument_id'],recipient,bps))
        except sqlite3.IntegrityError as exc: raise ValueError('duplicate/replayed revenue rule set') from exc
        return dict(canonical,total_bps=total,received_at_ms=received,signature=signature)
    def submit_signed_revenue_rules(self,rule_set,signature):
        return self._record_signed_revenue_rules(dict(rule_set),dict(signature))
    def set_revenue_rules(self,instrument_id,issuer,rules_bps,nonce=None):
        allocations={str(k):int(v) for k,v in dict(rules_bps).items()}
        body={'schema':'entity-eep-revenue-rule-set-v1','rule_set_id':rid('revrule3'),'instrument_id':instrument_id,
              'issuer':issuer,'allocations_bps':dict(sorted(allocations.items())),'nonce':str(nonce or rid('nonce')),'created_at_ms':now_ms()}
        sig=self.identity.sign(issuer,body)
        return self._record_signed_revenue_rules(body,sig)
    def _distribute_revenue_db(self,db,trade_id,amount,currency):
        binding=db.execute('SELECT * FROM trade_revenue_bindings WHERE trade_id=?',(trade_id,)).fetchone()
        if not binding: raise RuntimeError('trade revenue binding missing')
        allocations=json.loads(binding['allocations_json']); raw=[(recipient,int(amount)*int(bps)//10000) for recipient,bps in sorted(allocations.items())]; out=[]
        for recipient,units in raw:
            if units<=0: continue
            eid=rid('rev3'); db.execute('INSERT INTO revenue_events VALUES(?,?,?,?,?,?)',(eid,trade_id,recipient,units,currency,now_ms())); out.append({'recipient':recipient,'amount_units':units,'currency':currency,'revenue_event_id':eid})
        return out
    def _distribute_revenue(self,trade_id,amount,currency):
        with self._db() as db: return self._distribute_revenue_db(db,trade_id,amount,currency)
    def _record_signed_usage(self,body,signature):
        required={'schema','usage_id','instrument_id','holder','action','units','nonce','created_at_ms'}
        validate_signed_wire(body)
        if set(body)!=required or body.get('schema')!='entity-eep-usage-v1': raise ValueError('invalid signed usage shape')
        holder=str(body['holder']); action=str(body['action']).upper(); units=max(1,int(body['units'])); created=int(body['created_at_ms'])
        if not str(body['usage_id']) or not str(body['nonce']) or created<0: raise ValueError('invalid usage identity/time')
        manifest=self.identity.load_manifest(holder)
        if not self.identity.verify_signature(manifest,body,signature): raise PermissionError('usage signature invalid')
        with self._db() as db:
            ents=db.execute('SELECT * FROM entitlements WHERE instrument_id=? AND holder=? AND (expires_at_ms IS NULL OR expires_at_ms>?) ORDER BY created_at_ms,entitlement_id',(body['instrument_id'],holder,now_ms())).fetchall()
            inst=db.execute('SELECT * FROM instruments WHERE instrument_id=?',(body['instrument_id'],)).fetchone()
        if not ents: raise PermissionError('active entitlement required')
        rights=json.loads(ents[-1]['rights_json']); allowed={str(x).upper() for x in rights.get('actions') or []}
        if action not in allowed: raise PermissionError('action not entitled')
        if inst and inst['delivery_mode']=='COMPUTE_TO_DATA' and action in {'COPY','REDISTRIBUTE'}: raise PermissionError('raw data delivery prohibited')
        try:
            with self._db() as db: db.execute('INSERT INTO usage VALUES(?,?,?,?,?,?,?,?)',(body['usage_id'],body['instrument_id'],holder,action,units,str(body['nonce']),created,json.dumps(signature,sort_keys=True)))
        except sqlite3.IntegrityError as exc: raise ValueError('duplicate/replayed usage') from exc
        return dict(body,action=action,units=units,signature=signature)
    def submit_signed_usage(self,usage,signature):
        return self._record_signed_usage(dict(usage),dict(signature))
    def meter_usage(self,instrument_id,holder,action,units,nonce):
        body={'schema':'entity-eep-usage-v1','usage_id':rid('usage3'),'instrument_id':instrument_id,'holder':holder,'action':str(action).upper(),'units':max(1,int(units)),'nonce':str(nonce),'created_at_ms':now_ms()}
        sig=self.identity.sign(holder,body)
        return self._record_signed_usage(body,sig)
    def market_data(self,venue_id,instrument_id):
        with self._db() as db:
            bid=db.execute("SELECT MAX(limit_price) p,SUM(remaining) q FROM orders WHERE venue_id=? AND instrument_id=? AND side='BUY' AND status IN ('OPEN','PARTIAL')",(venue_id,instrument_id)).fetchone(); ask=db.execute("SELECT MIN(limit_price) p,SUM(remaining) q FROM orders WHERE venue_id=? AND instrument_id=? AND side='SELL' AND status IN ('OPEN','PARTIAL')",(venue_id,instrument_id)).fetchone(); last=db.execute("SELECT price,quantity FROM trades WHERE venue_id=? AND instrument_id=? ORDER BY created_at_ms DESC LIMIT 1",(venue_id,instrument_id)).fetchone(); volume=db.execute("SELECT COALESCE(SUM(quantity),0) v FROM trades WHERE venue_id=? AND instrument_id=?",(venue_id,instrument_id)).fetchone()['v']
        return {'venue_id':venue_id,'instrument_id':instrument_id,'best_bid':bid['p'],'best_ask':ask['p'],'last_price':last['price'] if last else None,'last_quantity':last['quantity'] if last else None,'volume_units':int(volume),'market_data_is_observation_not_valuation':True}
    def _record_signed_rfq(self,body,signature):
        required={'schema','rfq_id','venue_id','instrument_id','requester','side','quantity','expires_at_ms','nonce','created_at_ms'}
        validate_signed_wire(body)
        if set(body)!=required or body.get('schema')!='entity-eep-rfq-v1': raise ValueError('invalid signed RFQ shape')
        requester=str(body['requester']); side=str(body['side']).upper(); qty=int(body['quantity']); expiry=int(body['expires_at_ms']); created=int(body['created_at_ms'])
        if side not in self.SIDES or qty<1 or expiry<=now_ms() or created<0 or not str(body['nonce']): raise ValueError('invalid RFQ')
        if not self._listing(body['venue_id'],body['instrument_id']): raise KeyError('instrument not listed on venue')
        manifest=self.identity.load_manifest(requester)
        if not self.identity.verify_signature(manifest,body,signature): raise PermissionError('RFQ signature invalid')
        if side=='SELL' and self.balance(body['instrument_id'],requester)<qty: raise PermissionError('RFQ seller lacks entitlement')
        received=now_ms()
        try:
            with self._db() as db:
                db.execute('INSERT INTO rfqs(rfq_id,venue_id,instrument_id,requester,side,quantity,expires_at_ms,status,created_at_ms,nonce,received_at_ms,signature_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(
                    body['rfq_id'],body['venue_id'],body['instrument_id'],requester,side,qty,expiry,'OPEN',created,str(body['nonce']),received,json.dumps(signature,sort_keys=True)))
        except sqlite3.IntegrityError as exc: raise ValueError('duplicate/replayed RFQ') from exc
        return dict(body,side=side,quantity=qty,status='OPEN',received_at_ms=received,signature=signature)
    def submit_signed_rfq(self,rfq,signature):
        return self._record_signed_rfq(dict(rfq),dict(signature))
    def open_rfq(self,venue_id,instrument_id,requester,side,quantity,expires_at_ms,nonce=None):
        body={'schema':'entity-eep-rfq-v1','rfq_id':rid('rfq3'),'venue_id':venue_id,'instrument_id':instrument_id,
              'requester':requester,'side':str(side).upper(),'quantity':int(quantity),'expires_at_ms':int(expires_at_ms),
              'nonce':str(nonce or rid('nonce')),'created_at_ms':now_ms()}
        sig=self.identity.sign(requester,body)
        return self._record_signed_rfq(body,sig)
    def create_rfq(self,venue_id,instrument_id,requester,side,quantity,expires_at_ms,nonce=None):
        return self.open_rfq(venue_id,instrument_id,requester,side,quantity,expires_at_ms,nonce)
    def _record_signed_quote(self,body,signature):
        required={'schema','quote_id','rfq_id','provider','price','expires_at_ms','nonce','created_at_ms'}
        validate_signed_wire(body)
        if set(body)!=required or body.get('schema')!='entity-eep-rfq-quote-v1': raise ValueError('invalid signed quote shape')
        provider=str(body['provider']); price=int(body['price']); expiry=int(body['expires_at_ms']); created=int(body['created_at_ms'])
        if price<0 or expiry<=now_ms() or created<0 or not str(body['nonce']): raise ValueError('invalid quote')
        manifest=self.identity.load_manifest(provider)
        if not self.identity.verify_signature(manifest,body,signature): raise PermissionError('quote signature invalid')
        with self._db() as db: rfq=db.execute("SELECT * FROM rfqs WHERE rfq_id=? AND status='OPEN'",(body['rfq_id'],)).fetchone()
        if not rfq or now_ms()>int(rfq['expires_at_ms']): raise KeyError('active RFQ required')
        if rfq['side']=='BUY':
            available=self.balance(rfq['instrument_id'],provider)-self._reserved_sell(rfq['instrument_id'],provider)
            if available<int(rfq['quantity']): raise PermissionError('quote provider lacks unreserved sell entitlement')
        received=now_ms()
        try:
            with self._db() as db:
                db.execute('INSERT INTO quotes(quote_id,rfq_id,provider,price,expires_at_ms,status,created_at_ms,nonce,received_at_ms,signature_json) VALUES(?,?,?,?,?,?,?,?,?,?)',(
                    body['quote_id'],body['rfq_id'],provider,price,expiry,'OPEN',created,str(body['nonce']),received,json.dumps(signature,sort_keys=True)))
        except sqlite3.IntegrityError as exc: raise ValueError('duplicate/replayed quote') from exc
        return dict(body,price=price,status='OPEN',received_at_ms=received,signature=signature)
    def submit_signed_quote(self,quote,signature):
        return self._record_signed_quote(dict(quote),dict(signature))
    def quote_rfq(self,rfq_id,provider,price,expires_at_ms,nonce=None):
        body={'schema':'entity-eep-rfq-quote-v1','quote_id':rid('quote3'),'rfq_id':rfq_id,'provider':provider,'price':int(price),
              'expires_at_ms':int(expires_at_ms),'nonce':str(nonce or rid('nonce')),'created_at_ms':now_ms()}
        sig=self.identity.sign(provider,body)
        return self._record_signed_quote(body,sig)
    def _record_signed_quote_acceptance(self,body,signature):
        required={'schema','acceptance_id','rfq_id','quote_id','requester','nonce','created_at_ms'}
        validate_signed_wire(body)
        if set(body)!=required or body.get('schema')!='entity-eep-rfq-acceptance-v1': raise ValueError('invalid signed RFQ acceptance shape')
        requester=str(body['requester']); created=int(body['created_at_ms'])
        if created<0 or not str(body['nonce']): raise ValueError('invalid RFQ acceptance')
        manifest=self.identity.load_manifest(requester)
        if not self.identity.verify_signature(manifest,body,signature): raise PermissionError('RFQ acceptance signature invalid')
        received=now_ms()
        try:
            with self._db() as db:
                db.execute('BEGIN IMMEDIATE')
                rfq=db.execute("SELECT * FROM rfqs WHERE rfq_id=? AND status='OPEN'",(body['rfq_id'],)).fetchone()
                quote=db.execute("SELECT * FROM quotes WHERE quote_id=? AND rfq_id=? AND status='OPEN'",(body['quote_id'],body['rfq_id'])).fetchone()
                if not rfq or not quote or rfq['requester']!=requester: raise PermissionError('valid requester/quote required')
                if now_ms()>min(int(rfq['expires_at_ms']),int(quote['expires_at_ms'])): raise ValueError('RFQ/quote expired')
                buyer=requester if rfq['side']=='BUY' else quote['provider']; seller=quote['provider'] if rfq['side']=='BUY' else requester
                bal=db.execute('SELECT units FROM balances WHERE instrument_id=? AND holder=?',(rfq['instrument_id'],seller)).fetchone()
                available=(int(bal['units']) if bal else 0)-self._reserved_sell_db(db,rfq['instrument_id'],seller)
                if available<int(rfq['quantity']): raise PermissionError('RFQ seller lacks unreserved entitlement')
                db.execute('INSERT INTO rfq_acceptances VALUES(?,?,?,?,?,?,?,?)',(
                    body['acceptance_id'],body['rfq_id'],body['quote_id'],requester,str(body['nonce']),created,received,json.dumps(signature,sort_keys=True)))
                inst=db.execute('SELECT * FROM instruments WHERE instrument_id=?',(rfq['instrument_id'],)).fetchone(); trade_id=rid('trade3'); amount=int(rfq['quantity'])*int(quote['price'])
                db.execute('INSERT INTO trades VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(trade_id,rfq['venue_id'],rfq['instrument_id'],None,None,buyer,seller,int(rfq['quantity']),int(quote['price']),'RFQ','EXECUTED',now_ms()))
                db.execute('INSERT INTO clearing VALUES(?,?,?,?,?,?,?,?)',(trade_id,buyer,seller,amount,inst['settlement_currency'],'PENDING',None,0))
                self._bind_trade_revenue(db,trade_id,rfq['instrument_id'])
                db.execute("UPDATE rfqs SET status='ACCEPTED' WHERE rfq_id=?",(body['rfq_id'],)); db.execute("UPDATE quotes SET status='ACCEPTED' WHERE quote_id=?",(body['quote_id'],))
        except sqlite3.IntegrityError as exc: raise ValueError('duplicate/replayed RFQ acceptance') from exc
        return dict(body,status='EXECUTED',trade_id=trade_id,execution_model='RFQ',received_at_ms=received,signature=signature)
    def submit_signed_quote_acceptance(self,acceptance,signature):
        return self._record_signed_quote_acceptance(dict(acceptance),dict(signature))
    def accept_quote(self,rfq_id,quote_id,requester,nonce=None):
        body={'schema':'entity-eep-rfq-acceptance-v1','acceptance_id':rid('accept3'),'rfq_id':rfq_id,'quote_id':quote_id,
              'requester':requester,'nonce':str(nonce or rid('nonce')),'created_at_ms':now_ms()}
        sig=self.identity.sign(requester,body)
        return self._record_signed_quote_acceptance(body,sig)
    def _alert(self,venue_id,instrument_id,participant,alert_type,evidence):
        with self._db() as db: db.execute('INSERT INTO surveillance VALUES(?,?,?,?,?,?,?)',(rid('alert3'),venue_id,instrument_id,participant,alert_type,json.dumps(evidence,sort_keys=True),now_ms()))
    def surveillance_alerts(self,venue_id):
        with self._db() as db: rows=db.execute('SELECT * FROM surveillance WHERE venue_id=? ORDER BY created_at_ms,alert_id',(venue_id,)).fetchall()
        return [{**dict(r),'evidence':json.loads(r['evidence_json'])} for r in rows]
    def status(self):
        with self._db() as db:
            tables=('venues','instruments','listings','orders','order_cancellations','trades','clearing','payment_attestations','settlement_verifiers','entitlements','usage','surveillance','rfqs','quotes','rfq_acceptances','revenue_rule_sets','trade_revenue_bindings')
            counts={name:int(db.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]) for name in tables}
        return {'schema':'entity-eep-status-v1','profile':'ENTITY_EXCHANGE_PROTOCOL','version':'3.0.0',
                'rights_are_traded_not_bytes':True,'venue_neutral':True,'payment_versus_right_transfer':True,
                'deterministic_price_time_matching':True,'market_surveillance':True,'market_data':True,'rfq':True,
                'revenue_distribution':True,'externally_signed_orders':True,'venue_receipt_time_priority':True,
                'externally_signed_participant_actions':True,'externally_signed_issuer_actions':True,
                'signed_external_payment_attestations':True,'listing_disclosure_binding':True,
                'issuer_authenticated_revenue_rules':True,'entitlement_attested_by_venue_operator':True,
                'unsettled_sell_commitments_reserved':True,'trade_time_revenue_binding':True,
                'atomic_sell_admission':True,'atomic_order_book_execution':True,'atomic_settlement':True,'atomic_revenue_settlement':True,'counts':counts}
