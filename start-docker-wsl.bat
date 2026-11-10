@echo off
setlocal
title ValuePilot - Ubuntu 26.04 Docker
echo ValuePilot starts inside WSL2 Ubuntu 26.04.
echo.
echo Open http://127.0.0.1:8765/ after the service starts.
echo Keep this window open while using ValuePilot.
echo Press Ctrl+C to stop the container.
echo.
wsl.exe -d Ubuntu -u root -- bash -lc "cd /home/kiran/ValuePilot && docker compose up --build"
if errorlevel 1 (
  echo.
  echo ValuePilot did not start successfully. Check Docker and Ubuntu logs.
  pause
)
endlocal
