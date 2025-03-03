@echo off

REM Define paths
set VENV_DIR=.venv
set REQUIREMENTS_FILE=requirements.txt

echo Checking for virtual environment...

REM Check if the virtual environment exists
if not exist %VENV_DIR%\ (
    echo Virtual environment not found. Creating one...
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo Failed to create virtual environment. Ensure Python is installed.
        pause
        exit /b 1
    )
    echo Virtual environment created.
)

echo Activating virtual environment...
call %VENV_DIR%\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Install dependencies
if exist %REQUIREMENTS_FILE% (
    echo Installing dependencies...
    pip install -r %REQUIREMENTS_FILE%
    if errorlevel 1 (
        echo Failed to install dependencies. Check requirements.txt.
        pause
        exit /b 1
    )
) else (
    echo Warning: requirements.txt not found. Ensure dependencies are installed manually.
)

echo Building the executable...
pyinstaller --onefile --windowed --add-data "assets;assets" --hidden-import=google.generativeai --icon=assets/scissor.png --name=Im2Latex main.py
if errorlevel 1 (
    echo Failed to build the executable.
    pause
    exit /b 1
)

echo Build complete! The executable can be found in the 'dist' folder.
pause
