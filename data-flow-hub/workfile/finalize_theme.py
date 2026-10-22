from pathlib import Path
import sqlite3
root=Path(__file__).resolve().parent.parent
source=root/'outputs/V1.14.0/script/dataflow.db'
target=root/'outputs/V1.14.A1/script/dataflow.db'
if source.exists():
    with sqlite3.connect(source) as old,sqlite3.connect(target) as new:old.backup(new)
launcher=root/'outputs/V1.3.A1.bat'
launcher.write_text(launcher.read_text(encoding='utf-8-sig').replace('V1.14.0','V1.14.A1').replace('1.14.0','1.14.A1'),encoding='utf-8')
print('Preserved local data and updated the single launcher to V1.14.A1.')
