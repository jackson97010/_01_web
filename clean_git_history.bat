@echo off
REM =========================================
REM Git 歷史清理腳本
REM 完全重置 Git 歷史，移除所有大檔案
REM =========================================

echo.
echo ========================================
echo Git 歷史清理腳本
echo ========================================
echo.
echo 這個腳本將會:
echo 1. 備份目前的 .git 目錄
echo 2. 重新初始化 Git repository
echo 3. 建立全新的初始 commit
echo.
echo 警告: 這將移除所有 Git 歷史記錄！
echo.

REM 確認
set /p confirm="確定要繼續嗎? (y/N): "
if /i not "%confirm%"=="y" (
    echo 操作已取消
    exit /b 0
)

echo.
echo [1/5] 備份目前的 .git 目錄...
if exist .git.backup (
    echo 刪除舊的備份...
    rmdir /s /q .git.backup
)
move .git .git.backup
echo 備份完成: .git.backup

echo.
echo [2/5] 重新初始化 Git...
git init
echo Git 初始化完成

echo.
echo [3/5] 設定 Git 設定...
git config core.autocrlf false
git config core.longpaths true
echo Git 設定完成

echo.
echo [4/5] 加入所有檔案（遵守 .gitignore）...
git add .
echo 檔案加入完成

echo.
echo [5/5] 建立初始 commit...
git commit -m "Initial commit: 台股即時報價回放系統

- React 18 + TypeScript 前端應用
- Rust 高效能資料處理引擎
- Python 資料解碼和轉換腳本
- 統一時間軸架構實作
- Chart.js 圖表視覺化
- Zustand 狀態管理
- 完整的開發文檔

排除大型檔案:
- data/ (原始和處理後的資料)
- api/ (JSON API 資料)
- 編譯產物 (target/, node_modules/)

請參考 DATA_README.md 了解如何準備資料"

echo.
echo ========================================
echo 清理完成！
echo ========================================
echo.
echo 接下來的步驟:
echo.
echo 1. 檢查要提交的檔案:
echo    git status
echo    git ls-files
echo.
echo 2. 如果一切正常，連接到 GitHub:
echo    git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
echo.
echo 3. 推送到 GitHub:
echo    git push -u origin main
echo.
echo 4. 如果需要恢復舊的歷史:
echo    rmdir /s /q .git
echo    move .git.backup .git
echo.

pause
