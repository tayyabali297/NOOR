@echo off
cd /d %~dp0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8765 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
py -3.11 main.py
