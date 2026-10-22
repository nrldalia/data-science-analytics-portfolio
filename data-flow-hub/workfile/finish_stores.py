from pathlib import Path
root=Path('outputs/V1.4.A1')
p=root/'frontend-github/src/RetailerSetup.jsx';s=p.read_text(encoding='utf-8')
s=s.replace('disabled={busy} className={button} onClick={()=>selectRetailer', "disabled={busy||view==='store'} className={button} onClick={()=>selectRetailer")
s=s.replace('disabled={busy} className={primary} onClick={()=>save()}', "disabled={busy||view==='store'} className={primary} onClick={()=>save()}")
s=s.replace('disabled={busy} onChange={e=>selectRetailer', "disabled={busy||view==='store'} onChange={e=>selectRetailer")
s=s.replace('onClick={()=>setView(', "disabled={view==='store'} onClick={()=>setView(")
s=s.replace('Store saved. SUITE storecode assigned and retailer key updated.', 'Store details saved.')
p.write_text(s,encoding='utf-8')
(root/'CHANGELOG_V1.4.A1.md').write_text('''# V1.4.A1 — Store Table Management

Amends V1.4.0. Replaces the inline store inputs with Retailer Store ID, Retailer Store Name, SUITE Storecode, Active, Inactive and Edit columns. Status indicators are mutually exclusive. The pencil opens a separate store edit page; Add Store opens the same page with a new draft.

The page prefills the retailer name and shared retailer key. Includes editable Store ID, Store Name and Store Address, Active/Inactive and exception Yes/No radio choices, and a read-only SUITE Storecode. As confirmed by the user, Retailer Key updates the retailer's shared key for all its stores. Save Store persists the retailer/store data and returns to the table; Cancel/Back discard the store draft. Store saves require valid retailer information and rule configuration.

The server assigns each saved store an immutable identity and a SUITE-prefixed UUID storecode. Updates preserve the code even if the Store ID or shared retailer key changes, ignoring caller attempts to overwrite it. New codes are distinct; invalid or reused identities are rejected. Existing legacy stores receive codes on their next save, defaulting to Active, no exception and an empty optional address. Shared-key uniqueness conflicts roll back atomically.

Preserves Rules Configuration popups, batch audit codes and compact Data Streams icons. The existing single V1.3.A1.bat entry point now launches V1.4.A1 on port 5001. Local data is copied via a consistent SQLite backup and excluded from GitHub.
''',encoding='utf-8')
(root/'README.md').write_text('''# DataFlow V1.4.A1

Close the previous server window and open the existing single V1.3.A1.bat launcher. It now opens V1.4.A1 at http://127.0.0.1:5001/. Keep its window open. Fresh checkouts: run Setup_Windows.bat and Start_V1.4.A1.bat.

In Retailer Data Setup, Store Table Management shows Retailer Store ID, Retailer Store Name, SUITE Storecode, Active, Inactive and Edit. Click Add Store or a row's pencil to open the store page.

Retailer Name is prefilled. Retailer Key is editable and shared across all stores under that retailer. Set Store ID, Store Name, optional Store Address, Active/Inactive and exception Yes/No. Save Store persists the changes and generates a read-only SUITE Storecode for a new store. Future edits keep that code. Cancel or Back discards the draft.

Existing stores without storecodes receive them on the next save. Codes use SUITE- plus a UUID. Store IDs remain unique within a retailer; retailer keys remain unique across retailers. A duplicate-key error leaves saved data unchanged.

Rules Configuration and Data Streams features from V1.4.0 remain included.
''',encoding='utf-8')
print('Store page controls and documentation finalized')
