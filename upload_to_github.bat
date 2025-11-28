@echo off
REM =========================================
REM GitHub 快速上傳腳本
REM =========================================

echo.
echo ========================================
echo GitHub 快速上傳腳本
echo ========================================
echo.

REM 檢查是否已經清理過歷史
if not exist .git (
    echo 錯誤: .git 目錄不存在
    echo 請先執行 clean_git_history.bat
    pause
    exit /b 1
)

REM 顯示目前狀態
echo [檢查] Git 狀態...
git status
echo.

REM 詢問 GitHub repository URL
set /p repo_url="請輸入您的 GitHub repository URL (例: https://github.com/username/repo.git): "

if "%repo_url%"=="" (
    echo 錯誤: repository URL 不能為空
    pause
    exit /b 1
)

echo.
echo ========================================
echo 準備上傳
echo ========================================
echo Repository: %repo_url%
echo.

set /p confirm="確定要上傳嗎? (y/N): "
if /i not "%confirm%"=="y" (
    echo 操作已取消
    exit /b 0
)

echo.
echo [1/3] 設定遠端 repository...
git remote remove origin 2>nul
git remote add origin %repo_url%
echo 遠端設定完成

echo.
echo [2/3] 檢查遠端連接...
git remote -v

echo.
echo [3/3] 推送到 GitHub...
echo.
echo 提示: 如果提示輸入帳號密碼，建議使用 Personal Access Token
echo.

git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo 上傳成功！
    echo ========================================
    echo.
    echo 您的專案已成功上傳到 GitHub
    echo Repository: %repo_url%
    echo.
    echo 接下來您可以:
    echo 1. 訪問 GitHub 確認檔案
    echo 2. 設定 repository 描述和 topics
    echo 3. 新增協作者（如需要）
    echo.
) else (
    echo.
    echo ========================================
    echo 上傳失敗
    echo ========================================
    echo.
    echo 常見問題:
    echo 1. 確認 repository URL 正確
    echo 2. 確認您有權限推送
    echo 3. 如果是新 repository，可能需要先在 GitHub 建立
    echo.
    echo 手動推送指令:
    echo git push -u origin main --force  (強制推送)
    echo.
)

pause
