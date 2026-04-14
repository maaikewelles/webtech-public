@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  py -m venv .venv || python -m venv .venv
)

echo Installing requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo Starting Flask app...
".venv\Scripts\python.exe" app.py
