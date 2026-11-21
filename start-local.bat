@echo off
cd /d "%~dp0"
echo Iniciando servidor local em http://localhost:8080 ...
start "" http://localhost:8080/
python backend\app.py
