@echo off
echo ================================================================================
echo 啟動開發環境（Parquet 即時轉換模式）
echo ================================================================================
echo.

echo [1/2] 啟動 Parquet Server (http://localhost:5000)
echo.
start "Parquet Server" cmd /k "cd server\python && python parquet_server.py --port 5000"

timeout /t 3 /nobreak > nul

echo [2/2] 啟動前端 (http://localhost:3000)
echo.
start "前端 Server" cmd /k "cd frontend-app && npm run dev"

echo.
echo ================================================================================
echo 開發環境啟動完成！
echo.
echo 後端 (Parquet): http://localhost:5000
echo 前端: http://localhost:3000
echo.
echo 請稍候幾秒等待服務啟動，然後開啟瀏覽器訪問:
echo http://localhost:3000
echo.
echo 按任意鍵開啟瀏覽器...
echo ================================================================================
pause > nul

start http://localhost:3000
