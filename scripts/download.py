import argparse
import collections
import datetime
import hashlib
import json
from pathlib import Path
import time
import urllib.request


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description='Download serial meme pages; require fresh output directory.')
    p.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'data')
    p.add_argument('--page-size', type=int, default=500)
    p.add_argument('--interval', type=float, default=0.5)
    a = p.parse_args()
    if a.interval < 0.5 or a.page_size < 1:
        p.error('interval must be >= 0.5 and page-size > 0')
    out = a.output.resolve()
    pages_dir = out / 'pages'
    pages_dir.mkdir(parents=True, exist_ok=True)
    if any(pages_dir.glob('page-*.json')):
        p.error('Existing snapshot; choose fresh output directory')
    started = now()
    rows, pages, totals = [], [], []
    page = 1
    last = None
    error = None
    try:
        while True:
            url = f'https://api.hguofichp.cn/machine/Page?pageNum={page}&pageSize={a.page_size}'
            for attempt in range(4):
                if last is not None:
                    time.sleep(max(0, a.interval - (time.monotonic() - last)))
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'lan-geng-downloader/1.0'})
                    with urllib.request.urlopen(req, timeout=60) as response:
                        raw = response.read()
                    payload = json.loads(raw)
                    if payload.get('code') != 200:
                        raise ValueError(str(payload))
                    data = payload['data']
                    batch, total = data['list'], int(data['total'])
                    assert isinstance(batch, list) and all('id' in r for r in batch)
                    break
                except Exception as exc:
                    if attempt == 3:
                        raise
                    print(f'Retry page {page}: {exc}', flush=True)
                finally:
                    last = time.monotonic()
            path = pages_dir / f'page-{page:04d}.json'
            path.write_bytes(raw)
            pages.append({'page_num': page, 'url': url, 'path': f'pages/{path.name}', 'records': len(batch), 'reported_total': total, 'last_page': data.get('lastPage'), 'fetched_at': now(), 'bytes': len(raw), 'sha256': sha(path)})
            rows.extend(batch)
            totals.append(total)
            print(f'Page {page}: {len(batch)} rows; collected {len(rows)}/{total}', flush=True)
            if data.get('lastPage') is True or page * a.page_size >= total:
                break
            if not batch:
                raise ValueError('Unexpected empty page')
            page += 1
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
    ids = collections.Counter(str(r['id']) for r in rows)
    texts = collections.Counter(r.get('barrage', '') for r in rows)
    tags = collections.Counter(t for r in rows for t in str(r.get('tags') or '').split(',') if t)
    total = totals[0] if totals else None
    checks = {'passed': error is None and bool(totals) and len(set(totals)) == 1 and len(ids) == len(rows) == total, 'unique_id_count_equals_total': len(ids) == total, 'row_count_equals_total': len(rows) == total, 'all_pages_report_same_total': bool(totals) and len(set(totals)) == 1, 'duplicate_id_count': sum(n - 1 for n in ids.values()), 'duplicate_ids': [i for i, n in ids.items() if n > 1], 'error': error}
    save(out / 'memes.json', rows)
    with (out / 'memes.jsonl').open('w', encoding='utf-8', newline='\n') as stream:
        for r in rows:
            stream.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')
    manifest = {'schema_version': 1, 'source_page': 'https://sb6657.cn/memes/AllBarrage', 'started_at': started, 'finished_at': now(), 'request_policy': {'serial': True, 'minimum_interval_seconds': a.interval, 'page_size': a.page_size, 'max_retries': 3}, 'expected_total': total, 'reported_totals': sorted(set(totals)), 'page_count': len(pages), 'record_count': len(rows), 'unique_id_count': len(ids), 'statistics': {'unique_barrage_count': len(texts), 'duplicate_barrage_extra_rows': sum(n - 1 for n in texts.values()), 'empty_barrage_count': sum(not r.get('barrage') for r in rows), 'tag_record_counts': dict(tags.most_common()), 'minimum_id': min((int(r['id']) for r in rows), default=None), 'maximum_id': max((int(r['id']) for r in rows), default=None)}, 'validation': checks, 'files': {n: {'bytes': (out / n).stat().st_size, 'sha256': sha(out / n)} for n in ('memes.json', 'memes.jsonl')}, 'pages': pages, 'notes': ['Raw page files preserve exact response bytes.', 'Live API has no snapshot isolation: changed totals or repeated IDs cause validation failure.']}
    save(out / 'manifest.json', manifest)
    print(json.dumps({k: manifest[k] for k in ('page_count', 'record_count', 'unique_id_count', 'expected_total', 'statistics', 'validation')}, ensure_ascii=False, indent=2), flush=True)
    return 0 if checks['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
