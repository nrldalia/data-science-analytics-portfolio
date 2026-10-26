"""Opt-in, additive demo loading through the normal DataFlow Hub API."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'sample_data' / 'store_import'
SETUP_FIELDS = ('name', 'key', 'serviceType', 'senderEmail', 'retailerEmail')
IMPORT_FIELDS = ('store_id', 'store_name', 'address', 'status', 'exception')


def load_plan():
    manifest = json.loads((FIXTURES / 'retailers.json').read_text(encoding='utf-8'))
    entries = manifest['retailers']
    if len(entries) != 4 or len({r['key'].casefold() for r in entries}) != 4:
        raise ValueError('Demo manifest must define four distinct retailers.')
    plans = []
    for entry in entries:
        path = (FIXTURES / entry['storesFile']).resolve()
        if path.parent != FIXTURES.resolve() or not path.is_file():
            raise ValueError('Demo CSV must be an existing file inside the fixture folder.')
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != manifest['sha256'][entry['storesFile']]:
            raise ValueError('Demo fixture fingerprint does not match its manifest.')
        reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
        rows = list(reader)
        if reader.fieldnames != list(IMPORT_FIELDS) or len(rows) != 300:
            raise ValueError('Each demo CSV must contain the five import columns and 300 stores.')
        if len({r['store_id'].casefold() for r in rows}) != 300:
            raise ValueError('Demo store IDs must be unique within each retailer.')
        if any(r['status'] not in ('Active', 'Inactive') or r['exception'] not in ('true', 'false') for r in rows):
            raise ValueError('Demo rows contain invalid status or exception values.')
        plans.append({'setup': {k: entry[k] for k in SETUP_FIELDS}, 'rows': rows})
    return plans


def api(client, method, path, **options):
    response = client.open('/api/v1' + path, method=method, **options)
    data = response.get_json(silent=True)
    if response.status_code >= 400 or not isinstance(data, dict) or not data.get('success'):
        raise ValueError(f'Demo API operation failed ({method}, HTTP {response.status_code}); no unrelated records were replaced. Correct the failure and rerun.')
    return data


def expected_store(row):
    return {'key': row['store_id'], 'name': row['store_name'], 'address': row['address'],
            'status': row['status'], 'exception': row['exception'] == 'true'}


def missing_stores(retailer, plan):
    key = plan['setup']['key']
    if retailer.get('archived'):
        raise ValueError(f'{key}: matching retailer is archived; nothing will be changed.')
    for field in SETUP_FIELDS:
        value = retailer.get(field, '')
        expected = plan['setup'][field]
        if (value.casefold() if field == 'key' else value) != (expected.casefold() if field == 'key' else expected):
            raise ValueError(f'{key}: existing retailer setup conflicts with the demo; nothing will be replaced.')
    desired = {r['store_id'].casefold(): expected_store(r) for r in plan['rows']}
    existing = retailer.get('stores', [])
    known = set()
    for store in existing:
        identity = store.get('key', '').casefold()
        if identity in known or identity not in desired:
            raise ValueError(f'{key}: existing stores conflict with the demo; nothing will be replaced.')
        known.add(identity)
        if any(store.get(field, '' if field == 'address' else None) != value
               for field, value in desired[identity].items() if field != 'key'):
            raise ValueError(f'{key}: existing store details conflict with the demo; nothing will be replaced.')
    return [row for row in plan['rows'] if row['store_id'].casefold() not in known]


def apply_demo(client, plans):
    """Preflight all retailers, then add missing stores; safe to resume after failure."""
    listings = api(client, 'GET', '/retailers')['retailers']
    by_key = {}
    for retailer in listings:
        by_key.setdefault(retailer['key'].casefold(), []).append(retailer)
    actions = []
    for plan in plans:
        key = plan['setup']['key']
        matches = by_key.get(key.casefold(), [])
        if len(matches) > 1:
            raise ValueError(f'{key}: multiple matching retailers; no demo loading started.')
        retailer = matches[0] if matches else None
        rows = missing_stores(retailer, plan) if retailer else plan['rows']
        actions.append((plan, retailer, rows))
    # The full preflight above prevents an existing conflict in retailer four
    # from creating or importing the first three retailers.
    created = added = reused = 0
    for plan, retailer, rows in actions:
        key = plan['setup']['key']
        if retailer is None:
            retailer = api(client, 'POST', '/retailers', json={**plan['setup'], 'stores': [], 'pipeline': []})['retailer']
            created += 1
        if not rows:
            reused += 1
            print(f'{key}: already has all 300 demo stores; unchanged.')
            continue
        previous_ids = {s['key'].casefold(): (s.get('id'), s.get('suiteCode')) for s in retailer.get('stores', [])}
        source = io.StringIO(newline='')
        writer = csv.DictWriter(source, fieldnames=IMPORT_FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        path = '/retailers/' + retailer['id'] + '/stores/import'
        preview = api(client, 'POST', path + '/preview',
                      data={'file': (io.BytesIO(source.getvalue().encode('utf-8')), 'demo_stores.csv'), 'mode': 'add'},
                      content_type='multipart/form-data')
        summary = preview['summary']
        if not preview['canConfirm'] or summary['errors'] or summary['added'] != len(rows) or summary['updated']:
            raise ValueError(f'{key}: import preview did not match the additive plan; no stores confirmed for this retailer.')
        confirmed = api(client, 'POST', path + '/confirm', json={'previewId': preview['previewId']})
        saved = confirmed['retailer']
        if missing_stores(saved, plan) or len(saved['stores']) != 300:
            raise ValueError(f'{key}: saved retailer did not match all 300 planned stores.')
        for store in saved['stores']:
            previous = previous_ids.get(store['key'].casefold())
            if previous and previous != (store.get('id'), store.get('suiteCode')):
                raise ValueError(f'{key}: an existing identity changed unexpectedly.')
        added += len(rows)
        print(f'{key}: added {len(rows)} stores; total 300.')
    return {'createdRetailers': created, 'addedStores': added, 'unchangedRetailers': reused}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Create only missing demo retailers/stores in the configured database. Never replaces conflicting data.')
    args = parser.parse_args()
    try:
        plans = load_plan()
        if not args.apply:
            for plan in plans:
                print(f"{plan['setup']['key']}: {plan['setup']['name']} — 300 stores")
            print('Plan only: four retailers, 1,200 stores. No application import or database connection was made. Use --apply to load missing demo data.')
            return 0
        # Deliberately delay importing Flask until explicit opt-in. Application
        # initialization may create tables; the default plan never does so.
        from app import app
        summary = apply_demo(app.test_client(), plans)
        print(f"Done: {summary['createdRetailers']} retailers created, {summary['addedStores']} stores added, {summary['unchangedRetailers']} retailers already complete.")
        return 0
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
