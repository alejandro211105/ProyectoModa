@echo off
cd /d "%~dp0"
call venv\Scripts\activate
python servidor.py
pause