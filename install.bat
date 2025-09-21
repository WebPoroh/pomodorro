@echo off
echo Installing Pomodoro Tracker dependencies...
echo.

echo Step 1: Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo Error creating virtual environment
    pause
    exit /b 1
)

echo Step 2: Activating virtual environment...
call .venv\Scripts\activate.bat

echo Step 3: Upgrading pip...
python -m pip install --upgrade pip

echo Step 4: Installing dependencies...
echo Trying requirements-windows.txt first...
pip install -r requirements-windows.txt
if errorlevel 1 (
    echo Failed with requirements-windows.txt, trying individual packages...
    pip install fastapi
    pip install uvicorn[standard]
    pip install sqlalchemy
    pip install aiohttp
    pip install pystray
    pip install Pillow
    pip install websockets
)

echo.
echo Installation complete!
echo.
echo To start the server:
echo   python main.py
echo.
echo To start desktop app:
echo   python desktop_app.py
echo.
pause
