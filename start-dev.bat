@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   台股報價回放系統 - 開發模式啟動
echo ========================================
echo.

REM 檢查 Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 錯誤: 找不到 Node.js
    echo 請先安裝 Node.js: https://nodejs.org/
    pause
    exit /b 1
)

echo ✅ Node.js 已安裝
echo.

REM 檢查依賴
if not exist "server\nodejs\node_modules" (
    echo 📦 正在安裝後端依賴...
    cd server\nodejs
    call npm install
    cd ..\..
)

if not exist "frontend-app\node_modules" (
    echo 📦 正在安裝前端依賴...
    cd frontend-app
    call npm install
    cd ..
)

echo.
echo 🚀 啟動後端 (Port 5000)...
echo.
start "Stock Backend" cmd /k "cd server\nodejs && npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo 🎨 啟動前端 (Port 3000)...
echo.
start "Stock Frontend" cmd /k "cd frontend-app && npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   啟動完成！
echo ========================================
echo.
echo 後端: http://localhost:5000
echo 前端: http://localhost:3000
echo.
echo 瀏覽器會在 5 秒後自動開啟...
echo.

timeout /t 5 /nobreak >nul
start http://localhost:3000

echo 按任意鍵關閉此視窗...
pause >nul
