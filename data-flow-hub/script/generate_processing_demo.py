"""Generate bounded, synthetic Priority 4 processing fixtures without database access."""
import argparse
import csv
import io
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STORE_SOURCE = PROJECT_ROOT / 'sample_data' / 'store_import' / 'demo_aurora_stores.csv'
DEFAULT_OUTPUT = PROJECT_ROOT / 'sample_data' / 'processing_demo'
FIELDS = ('store_id', 'sales', 'quantity')
MISSING_COUNTS = (0, 0, 5, 0, 10, 0, 15, 5)


def csv_bytes(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def roster():
    if not STORE_SOURCE.resolve().is_relative_to(PROJECT_ROOT):
        raise ValueError('Store source must remain inside data-flow-hub.')
    with STORE_SOURCE.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 300 or len({row['store_id'].casefold() for row in rows}) != 300:
        raise ValueError('Aurora store fixture must contain 300 distinct Store IDs.')
    active = [row['store_id'] for row in rows if row['status'] == 'Active']
    inactive = [row['store_id'] for row in rows if row['status'] == 'Inactive']
    if len(active) != 285 or len(inactive) != 15:
        raise ValueError('This demo requires the unchanged 285 Active / 15 Inactive Aurora roster.')
    return active, inactive


def record(store_id, ordinal, week_offset):
    # Illustrative values only: these are not real sales, prices or measured trends.
    return {'store_id': store_id, 'sales': f'{1000 + ordinal * 7 + week_offset * 23}.00',
            'quantity': str(12 + ordinal % 17 + week_offset)}


def expected(rows, active, inactive, *, week, invalid_lines=()):
    received = {row['store_id'].casefold() for row in rows}
    active_set = {key.casefold() for key in active}
    inactive_set = {key.casefold() for key in inactive}
    missing = [key for key in active if key.casefold() not in received]
    return {
        'businessPeriod': week, 'rowsReceived': len(rows),
        'expectedActiveStores': len(active), 'receivedExpectedActiveStores': len(active) - len(missing),
        'expectedCoveragePercent': round((len(active) - len(missing)) / len(active) * 100, 2),
        'missingExpectedStoreIds': missing,
        'unknownStoreIds': [row['store_id'] for row in rows if row['store_id'].casefold() not in active_set | inactive_set],
        'receivedInactiveStoreIds': [key for key in inactive if key.casefold() in received],
        'invalidNumericSalesCsvLines': list(invalid_lines),
    }


def build_files():
    active, inactive = roster()
    files = {}
    fixtures = {}
    for offset, missing in enumerate(MISSING_COUNTS):
        week = f'2026-W{37 + offset:02d}'
        chosen = active if not missing else active[:-missing]
        rows = [record(key, number, offset) for number, key in enumerate(chosen, 1)]
        name = f'aurora_{week}.csv'
        files[name] = csv_bytes(rows)
        fixtures[name] = expected(rows, active, inactive, week=week)
        fixtures[name]['intendedOutcome'] = 'Numeric sales rule passes; review reconciliation before deliberate approval.'
    failed = [record(key, number, 0) for number, key in enumerate(active[:10], 1)]
    for index, value in ((1, 'not-a-number'), (4, ''), (8, 'invalid-sales')):
        failed[index]['sales'] = value
    files['failed_numeric.csv'] = csv_bytes(failed)
    fixtures['failed_numeric.csv'] = expected(failed, active, inactive, week='2026-W44', invalid_lines=(3, 6, 10))
    fixtures['failed_numeric.csv']['intendedOutcome'] = 'Sales numeric validation fails; investigate exceptions and fix a copied file or rule before another run. Never approve a cancelled run.'
    exceptional = [record(key, number, 7) for number, key in enumerate(active[:-10], 1)]
    exceptional += [record(inactive[0], 286, 7), record('DEMO_AURORA-UNKNOWN', 287, 7)]
    files['unknown_store.csv'] = csv_bytes(exceptional)
    fixtures['unknown_store.csv'] = expected(exceptional, active, inactive, week='2026-W44')
    fixtures['unknown_store.csv']['intendedOutcome'] = 'Numeric rule passes; inspect one unknown store, one inactive known store, and ten missing active stores. Received unique IDs 277 must not inflate coverage above 275/285.'
    manifest = {
        'synthetic': True,
        'description': 'Operational processing examples only; sales and quantity are invented values, not financial performance evidence.',
        'retailerKey': 'DEMO_AURORA', 'retailerName': 'Aurora Demo Grocer',
        'sourceStoreFile': 'sample_data/store_import/demo_aurora_stores.csv',
        'columns': list(FIELDS), 'expectedRosterPolicy': 'Unchanged demo roster: 285 Active, 15 Inactive; each run must retain its own launch snapshot.',
        'suggestedRule': {'id': 'processing-demo-sales-numeric', 'name': 'Convert sales to number', 'category': 'Transformation',
                          'operation': 'numeric', 'field': 'sales', 'description': 'Validate and convert the synthetic sales field without inventing missing amounts.'},
        'weeklyFiles': [name for name in files if name.startswith('aurora_')],
        'fixtures': fixtures,
    }
    files['manifest.json'] = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    return files


def generate(output):
    output = output.expanduser().resolve()
    if not output.is_relative_to(PROJECT_ROOT):
        raise ValueError('Output must remain inside data-flow-hub.')
    files = build_files()
    for name, data in files.items():
        target = output / name
        if target.is_symlink():
            raise ValueError(f'Refusing symlink destination:{name}')
        if target.exists() and (not target.is_file() or target.read_bytes().replace(b'\r\n', b'\n') != data):
            raise ValueError(f'Refusing to overwrite changed file:{name}. Choose a new output folder.')
    output.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        target = output / name
        if not target.exists():
            with target.open('xb') as stream:
                stream.write(data)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        path = generate(args.output)
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')
    print(f'Generated 8 weekly files and 2 exception files in {path}. No database connection or approvals were made.')
