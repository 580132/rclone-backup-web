@echo off
echo Starting backup-web application in Docker mode...
echo.

echo Building and starting containers...
docker-compose up -d --build

echo.
echo Waiting for containers to start...
timeout /t 10 /nobreak > nul

echo.
echo Checking container status...
docker-compose ps

echo.
echo Application should be available at: http://localhost:5000
echo.
echo To view logs, run: docker-compose logs -f
echo To stop containers, run: docker-compose down
