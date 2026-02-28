@echo off
echo ====================================
echo   VedaVision Web Application
echo   Starting Flask Server...
echo ====================================
echo.

cd /d "%~dp0"

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

echo.
echo Checking dependencies...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo Flask not installed. Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo Starting Flask server...
echo.
echo ====================================
echo   Server will start on:
echo   http://localhost:5000
echo ====================================
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py

pause
