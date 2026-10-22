from pathlib import Path
import shutil
root=Path('outputs/V1.3.0')
shutil.copytree('outputs/V1.2.A1/frontend-github/node_modules',root/'frontend-github/node_modules',dirs_exist_ok=True)
p=root/'script/app.py';s=p.read_text(encoding='utf-8');s=s.replace('http://127.0.0.1:5000/api/v1/health',"http://127.0.0.1:{port}/api/v1/health").replace("urllib.request.urlopen('http://127.0.0.1:{port}/api/v1/health'","urllib.request.urlopen(f'http://127.0.0.1:{port}/api/v1/health'").replace("webbrowser.open('http://127.0.0.1:5000')","webbrowser.open(f'http://127.0.0.1:{port}')").replace(" import sys\n", " import sys\n port=int(os.getenv('DATAFLOW_PORT','5000'))\n").replace("port=5000,debug=False", "port=port,debug=False");p.write_text(s,encoding='utf-8')
p=root/'Start_V1.3.0.bat';s=p.read_text().replace('http://127.0.0.1:5000','http://127.0.0.1:5001').replace('echo Keep this window open. Close the old DataFlow server before starting.','echo Keep this window open.\nset "DATAFLOW_PORT=5001"');p.write_text(s)
print('Dependencies and launcher ready')
