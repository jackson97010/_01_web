@echo off
echo ================================================================================
echo Parquet to JSON Preprocessing Script
echo ================================================================================
echo.

REM Activate conda environment
echo Activating conda environment: my_project
call conda activate my_project
if errorlevel 1 (
    echo ERROR: Cannot activate conda environment
    echo Please make sure Anaconda is installed and configured
    pause
    exit /b 1
)
echo.

echo Starting preprocessing...
echo.
python preprocess.py

echo.
echo ================================================================================
echo Preprocessing completed!
echo ================================================================================
pause
