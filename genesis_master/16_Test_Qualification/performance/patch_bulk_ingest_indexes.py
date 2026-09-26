from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\04_Entity_Registry\bulk_ingest\canonical_bulk_ingest.py")
s=p.read_text(encoding="utf-8")
for line in (
    '            db.execute("CREATE INDEX IF NOT EXISTS idx_bulk_assets_controller ON assets(controller_entity_id)")\n',
    '            db.execute("CREATE INDEX IF NOT EXISTS idx_bulk_assets_batch ON assets(batch_id)")\n',
    '            db.execute("CREATE INDEX IF NOT EXISTS idx_bulk_events_batch ON events(batch_id)")\n',
    '            db.execute("CREATE INDEX IF NOT EXISTS idx_bulk_events_asset ON events(asset_id)")\n',
):
    s=s.replace(line,"")
marker='    def status(self) -> dict:\n'
insert='''    def finalize_indexes(self) -> dict:\n        with self._connect() as db:\n            db.execute("CREATE INDEX IF NOT EXISTS idx_bulk_assets_controller ON assets(controller_entity_id)")\n            db.execute("CREATE INDEX IF NOT EXISTS idx_bulk_assets_batch ON assets(batch_id)")\n            db.execute("CREATE INDEX IF NOT EXISTS idx_bulk_events_batch ON events(batch_id)")\n            db.execute("CREATE INDEX IF NOT EXISTS idx_bulk_events_asset ON events(asset_id)")\n        return {"ready":True,"indexes":["idx_bulk_assets_controller","idx_bulk_assets_batch","idx_bulk_events_batch","idx_bulk_events_asset"]}\n\n'''
if 'def finalize_indexes' not in s:
    if marker not in s: raise RuntimeError('status marker missing')
    s=s.replace(marker,insert+marker)
p.write_text(s,encoding="utf-8")
print('PATCHED')
