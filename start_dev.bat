@echo off
echo ====================================
echo Stock Quote Playback System
echo ====================================
echo.
echo Starting Node.js backend server...
echo.

cd server\nodejs
start cmd /k "npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo Starting React frontend...
echo.

cd ..\..\frontend-app
start cmd /k "npm run dev"

echo.
echo ====================================
echo Both servers are starting...
echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:3000
echo ====================================
