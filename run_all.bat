@echo off
REM FlakeXplain iDFlakies Pytest Execution Batch Script
echo ========================================================
echo Starting FlakeXplain iDFlakies Pytest Pipeline...
echo ========================================================

python run_all.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Pipeline execution encountered an error. Exit code: %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo.
echo Pipeline completed successfully!
pause
