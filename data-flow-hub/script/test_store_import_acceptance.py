"""Independent acceptance checks for retailer-scoped imports and store management.

Run through check_postgres.py so all application writes use a disposable schema.
"""
import csv
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import unittest
import uuid

from openpyxl import load_workbook
import test_app as fixtures
from database import get_db_connection
from load_store_demo import apply_demo, load_plan

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / 'sample_data' / 'store_import'
HEADERS = ['store_id', 'store_name', 'address', 'status', 'exception']


class StoreImportAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.client = fixtures.module.app.test_client()

    def create_retailer(self, metadata=None):
        body = {k: v for k, v in (metadata or {}).items()
                if k in ('name', 'key', 'serviceType', 'senderEmail', 'retailerEmail')}
        body.setdefault('name', 'Acceptance retailer')
        body['key'] = body.get('key', 'ACCEPTANCE') + '_' + uuid.uuid4().hex[:8]
        body.setdefault('serviceType', 'SM')
        body.setdefault('senderEmail', 'qa@example.com')
        body.update(stores=[], pipeline=[])
        result = self.client.post('/api/v1/retailers', json=body)
        self.assertEqual(result.status_code, 200, result.data)
        return result.json['retailer']

    def preview(self, retailer, content, mode='add', filename='stores.csv'):
        result = self.client.post(
            f"/api/v1/retailers/{retailer['id']}/stores/import/preview",
            data={'file': (io.BytesIO(content), filename), 'mode': mode})
        self.assertEqual(result.status_code, 200, result.data)
        return result.json

    def confirm(self, retailer, preview):
        return self.client.post(
            f"/api/v1/retailers/{retailer['id']}/stores/import/confirm",
            json={'previewId': preview['previewId']})

    def stores(self, retailer, **query):
        result = self.client.get(f"/api/v1/retailers/{retailer['id']}/stores", query_string=query)
        self.assertEqual(result.status_code, 200, result.data)
        return result.json

    @staticmethod
    def csv_bytes(rows):
        stream = io.StringIO(newline='')
        writer = csv.writer(stream)
        writer.writerow(HEADERS)
        writer.writerows(rows)
        return stream.getvalue().encode('utf-8')

    def test_four_retailers_with_300_stores_then_review_update_and_pagination(self):
        manifest = json.loads((DEMO / 'retailers.json').read_text())
        self.assertEqual(len(manifest['retailers']), 4)
        codes, identities = set(), set()
        for metadata in manifest['retailers']:
            with self.subTest(retailer=metadata['key']):
                retailer = self.create_retailer(metadata)
                preview = self.preview(retailer, (DEMO / metadata['storesFile']).read_bytes())
                self.assertTrue(preview['canConfirm'])
                self.assertEqual(preview['summary'], dict(total=300, added=300, updated=0, unchanged=0, errors=0))
                # Preview itself must not write stores.
                self.assertEqual(self.stores(retailer)['total'], 0)
                result = self.confirm(retailer, preview)
                self.assertEqual(result.status_code, 200, result.data)
                imported = result.json['retailer']['stores']
                self.assertEqual(len(imported), 300)
                codes.update(s['suiteCode'] for s in imported)
                identities.update(s['id'] for s in imported)
                first = self.stores(retailer, page=1, pageSize=25)
                last = self.stores(retailer, page=12, pageSize=25)
                self.assertEqual(first['total'], 300)
                self.assertEqual(last['page'], 12)
                self.assertEqual(len(last['stores']), 25)
                self.assertFalse({s['id'] for s in first['stores']} & {s['id'] for s in last['stores']})
                self.assertEqual(self.stores(retailer, status='Active')['total'], metadata['activeStores'])
                self.assertEqual(self.stores(retailer, status='Inactive')['total'], metadata['inactiveStores'])
                target = imported[173]
                found = self.stores(retailer, q=target['key'].lower())
                self.assertEqual([s['id'] for s in found['stores']], [target['id']])
                descending = self.stores(retailer, sort='name', direction='desc', pageSize=100)
                names = [s['name'].casefold() for s in descending['stores']]
                self.assertEqual(names, sorted(names, reverse=True))
                # The same file is now a no-op in upsert mode, and an error in add mode.
                again = self.preview(retailer, (DEMO / metadata['storesFile']).read_bytes(), mode='upsert')
                self.assertFalse(again['canConfirm'])
                self.assertEqual(again['summary']['unchanged'], 300)
                update = self.preview(retailer, self.csv_bytes([
                    [target['key'], 'Updated acceptance branch', target['address'], 'Inactive', 'true']
                ]), mode='upsert')
                self.assertEqual(update['summary']['updated'], 1)
                updated = self.confirm(retailer, update)
                self.assertEqual(updated.status_code, 200, updated.data)
                after = {s['key']: s for s in updated.json['retailer']['stores']}
                self.assertEqual(len(after), 300)
                self.assertEqual(after[target['key']]['id'], target['id'])
                self.assertEqual(after[target['key']]['suiteCode'], target['suiteCode'])
                self.assertEqual(after[target['key']]['name'], 'Updated acceptance branch')
                self.assertEqual(after[imported[0]['key']], imported[0])
        self.assertEqual(len(codes), 1200)
        self.assertEqual(len(identities), 1200)

    def test_store_ids_are_retailer_scoped_and_preview_cannot_cross_retailers(self):
        first, second = self.create_retailer(), self.create_retailer()
        content = self.csv_bytes([['SHARED-001', 'Same business ID', 'Synthetic', 'Active', 'false']])
        p1, p2 = self.preview(first, content), self.preview(second, content)
        wrong = self.confirm(second, p1)
        self.assertEqual(wrong.status_code, 404)
        r1, r2 = self.confirm(first, p1), self.confirm(second, p2)
        self.assertEqual(r1.status_code, 200, r1.data)
        self.assertEqual(r2.status_code, 200, r2.data)
        s1, s2 = r1.json['retailer']['stores'][0], r2.json['retailer']['stores'][0]
        self.assertEqual(s1['key'], s2['key'])
        self.assertNotEqual(s1['id'], s2['id'])
        self.assertNotEqual(s1['suiteCode'], s2['suiteCode'])
        self.assertEqual(self.confirm(first, p1).status_code, 409)
        self.assertEqual(self.stores(first)['total'], 1)
        self.assertEqual(self.stores(second)['total'], 1)

    def test_invalid_preview_is_atomic_and_error_export_is_spreadsheet_safe(self):
        retailer = self.create_retailer()
        invalid = self.preview(retailer, (DEMO / 'invalid_stores.csv').read_bytes())
        self.assertFalse(invalid['canConfirm'])
        self.assertEqual(invalid['summary']['errors'], 5)
        self.assertTrue(all(row['errors'] for row in invalid['rows']))
        self.assertEqual(self.confirm(retailer, invalid).status_code, 400)
        self.assertEqual(self.stores(retailer)['total'], 0)
        dangerous = self.preview(retailer, self.csv_bytes([
            ['BAD-001', '=1+1', 'Synthetic', 'Unknown', 'false']]))
        response = self.client.get(f"/api/v1/retailers/{retailer['id']}/stores/import/{dangerous['previewId']}/errors")
        self.assertEqual(response.status_code, 200, response.data)
        rows = list(csv.reader(io.StringIO(response.data.decode('utf-8-sig'))))
        self.assertTrue(any("'=1+1" in cell for row in rows for cell in row))
        self.assertFalse(any(cell.lstrip().startswith(('=', '+', '-', '@')) for row in rows for cell in row))

    def test_stale_or_archived_config_requires_new_preview(self):
        retailer = self.create_retailer()
        content = self.csv_bytes([['GUARD-001', 'Guarded', '', 'Active', 'false']])
        old = self.preview(retailer, content)
        edited = self.client.put(f"/api/v1/retailers/{retailer['id']}", json={**retailer, 'name': 'Edited after preview'})
        self.assertEqual(edited.status_code, 200, edited.data)
        self.assertEqual(self.confirm(retailer, old).status_code, 409)
        fresh = self.preview(retailer, content)
        archived = self.client.post('/api/v1/retailers/archive', json={'ids': [retailer['id']]})
        self.assertEqual(archived.status_code, 200, archived.data)
        self.assertEqual(self.confirm(retailer, fresh).status_code, 409)
        self.assertEqual(self.stores(retailer)['total'], 0)

    @staticmethod
    def demo_plans():
        plans = load_plan()
        suffix = '_' + uuid.uuid4().hex[:8]
        for plan in plans:
            plan['setup']['key'] += suffix
        return plans

    @staticmethod
    def allocation_state():
        with get_db_connection() as db:
            return {
                'retailers': db.execute('SELECT COUNT(*) FROM retailer_configs').fetchone()[0],
                'versions': db.execute('SELECT COUNT(*) FROM retailer_configuration_versions').fetchone()[0],
                'codes': db.execute('SELECT COUNT(*) FROM store_code_registry').fetchone()[0],
                'sequence': db.execute('SELECT last_value FROM store_code_sequence WHERE id=1').fetchone()[0],
                'previews': db.execute('SELECT COUNT(*) FROM store_import_previews').fetchone()[0],
            }

    def test_demo_loader_repeat_does_not_allocate_codes_or_write_versions(self):
        plans = self.demo_plans()
        with redirect_stdout(io.StringIO()):
            first = apply_demo(self.client, plans)
        self.assertEqual(first, dict(createdRetailers=4, addedStores=1200, unchangedRetailers=0))
        keys = {p['setup']['key'] for p in plans}
        response = self.client.get('/api/v1/retailers')
        self.assertEqual(response.status_code, 200, response.data)
        saved = {r['key']: r for r in response.json['retailers'] if r['key'] in keys}
        self.assertEqual(len(saved), 4)
        self.assertTrue(all(len(r['stores']) == 300 for r in saved.values()))
        before = self.allocation_state()
        with redirect_stdout(io.StringIO()):
            second = apply_demo(self.client, plans)
        self.assertEqual(second, dict(createdRetailers=0, addedStores=0, unchangedRetailers=4))
        self.assertEqual(self.allocation_state(), before)
        response = self.client.get('/api/v1/retailers')
        reread = {r['key']: r for r in response.json['retailers'] if r['key'] in keys}
        self.assertEqual(reread, saved)

    def test_demo_loader_conflict_in_fourth_retailer_prevents_partial_loading(self):
        plans = self.demo_plans()
        # The first three do not exist; the last conflicts. Full preflight must
        # discover that before creating any of the first three or their stores.
        response = self.client.post('/api/v1/retailers', json={
            **plans[-1]['setup'], 'name': 'Existing unrelated business',
            'stores': [], 'pipeline': [],
        })
        self.assertEqual(response.status_code, 200, response.data)
        conflicting = response.json['retailer']
        before = self.allocation_state()
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'conflicts'):
            apply_demo(self.client, plans)
        self.assertEqual(self.allocation_state(), before)
        response = self.client.get('/api/v1/retailers')
        keys = {p['setup']['key'] for p in plans}
        matching = [r for r in response.json['retailers'] if r['key'] in keys]
        self.assertEqual(matching, [conflicting])

    def test_templates_are_downloadable_and_xlsx_import_preserves_text_identifiers(self):
        csv_response = self.client.get('/api/v1/store-template?format=csv')
        self.assertEqual(csv_response.status_code, 200)
        self.assertEqual(next(csv.reader(io.StringIO(csv_response.data.decode('utf-8-sig')))), HEADERS)
        response = self.client.get('/api/v1/store-template?format=xlsx')
        self.assertEqual(response.status_code, 200)
        book = load_workbook(io.BytesIO(response.data))
        try:
            self.assertEqual(list(next(book.active.values)), HEADERS)
            book.active.append(['00123', 'Zero prefix branch', '', 'Inactive', False])
            stream = io.BytesIO()
            book.save(stream)
        finally:
            book.close()
        retailer = self.create_retailer()
        preview = self.preview(retailer, stream.getvalue(), filename='stores.xlsx')
        self.assertTrue(preview['canConfirm'])
        result = self.confirm(retailer, preview)
        self.assertEqual(result.status_code, 200, result.data)
        store = result.json['retailer']['stores'][0]
        self.assertEqual(store['key'], '00123')
        self.assertEqual(store['status'], 'Inactive')
        self.assertIs(store['exception'], False)


if __name__ == '__main__':
    unittest.main()
