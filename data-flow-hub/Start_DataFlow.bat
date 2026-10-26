@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run Setup_Windows.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe script\configure_native_database.py --check
if errorlevel 1 (
  echo PostgreSQL is not ready. Check its Windows service and README.md.
  pause
  exit /b 1
)
.venv\Scripts\python.exe script\app.py
set "dataflow_exit=%errorlevel%"
pause
exit /b %dataflow_exit%
