from __future__ import annotations
from pathlib import Path
import base64, hashlib, ipaddress, json, mimetypes, os, secrets, socket, socketserver, struct, threading, time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey,X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

def _b64(v:bytes)->str: return base64.urlsafe_b64encode(v).decode().rstrip('=')
def _unb64(v:str)->bytes: return base64.urlsafe_b64decode(str(v)+'='*(-len(str(v))%4))
def _canon(v)->bytes: return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def _sha(v)->str: return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else _canon(v)).hexdigest()
def _now()->int: return int(time.time()*1000)
def _send(sock,obj):
    raw=_canon(obj); sock.sendall(struct.pack('!I',len(raw))+raw)
def _recv(sock,max_size=4*1024*1024):
    head=b''
    while len(head)<4:
        part=sock.recv(4-len(head))
        if not part: raise ConnectionError('connection closed')
        head+=part
    size=struct.unpack('!I',head)[0]
    if size<1 or size>max_size: raise ValueError('invalid frame size')
    data=b''
    while len(data)<size:
        part=sock.recv(min(65536,size-len(data)))
        if not part: raise ConnectionError('connection closed')
        data+=part
    return json.loads(data.decode())
class NodeKeyMaterial:
    def __init__(self,key_path:str|Path):
        self.path=Path(key_path); self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.is_file(): self.private=Ed25519PrivateKey.from_private_bytes(self.path.read_bytes())
        else:
            self.private=Ed25519PrivateKey.generate()
            raw=self.private.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption())
            self.path.write_bytes(raw)
            try: os.chmod(self.path,0o600)
            except OSError: pass
    @property
    def public_b64(self)->str:
        return _b64(self.private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))
    def sign(self,body:dict)->dict:
        return {'suite':'Ed25519','signature_b64':_b64(self.private.sign(_canon(body))),'payload_sha256':_sha(body)}

class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True
    # Qualification requirement: sustain request storms without inheriting
    # socketserver's tiny default listen backlog (5). The OS may clamp this
    # value, but a large explicit queue prevents avoidable connection refusal
    # during bounded high-concurrency bursts.
    request_queue_size=8192

class EntityNodeRuntime:
    """Owner-controlled DNS-free node runtime with signed ephemeral E2E session establishment."""
    def __init__(self,node_root:str|Path,node_id:str):
        self.root=Path(node_root).resolve(); self.root.mkdir(parents=True,exist_ok=True)
        self.node_id=str(node_id); self.keys=NodeKeyMaterial(self.root/'node_ed25519.key')
        self.services={}; self._seen=set(); self._lock=threading.RLock(); self._server=None; self._thread=None
    @property
    def public_key_b64(self): return self.keys.public_b64
    def add_content_service(self,service_id:str,content_root:str|Path):
        root=Path(content_root).resolve(); root.mkdir(parents=True,exist_ok=True)
        self.services[str(service_id)]={'type':'CONTENT','root':root}
        return {'service_id':str(service_id),'content_root':str(root),'source_data_uploaded_centrally':False}
    def add_api_service(self,service_id:str,handler):
        if not callable(handler): raise TypeError('handler must be callable')
        self.services[str(service_id)]={'type':'API','handler':handler}; return {'service_id':str(service_id),'type':'API'}
    def _derive(self,private:X25519PrivateKey,peer_public_b64:str,aad:bytes)->bytes:
        shared=private.exchange(X25519PublicKey.from_public_bytes(_unb64(peer_public_b64)))
        return HKDF(algorithm=hashes.SHA256(),length=32,salt=hashlib.sha256(aad).digest(),info=b'ENTITY-DIRECT-SESSION-v1').derive(shared)
    def _application(self,service_id:str,request:dict)->dict:
        svc=self.services.get(str(service_id))
        if not svc: return {'status':404,'error':'service_not_found'}
        if svc['type']=='CONTENT':
            if str(request.get('operation') or 'GET').upper()!='GET': return {'status':405,'error':'operation_denied'}
            rel=str(request.get('path') or 'index.html').lstrip('/\\')
            target=(svc['root']/rel).resolve()
            try: target.relative_to(svc['root'])
            except ValueError: return {'status':403,'error':'path_scope_denied'}
            if not target.is_file(): return {'status':404,'error':'content_not_found'}
            raw=target.read_bytes()
            return {'status':200,'content_b64':_b64(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                    'media_type':mimetypes.guess_type(target.name)[0] or 'application/octet-stream',
                    'source_path_exposed':False,'central_upload_required':False}
        result=svc['handler'](dict(request))
        return {'status':200,'result':result,'central_upload_required':False}

    def _handle(self,sock):
        hello=_recv(sock); service_id=str(hello.get('service_id') or ''); nonce=str(hello.get('nonce') or '')
        if hello.get('schema')!='entity-direct-hello-v1' or hello.get('node_id')!=self.node_id or service_id not in self.services:
            raise PermissionError('invalid direct-session hello')
        if not nonce or nonce in self._seen: raise ValueError('direct-session replay')
        with self._lock: self._seen.add(nonce)
        client_pub=str(hello.get('client_x25519_b64') or ''); ephemeral=X25519PrivateKey.generate()
        server_pub=_b64(ephemeral.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))
        body={'schema':'entity-direct-server-hello-v1','node_id':self.node_id,'service_id':service_id,
              'client_x25519_b64':client_pub,'server_x25519_b64':server_pub,'nonce':nonce,'created_at_ms':_now()}
        signature=self.keys.sign(body); _send(sock,{**body,'node_signature':signature})
        aad=_canon(body); key=self._derive(ephemeral,client_pub,aad)
        packet=_recv(sock)
        iv=_unb64(packet['nonce_b64']); plain=AESGCM(key).decrypt(iv,_unb64(packet['ciphertext_b64']),aad)
        request=json.loads(plain.decode()); response=self._application(service_id,request)
        raw=_canon(response); out_iv=os.urandom(12); cipher=AESGCM(key).encrypt(out_iv,raw,aad)
        _send(sock,{'schema':'entity-direct-data-v1','nonce_b64':_b64(out_iv),'ciphertext_b64':_b64(cipher)})

    def start(self,host:str='127.0.0.1',port:int=0)->dict:
        ipaddress.ip_address(host)
        runtime=self
        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                try: runtime._handle(self.request)
                except Exception as exc:
                    try: _send(self.request,{'schema':'entity-direct-error-v1','error':type(exc).__name__})
                    except Exception: pass
        self._server=_ThreadingTCPServer((host,int(port)),Handler)
        self._thread=threading.Thread(target=self._server.serve_forever,daemon=True); self._thread.start()
        addr=self._server.server_address
        return {'node_id':self.node_id,'host':addr[0],'port':addr[1],'dns_name':None,'dns_required':False,
                'encrypted_sessions':True,'owner_controlled_runtime':True}
    def stop(self):
        if self._server: self._server.shutdown(); self._server.server_close(); self._server=None
        if self._thread: self._thread.join(timeout=2); self._thread=None
    def status(self):
        return {'ready':True,'node_id':self.node_id,'services':sorted(self.services),'dns_required':False,
                'owner_controlled':True,'encrypted_direct_session':True,'replay_protected':True}
