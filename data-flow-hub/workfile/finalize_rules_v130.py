from pathlib import Path
root=Path('outputs/V1.3.0')
p=root/'frontend-github/src/RetailerSetup.jsx';s=p.read_text(encoding='utf-8')
a=s.index("  {view==='rules'&&<>\n   <section");start=s.index('   <section',a);end=s.index('   </section>',start)+len('   </section>')
selector=s[start:end];s=s[:start]+s[end:]
location=s.index('  <section className={card}><div className="flex flex-wrap justify-between gap-3"><div><h3 className="font-semibold">Upload Sample Data')
s=s[:location]+"  {view==='rules'&&"+selector.strip()+"}\n"+s[location:]
s=s.replace("category:data.rule.category}]", "category:data.rule.category,description:data.rule.defaults.description||`${data.rule.name} is used to prepare ${data.rule.category.toLowerCase()} data.`}]")
s=s.replace('value={rule.description||\'\'}', "value={rule.description||''}")
p.write_text(s,encoding='utf-8')
(root/'CHANGELOG_V1.3.0.md').write_text('''# V1.3.0 — Rules Configure table and conditions

Enhances V1.2.A1. Adds a single component dropdown above the sample area, followed vertically by the selected component's rule dropdown and Add Rules button. Only one component is selected at a time; each added rule appends one row.

The rules table uses Components, Description, Sequence, Condition and Edit columns. Descriptions explain the reason for each rule. Successful at Execution and Failure at Execution messages are prefilled and read-only. Edit opens the existing field/operation settings. Up/down arrows move rules across components; persistence, previews, exports and batch jobs use the exact displayed order.

Condition opens a popup with all rows, equal/not equal, numeric comparisons, inclusive between, text contains/begins/ends, and blank/not blank. Conditions gate which rows the operation applies to, using current values at that sequence step. Nonmatching rows are retained. Text matching is case-insensitive; numeric bounds are validated. Existing rules without conditions apply to all rows. Rule and component previews and the final example remain available.

No new error-code configuration is introduced; existing batch failure behavior is retained. V1.3.0 uses port 5001 via its launcher to coexist with V1.2.A1 on 5000. Local databases, uploaded samples and installed runtimes are excluded from GitHub snapshots.
''',encoding='utf-8')
(root/'README.md').write_text('''# DataFlow V1.3.0

Double-click Start_V1.3.0.bat and keep its window open. It opens http://127.0.0.1:5001/ when ready. The previous version can remain on port 5000. For a fresh checkout run Setup_Windows.bat first.

Open Retailer Data Setup → Rules Configure. Choose one Component, choose a Rule, then click Add Rules. Each click appends a table row. Use Edit to choose the field and operation settings, and the Description box to explain its purpose. Execution messages are prefilled.

Use Condition to open the popup. All rows removes any condition; other choices limit execution to matching rows. Comparisons use the data as it exists at this step. For example, sales greater than 100 applies the selected rule only to those rows. Conditions do not color cells or remove unmatched rows.

Move rows with the sequence arrows, including across Cleaning, Transformation and Validation. Save Configuration persists the displayed order, descriptions and conditions. Upload a sample smaller than 1 MB to inspect per-rule/component previews and the final example. Full batch jobs use the same saved sequence and conditions.

Source: frontend-github/src/RetailerSetup.jsx and script/retailer_setup.py. Build the frontend with npm run build; run python -m unittest discover -s script with an isolated temporary folder inside Codex for tests. Keep local databases and samples private.
''',encoding='utf-8')
(root/'VALIDATION.md').write_text('''# V1.3.0 validation

Production React/Vite/Tailwind build passed. All 37 backend tests passed, including seven new checks for matching-row execution, blank/text/numeric conditions, inclusive bounds, duplicate validation scope, invalid conditions, cross-component sequence and persisted descriptions/conditions. Existing retailer and batch audit/retry/replacement checks remain passing.

The in-app browser cannot reach a server started in this session's Windows sandbox on port 5001. Connection attempts returned refused/timed-out even after requesting network permission. Live interaction verification of the new UI remains unverified; launch Start_V1.3.0.bat directly from Windows for the user-hosted server. The prior V1.2.A1 browser verification is separate.
''',encoding='utf-8')
print('Release documentation and top selector finalized')
