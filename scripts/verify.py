"""Verify downloaded raw pages, merged JSON/JSONL, IDs and recorded hashes."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'data'
manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
rows = json.loads((root / 'memes.json').read_text(encoding='utf-8'))
lines = [json.loads(line) for line in (root / 'memes.jsonl').read_text(encoding='utf-8').splitlines()]
raw_rows = []
assert len(list((root / 'pages').glob('page-*.json'))) == manifest['page_count']
for entry in manifest['pages']:
    path = root / entry['path']
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == entry['sha256']
    payload = json.loads(raw)
    assert payload['code'] == 200
    assert payload['data']['total'] == manifest['expected_total']
    assert len(payload['data']['list']) == entry['records']
    raw_rows.extend(payload['data']['list'])
for name, entry in manifest['files'].items():
    raw = (root / name).read_bytes()
    assert len(raw) == entry['bytes']
    assert hashlib.sha256(raw).hexdigest() == entry['sha256']
assert rows == lines == raw_rows
assert len(rows) == len({row['id'] for row in rows}) == manifest['expected_total']
assert manifest['validation']['passed'] is True
print(f'PASS: {len(rows)} records, {manifest["page_count"]} raw pages, JSON/JSONL equal, all SHA256 hashes verified.')
