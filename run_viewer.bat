@echo off
chcp 65001 >nul
echo ================================================================================
echo OTC/TSE Quote Web Viewer Server
echo ================================================================================
echo.

REM Activate conda environment
call conda activate my_project
if %errorlevel% neq 0 (
    echo ERROR: Cannot activate conda environment my_project
    echo Please make sure the environment exists
    pause
    exit /b 1
)

echo Conda environment activated: my_project
echo.

REM Start web server
echo Starting web server...
echo Server will run at http://localhost:5000
echo Press Ctrl+C to stop the server
echo.
python web_viewer.py

pause
