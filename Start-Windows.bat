@echo off
set "GETEDIT_LAUNCH_CWD=%CD%"
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
 ".venv\Scripts\python.exe" "app.py" %*
) else (
 py -3 "app.py" %*
)
if errorlevel 1 pause
