@echo off
echo ================================================================================
echo 啟動開發環境
echo ================================================================================
echo.

REM 檢查是否需要轉換資料
if not exist "frontend\static\api\20251031" (
    echo [1/3] 轉換資料...
    python scripts\convert_to_json.py
    echo.
) else (
    echo [1/3] 資料已存在，跳過轉換
    echo.
)

echo [2/3] 啟動後端 (http://localhost:5000)
echo.
start "後端 Server" cmd /k "cd server\nodejs && npm run dev"

timeout /t 3 /nobreak > nul

echo [3/3] 啟動前端 (http://localhost:3000)
echo.
start "前端 Server" cmd /k "cd frontend-app && npm run dev"

echo.
echo ================================================================================
echo 開發環境啟動完成！
echo.
echo 後端: http://localhost:5000
echo 前端: http://localhost:3000
echo.
echo 請稍候幾秒等待服務啟動，然後開啟瀏覽器訪問:
echo http://localhost:3000
echo.
echo 按任意鍵開啟瀏覽器...
echo ================================================================================
pause > nul

start http://localhost:3000
