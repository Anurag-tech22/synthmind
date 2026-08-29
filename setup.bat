@echo off
echo.
echo ========================================
echo   SynthMind - Quick Setup Script
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed. Please install Python 3.10+
    exit /b 1
)
echo [OK] Python found

:: Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed. Please install Node.js 18+
    exit /b 1
)
echo [OK] Node.js found

:: Backend setup
echo.
echo [1/4] Setting up backend...
cd backend
if not exist venv (
    python -m venv venv
    echo [OK] Virtual environment created
)
call venv\Scripts\activate
pip install -r requirements.txt --quiet
echo [OK] Backend dependencies installed

:: Check for .env
if not exist .env (
    echo.
    echo [WARNING] No .env file found!
    echo Please create backend\.env with your GEMINI_API_KEY
    echo Example: copy .env.example .env and edit it
    echo.
)

cd ..

:: Frontend setup
echo.
echo [2/4] Setting up frontend...
cd frontend
call npm install --silent
echo [OK] Frontend dependencies installed
cd ..

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo To start the app:
echo.
echo   Terminal 1 (Backend):
echo     cd synthmind\backend
echo     venv\Scripts\activate
echo     python main.py
echo.
echo   Terminal 2 (Frontend):
echo     cd synthmind\frontend
echo     npm run dev
echo.
echo   Then open http://localhost:3000
echo.
echo ========================================
