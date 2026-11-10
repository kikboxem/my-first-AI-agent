@echo off
setlocal
cd /d "%~dp0"
set "VALUEPILOT_LOCAL_MODE=1"
set "PORT=8765"
if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  echo First-run setup: creating a local Python environment...
  py -3 -m venv .venv
  if errorlevel 1 (
    echo Could not create a Python environment. Install Python 3.11+.
    pause
    exit /b 1
  )
  set "PY=.venv\Scripts\python.exe"
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
  )
)
echo.
echo ValuePilot is running privately on your computer.
echo Open: http://127.0.0.1:8765
echo CSV analysis works fully offline. The other tools use local Ollama if running.
echo Press Ctrl+C to stop.
echo.
"%PY%" app.py
endlocal