class EntityDirectClient:
    """Verifies Entity-authorized node identity before accepting encrypted service data."""
    @staticmethod
    def request(resolution_proof:dict,service_id:str,request:dict,*,timeout:float=5.0)->dict:
        matches=[x for x in resolution_proof.get('services') or [] if (x.get('service') or {}).get('service_id')==service_id]
        if len(matches)!=1: raise KeyError('service not present in verified resolution proof')
        service=matches[0]['service']; node=matches[0]['node']; endpoint=dict(service.get('endpoint') or {})
        host=str(endpoint.get('host') or ''); port=int(endpoint.get('port') or 0); ipaddress.ip_address(host)
        if node.get('effective_status',node.get('status'))!='ACTIVE': raise PermissionError('resolved node is not active')
        client=X25519PrivateKey.generate(); client_pub=_b64(client.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))
        hello={'schema':'entity-direct-hello-v1','node_id':node['node_id'],'service_id':service_id,
               'client_x25519_b64':client_pub,'nonce':secrets.token_urlsafe(24)}
        last_exc=None
        sock=None
        for attempt in range(6):
            try:
                sock=socket.create_connection((host,port),timeout=timeout)
                break
            except (ConnectionRefusedError, TimeoutError, OSError) as exc:
                last_exc=exc
                if attempt>=5: raise
                time.sleep(min(0.005*(2**attempt),0.08))
        if sock is None:
            raise ConnectionError('direct connection unavailable') from last_exc
        with sock:
            _send(sock,hello); server=_recv(sock)
            if server.get('schema')!='entity-direct-server-hello-v1': raise PermissionError('invalid server handshake')
            body={k:server[k] for k in ('schema','node_id','service_id','client_x25519_b64','server_x25519_b64','nonce','created_at_ms')}
            if body['node_id']!=node['node_id'] or body['service_id']!=service_id or body['client_x25519_b64']!=client_pub or body['nonce']!=hello['nonce']:
                raise PermissionError('server handshake binding mismatch')
            sig=server.get('node_signature') or {}
            if sig.get('payload_sha256')!=_sha(body): raise PermissionError('node handshake payload hash mismatch')
            try:
                Ed25519PublicKey.from_public_bytes(_unb64(node['public_key_b64'])).verify(_unb64(sig['signature_b64']),_canon(body))
            except Exception as exc: raise PermissionError('node handshake signature invalid') from exc
            aad=_canon(body); key=EntityDirectClient._derive(client,body['server_x25519_b64'],aad)
            iv=os.urandom(12); cipher=AESGCM(key).encrypt(iv,_canon(request),aad)
            _send(sock,{'schema':'entity-direct-data-v1','nonce_b64':_b64(iv),'ciphertext_b64':_b64(cipher)})
            packet=_recv(sock)
            if packet.get('schema')!='entity-direct-data-v1': raise RuntimeError('node service request failed')
            plain=AESGCM(key).decrypt(_unb64(packet['nonce_b64']),_unb64(packet['ciphertext_b64']),aad)
            out=json.loads(plain.decode()); out['entity_root_verified']=resolution_proof.get('entity_root'); out['node_verified']=node['node_id']
            out['dns_used']=False; out['direct_encrypted_session']=True; return out
    @staticmethod
    def _derive(private,peer_public_b64,aad):
        shared=private.exchange(X25519PublicKey.from_public_bytes(_unb64(peer_public_b64)))
        return HKDF(algorithm=hashes.SHA256(),length=32,salt=hashlib.sha256(aad).digest(),info=b'ENTITY-DIRECT-SESSION-v1').derive(shared)
