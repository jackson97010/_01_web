@echo off
echo ======================================
echo Stock Quote Playback Server Launcher
echo ======================================
echo.

REM Check and kill any process using port 5000
echo Checking port 5000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    echo Found process using port 5000 (PID: %%a)
    echo Killing process...
    taskkill /F /PID %%a >nul 2>&1
    timeout /t 2 /nobreak >nul
)

echo Port 5000 is now available.
echo.
echo Starting server...
echo.

REM Start the server
npm run dev
