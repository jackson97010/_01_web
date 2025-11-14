@echo off
chcp 65001 >nul
echo ================================================================================
echo OTC/TSE Quote Batch Processing
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

REM Run batch processing
echo Starting batch processing...
python batch_process.py

if %errorlevel% equ 0 (
    echo.
    echo ================================================================================
    echo Batch processing completed successfully!
    echo ================================================================================
) else (
    echo.
    echo ================================================================================
    echo Batch processing failed. Please check error messages above.
    echo ================================================================================
)

echo.
pause
