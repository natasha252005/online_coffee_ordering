@echo off
cd /d "%~dp0"
echo =====================================
echo      BREW AND BLISS COFFEE SHOP
echo =====================================
echo Installing required packages (first run may take a minute)...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Installation failed. Check your Python installation and internet connection.
  pause
  exit /b 1
)
echo.
echo Starting Brew and Bliss...
echo Open http://127.0.0.1:5000 in your browser.
echo Keep this window open while using the website.
echo Press Ctrl+C to stop the server.
echo.
python app.py
pause
