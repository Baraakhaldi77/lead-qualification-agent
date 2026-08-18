@echo off
cd /d "%~dp0"
"C:\Python314\python.exe" -m agent.run --once >> agent.log 2>&1
