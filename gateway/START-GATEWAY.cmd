@echo off
setlocal
cd /d "%~dp0"
docker compose up -d
docker compose ps
pause
