@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run Setup_Windows.bat first.
  pause
  exit /b 1
)
docker compose up -d --wait
if errorlevel 1 (
  echo PostgreSQL did not start. Check Docker Desktop.
  pause
  exit /b 1
)
.venv\Scripts\python.exe script\app.py
pause
