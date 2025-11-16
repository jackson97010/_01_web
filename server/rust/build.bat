@echo off
echo ================================================================================
echo Rust Server Build Script
echo ================================================================================
echo.

REM Check if Rust is installed
where cargo >nul 2>nul
if errorlevel 1 (
    echo ERROR: Rust toolchain not detected
    echo.
    echo Please install Rust first:
    echo   1. Visit https://rustup.rs/
    echo   2. Download and run rustup-init.exe
    echo   3. Run this script again after installation
    echo.
    pause
    exit /b 1
)

echo Compiling Rust server (Release mode, optimized performance)...
echo.
cargo build --release

if errorlevel 1 (
    echo.
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo Build successful!
echo ================================================================================
echo.
echo Executable location: target\release\stock-server.exe
echo File size:
dir target\release\stock-server.exe | findstr stock-server
echo.
echo You can now run:
echo   1. Direct run: target\release\stock-server.exe
echo   2. Or use launcher: start_server.bat
echo.
pause
