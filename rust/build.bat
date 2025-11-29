@echo off
echo ================================================================================
echo 編譯 Rust 版本（發行模式）
echo ================================================================================
echo.

REM 檢查 Rust 是否已安裝
where cargo >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 錯誤: 找不到 Cargo（Rust 工具鏈）
    echo.
    echo 請先安裝 Rust:
    echo 1. 訪問 https://rustup.rs/
    echo 2. 下載並執行 rustup-init.exe
    echo 3. 重新開啟命令提示字元
    echo.
    pause
    exit /b 1
)

echo 正在編譯... 首次編譯可能需要數分鐘
echo.

cargo build --release

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 編譯失敗！
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo 編譯成功！
echo 執行檔位置: rust\target\release\convert_to_json.exe
echo ================================================================================
pause
