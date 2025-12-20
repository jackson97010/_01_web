@echo off
echo ========================================
echo  台股極速回放系統 - Rust 模塊安裝
echo ========================================
echo.

REM 檢查 Rust 是否已安裝
where rustc >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 未檢測到 Rust！
    echo.
    echo 請先安裝 Rust:
    echo 1. 訪問 https://rustup.rs/
    echo 2. 下載並運行 rustup-init.exe
    echo 3. 重啟命令行
    echo 4. 再次運行此腳本
    echo.
    pause
    exit /b 1
)

echo [✓] Rust 已安裝
rustc --version
echo.

REM 檢查 Neon CLI
where neon >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] 正在安裝 Neon CLI...
    call npm install -g @neon-rs/cli
    if %ERRORLEVEL% NEQ 0 (
        echo [錯誤] Neon CLI 安裝失敗
        pause
        exit /b 1
    )
)

echo [✓] Neon CLI 已安裝
neon --version
echo.

REM 構建 Rust 模塊
echo [!] 正在構建 Rust 模塊...
cd native
if not exist "package.json" (
    echo [錯誤] native/package.json 不存在
    pause
    exit /b 1
)

call npm install
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] npm install 失敗
    pause
    exit /b 1
)

call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] Rust 編譯失敗
    echo.
    echo 可能的原因:
    echo 1. 缺少 Visual Studio Build Tools
    echo 2. Rust 工具鏈問題
    echo.
    echo 請查看 RUST_SETUP.md 獲取幫助
    pause
    exit /b 1
)

cd ..

echo.
echo ========================================
echo  ✓ Rust 模塊安裝成功！
echo ========================================
echo.
echo 下一步:
echo   npm run dev    # 啟動開發模式
echo   npm start      # 啟動生產模式
echo.
pause
