@echo off

:: Get the directory where this script is located
cd /d "%~dp0"

echo Stopping Celery Worker...
taskkill /f /fi "WINDOWTITLE eq celery*" >nul 2>&1
taskkill /f /im "celery.exe" >nul 2>&1
echo Celery stopped (or was not running)

echo Stopping Redis (Docker)...
cd /d "%~dp0redis"
docker-compose -f docker-compose.yaml down
cd /d "%~dp0"

echo Stopping API Server (Uvicorn)...
taskkill /f /fi "WINDOWTITLE eq uvicorn*" >nul 2>&1
taskkill /f /im "uvicorn.exe" >nul 2>&1
echo Uvicorn stopped (or was not running)

echo All servers stopped!
timeout /t 2 /nobreak > nul
exit