"""Generate four fictional retailer store-import datasets without touching a database."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "sample_data" / "store_import"
FIELDS = ("store_id", "store_name", "address", "status", "exception")
RETAILERS = (
    ("AURORA", "Aurora Demo Grocer", "SM"),
    ("BAYU", "Bayu Demo Hypermarket", "HM"),
    ("CEMPAKA", "Cempaka Demo Market", "MM"),
    ("DAMAI", "Damai Demo Retail", "SM"),
)
LOCATIONS = (
    ("Kuala Lumpur", "Wilayah Persekutuan"),
    ("Petaling Jaya", "Selangor"),
    ("Shah Alam", "Selangor"),
    ("George Town", "Pulau Pinang"),
    ("Ipoh", "Perak"),
    ("Johor Bahru", "Johor"),
    ("Melaka", "Melaka"),
    ("Seremban", "Negeri Sembilan"),
    ("Kuantan", "Pahang"),
    ("Kota Bharu", "Kelantan"),
    ("Kuching", "Sarawak"),
    ("Kota Kinabalu", "Sabah"),
)


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def store_rows(code):
    rows = []
    for number in range(1, 301):
        city, state = LOCATIONS[(number - 1) % len(LOCATIONS)]
        rows.append({
            "store_id": f"DEMO_{code}-{number:03d}",
            "store_name": f"{code.title()} Demo {city} {number:03d}",
            "address": f"Fictional Lot {number:03d}, Jalan Demo {((number - 1) % 20) + 1}, {city}, {state}, Malaysia (synthetic)",
            "status": "Inactive" if number % 20 == 0 else "Active",
            "exception": "true" if number % 25 == 0 else "false",
        })
    return rows


def build_files():
    files = {}
    retailers = []
    for code, name, service_type in RETAILERS:
        filename = f"demo_{code.lower()}_stores.csv"
        rows = store_rows(code)
        files[filename] = csv_bytes(rows)
        retailers.append({
            "name": name, "key": f"DEMO_{code}", "serviceType": service_type,
            "senderEmail": f"dataflow.{code.lower()}@example.com",
            "retailerEmail": f"retailer.{code.lower()}@example.com",
            "storesFile": filename, "storeCount": len(rows),
            "activeStores": 285, "inactiveStores": 15, "exceptionStores": 12,
        })
    invalid = [
        {"store_id": "DEMO_INVALID-001", "store_name": "Duplicate example one", "address": "Synthetic address", "status": "Active", "exception": "false"},
        {"store_id": "demo_invalid-001", "store_name": "Duplicate example two", "address": "Synthetic address", "status": "Active", "exception": "false"},
        {"store_id": "DEMO_INVALID-002", "store_name": "", "address": "Synthetic address", "status": "Active", "exception": "false"},
        {"store_id": "DEMO_INVALID-003", "store_name": "Invalid status example", "address": "Synthetic address", "status": "Unknown", "exception": "false"},
        {"store_id": "DEMO_INVALID-004", "store_name": "Invalid exception example", "address": "Synthetic address", "status": "Active", "exception": "maybe"},
    ]
    files["invalid_stores.csv"] = csv_bytes(invalid)
    updated = store_rows("AURORA")[0].copy()
    updated.update(store_name="Aurora Demo Kuala Lumpur Flagship", status="Inactive", address="Fictional Lot 001, Jalan Demo Renovation, Kuala Lumpur, Malaysia (synthetic)")
    files["aurora_update_existing_store.csv"] = csv_bytes([updated])
    manifest = {
        "synthetic": True,
        "description": "Fictional Malaysian retailers and addresses for DataFlow Hub development; no real businesses or personal information.",
        "retailerCount": 4, "storesPerRetailer": 300, "totalStores": 1200,
        "importColumns": list(FIELDS), "retailers": retailers,
        "fixtures": {
            "invalid_stores.csv": {"dataRows": 5, "expectedInvalidRows": 5, "expectedCanConfirm": False, "errorsByCsvLine": {"2": "Duplicate store_id (case-insensitive match with line 3)", "3": "Duplicate store_id (case-insensitive match with line 2)", "4": "Missing store_name", "5": "Invalid status", "6": "Invalid exception"}},
            "aurora_update_existing_store.csv": {"mode": "upsert", "requires": "Import demo_aurora_stores.csv first", "expectedAdded": 0, "expectedUpdated": 1, "expectedStoreCountAfter": 300, "expectedIdAndSuiteCodePreserved": True},
        },
        "sha256": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    files["retailers.json"] = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    return files


def generate(output):
    output = output.expanduser().resolve()
    if not output.is_relative_to(PROJECT_ROOT):
        raise ValueError("Output must stay inside data-flow-hub.")
    files = build_files()
    # Check every destination first, so a conflict never causes a partial write.
    for name, data in files.items():
        target = output / name
        if target.is_symlink():
            raise ValueError(f"Refusing symlink destination: {name}")
        if target.exists() and (not target.is_file() or target.read_bytes() != data):
            raise ValueError(f"Refusing to overwrite changed file: {name}. Choose a new output folder.")
    output.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        target = output / name
        if not target.exists():
            with target.open("xb") as stream:
                stream.write(data)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output folder inside data-flow-hub; existing changed files are never overwritten.")
    args = parser.parse_args()
    try:
        folder = generate(args.output)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Verified/generated four retailers x 300 stores in {folder}.")
