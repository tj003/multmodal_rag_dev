@echo off

:: Get the directory where this script is located
cd /d "%~dp0"

echo Starting Redis (Docker)...
start cmd /k "cd /d "%~dp0redis" && docker-compose -f docker-compose.yaml up"

echo Waiting for Redis to start...
timeout /t 3 /nobreak > nul

echo Starting Celery Worker...
start cmd /k "cd /d "%~dp0" && venv\Scripts\activate && celery -A src.services.celery:celery_app worker --loglevel=info --pool=solo"

echo Starting API Server (Uvicorn)...
start cmd /k "cd /d "%~dp0" && venv\Scripts\activate && uvicorn src.server:app --reload --host 0.0.0.0 --port 8000"

echo All 3 servers started!