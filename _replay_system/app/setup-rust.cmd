@echo off
chcp 65001 >nul
echo ========================================
echo  Rust Setup
echo ========================================
echo.

where rustc >nul 2>&1
if errorlevel 1 (
    echo Rust not found!
    echo Please install from: https://rustup.rs/
    echo Then restart terminal and run this again
    pause
    exit /b 1
)

echo Rust found
rustc --version
echo.

where neon >nul 2>&1
if errorlevel 1 (
    echo Installing Neon CLI...
    call npm install -g @neon-rs/cli
)

echo Building Rust module...
cd native
call npm install
call npm run build
cd ..

echo.
echo Success!
echo.
pause
