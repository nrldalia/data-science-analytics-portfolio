import csv,json,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'outputs/V1.5.0/script'))
from retailer_setup import apply_pipeline
from batch_metrics import input_metrics,received_metrics
folder=root/'outputs/V1.5.0_Sample_Data'
def load(name):
 with (folder/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
settings=[('Cleaning','trim','Store Name',{}),('Cleaning','trim','SKU',{}),('Cleaning','trim','Category',{}),('Cleaning','uppercase','SKU',{}),('Cleaning','lowercase','Category',{}),('Cleaning','replace','Product Name',{'find':'St.','replacement':'Street'}),('Transformation','numeric','Sales',{}),('Transformation','date','Sale Date',{'dateFormat':'%d/%m/%Y'}),('Validation','required','Store ID',{}),('Validation','range','Sales',{'min':'0','max':'10000'}),('Validation','pattern','SKU',{'pattern':'SKU-*'}),('Validation','unique','Transaction ID',{})]
pipeline=[dict(id=f'TEST-{i}',name=op,category=category,operation=op,field=field,**extra) for i,(category,op,field,extra) in enumerate(settings,1)]
sizes=json.loads((root/'work/sample_data_manifest.json').read_text())
for entry in sizes:
 assert entry['bytes']<1_000_000
 assert len(load(entry['name']))==entry['rows']
for name in ['V1.5.0_Rules_Sample.csv','V1.5.0_Batch_2026-W40.csv','V1.5.0_Batch_2026-W41.csv','V1.5.0_Batch_2026-W42.csv']:
 records=load(name);out,steps,issues,trace=apply_pipeline(records,pipeline)
 assert not issues,(name,issues)
 assert len(out)==len(records)
 assert out[0]['SKU']=='SKU-100'
 assert out[0]['Category']=='dairy'
 assert not out[0]['Store Name'].startswith(' ')
bad=load('V1.5.0_Failure_Test_2026-W41.csv')
_,_,issues,_=apply_pipeline(bad,pipeline)
assert len(issues)>=6,issues
stores=[dict(key=id,name=name) for id,name in [('S001','MY6 Mart Central'),('S002','MY6 Mart North'),('S003','MY6 Mart South')]]
base=(folder/'V1.5.0_Batch_2026-W40.csv').read_bytes();main=(folder/'V1.5.0_Batch_2026-W41.csv').read_bytes();small=(folder/'V1.5.0_Batch_2026-W42.csv').read_bytes()
m=input_metrics(main,'2026-W41',stores,{'source':base});received_metrics(m,load('V1.5.0_Batch_2026-W41.csv'))
assert m['rowsReceived']==30 and m['storesReceived']==3
assert [s['key'] for s in m['newStores']]==['S004'] and [s['key'] for s in m['missingStores']]==['S003']
assert m['fileSizeDeviationBytes']>0
n=input_metrics(small,'2026-W42',stores+[dict(key='S004',name='MY6 Mart East')],{'source':main});received_metrics(n,load('V1.5.0_Batch_2026-W42.csv'))
assert n['fileSizeDeviationBytes']<0 and not n['newStores']
guide='''# V1.5.0 sample-data testing guide

All files contain synthetic MY6 Mart sales data. No real retailer or customer data is included. All CSVs are below 1 MB. Upload the sales CSVs as-is; leading/trailing spaces, lowercase SKUs and text dates are deliberate.

## 1. Create the test retailer

Retailer Name: MY6 Test Mart
Retailer Key: MY6_TEST
Service Type: MM
Sender Email: tester@example.com (synthetic contact)
Retailer Email: leave blank

Use V1.5.0_Store_Table_Reference.csv as a manual reference when adding S001, S002 and S003 in Store Table Management. All three are Active, Exception No. The application generates SUITE codes. Do not add S004 yet: it is the new-store test. The reference CSV is not a sales batch or an automatic store import.

## 2. Create the rules

Upload V1.5.0_Rules_Sample.csv in Rules Configure. Add these executable rules in the order below. Enter any description you want. Use the separate Condition editor to select the field and settings. Apply each rule to all rows (no row filter).

| Sequence | Component | Dropdown rule | Field | Settings |
|---|---|---|---|---|
| 1 | Cleaning | Trim whitespace | Store Name | — |
| 2 | Cleaning | Trim whitespace | SKU | — |
| 3 | Cleaning | Trim whitespace | Category | — |
| 4 | Cleaning | Uppercase text | SKU | — |
| 5 | Cleaning | Lowercase text | Category | — |
| 6 | Cleaning | Replace text | Product Name | Find St.; replace with Street |
| 7 | Transformation | Convert to number | Sales | — |
| 8 | Transformation | Standardise date | Sale Date | Source date format %d/%m/%Y |
| 9 | Validation | Required value | Store ID | — |
| 10 | Validation | Numeric range | Sales | Minimum 0; maximum 10000 |
| 11 | Validation | Text pattern | SKU | SKU-* |
| 12 | Validation | Unique values | Transaction ID | — |

Check the previews, then click Save Configuration. The successful preview contains 8 rows, uppercase SKUs, lowercase categories, trimmed names, numeric Sales and ISO dates. Do not use Unique values on Store ID: multiple transactions per store are expected. Select executable operations rather than entries marked Reference only.

## 3. Run the weekly jobs

In Data Streams, choose MY6 Test Mart and upload each file with its matching ISO period. Leave the Store ID override blank: the Store ID header is detected automatically.

1. V1.5.0_Batch_2026-W40.csv — period 2026-W40. Expect 20 rows before/after cleaning, 3 received stores, no new/missing stores and no previous-week deviation baseline.
2. V1.5.0_Batch_2026-W41.csv — period 2026-W41. Expect 30 rows before/after cleaning, 3 received stores, New Store S004, Missing Store S003, Store Table + New Stores = 4, and a file-size increase. Open the audit pencil before approval to inspect the flags. Then approve this job; S004 enters the store table with its generated MY6 code. S003 remains registered.
3. V1.5.0_Batch_2026-W42.csv — period 2026-W42. After approving W41, expect 10 rows before/after cleaning, 3 received stores, no new stores, Missing Store S003 and a file-size decrease against W41.

These executable cleaning rules change values, not the number of rows, so received and post-cleaning counts intentionally match.

## 4. Test failure and cancelled replacement

After W41 has completed, upload V1.5.0_Failure_Test_2026-W41.csv to the same retailer and period 2026-W41. It includes a duplicate Transaction ID, blank Store ID, bad SKU, impossible date, nonnumeric Sales and negative Sales. With the recommended sequence, numeric Sales conversion fails first and the job cancels after three attempts. The previous completed/approved W41 job remains, with cancelled reprocess error codes shown in the log. Cancelled jobs have no end time or audit.

To test each validation independently, upload the failure file as a Rules Configure sample and inspect previews. For batch testing, fix earlier failures in a copy before expecting a later rule to run. Restore the successful sample afterward. Do not overwrite the supplied originals.

## Verified file sizes and audit deviations

'''
for entry in sizes:guide+=f"- {entry['name']}: {entry['rows']} data rows, {entry['bytes']} bytes.\n"
guide+=f"\nW41 versus W40: +{m['fileSizeDeviationBytes']} bytes (+{m['fileSizeDeviationPercent']}%).\nW42 versus W41: {n['fileSizeDeviationBytes']} bytes ({n['fileSizeDeviationPercent']}%).\n\nThe generated files were checked with the V1.5.0 rule execution and audit metric functions. Interactive processing in your running browser has not been performed.\n"
(folder/'V1.5.0_Testing_Guide.md').write_text(guide,encoding='utf-8')
with zipfile.ZipFile(root/'outputs/V1.5.0_Sample_Data.zip','w',zipfile.ZIP_DEFLATED) as z:
 for file in sorted(folder.iterdir()):z.write(file,file.name)
print(json.dumps(dict(files=len(sizes),failureFindings=len(issues),increase=m['fileSizeDeviationBytes'],decrease=n['fileSizeDeviationBytes'],verified=True)))
