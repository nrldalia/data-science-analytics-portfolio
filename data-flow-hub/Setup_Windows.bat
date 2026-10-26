@echo off
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 goto python_missing
where npm.cmd >nul 2>&1
if errorlevel 1 goto node_missing
if not exist .venv\Scripts\python.exe py -m venv .venv
if errorlevel 1 goto failed
if not exist .venv\Scripts\python.exe goto failed
.venv\Scripts\python.exe -m pip install -r script\requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe script\configure_native_database.py
if errorlevel 1 goto failed
call npm.cmd ci
if errorlevel 1 goto failed
call npm.cmd run build
if errorlevel 1 goto failed
echo Setup complete. Run Start_DataFlow.bat next.
pause
exit /b 0
:python_missing
echo Install Python 3.11 or 3.12 with Add Python to PATH selected.
pause
exit /b 1
:node_missing
echo Install Node.js 20.19+ or 22.12+ first. Reopen this launcher after installation.
pause
exit /b 1
:failed
echo Setup failed. Review the message above and the Windows PostgreSQL instructions in README.md.
pause
exit /b 1
