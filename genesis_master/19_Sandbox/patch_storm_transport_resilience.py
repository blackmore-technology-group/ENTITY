from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\22_Sovereign_Domain\node_runtime\canonical_node_runtime.py")
s=p.read_text(encoding='utf-8')
s=s.replace('request_queue_size=2048','request_queue_size=8192')
old="""        with socket.create_connection((host,port),timeout=timeout) as sock:\n            _send(sock,hello); server=_recv(sock)"""
new="""        last_exc=None\n        sock=None\n        for attempt in range(6):\n            try:\n                sock=socket.create_connection((host,port),timeout=timeout)\n                break\n            except (ConnectionRefusedError, TimeoutError, OSError) as exc:\n                last_exc=exc\n                if attempt>=5: raise\n                time.sleep(min(0.005*(2**attempt),0.08))\n        if sock is None:\n            raise ConnectionError('direct connection unavailable') from last_exc\n        with sock:\n            _send(sock,hello); server=_recv(sock)"""
if old not in s:
    raise SystemExit('target block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched',p)
