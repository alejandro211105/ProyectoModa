@echo off
cd /d "%~dp0"
git add .
set /p msg="Descripcion del commit: "
git commit -m "%msg%"
git push
pause