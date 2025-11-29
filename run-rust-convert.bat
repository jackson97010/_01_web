@echo off
echo ================================================================================
echo 執行 Rust 版本的 Parquet 轉 JSON 轉換程式
echo ================================================================================
echo.

if not exist "rust\target\release\convert_to_json.exe" (
    echo 錯誤: 找不到執行檔
    echo.
    echo 請先編譯程式:
    echo   cd rust
    echo   cargo build --release
    echo.
    echo 或直接執行: rust\build-and-run.bat
    echo.
    pause
    exit /b 1
)

rust\target\release\convert_to_json.exe

echo.
pause
