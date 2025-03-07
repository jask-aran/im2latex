@echo off

REM Define paths and constants
set VENV_DIR=.venv
set REQUIREMENTS_FILE=requirements.txt
set PYTHON_SCRIPT=main.py
set SHORTCUT_PATH="%APPDATA%\Microsoft\Windows\Start Menu\Programs\Im2Latex.lnk"
set CURRENT_DIR=%CD%
set ICON_PATH=%CURRENT_DIR%\assets\scissor.ico

echo Setting up Im2Latex in the current directory: %CURRENT_DIR%...

REM Check if the Python script exists
if not exist "%PYTHON_SCRIPT%" (
    echo Error: '%PYTHON_SCRIPT%' not found in the current directory.
    echo Please run this script from the Im2Latex repository root.
    pause
    exit /b 1
)

REM Check if virtual environment exists, create it if not
if not exist "%VENV_DIR%\" (
    echo Virtual environment not found. Creating one...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Failed to create virtual environment. Ensure Python is installed and accessible.
        pause
        exit /b 1
    )
    echo Virtual environment created at %VENV_DIR%.
) else (
    echo Virtual environment already exists at %VENV_DIR%.
)

REM Install dependencies in a separate call to ensure control returns
echo Installing dependencies...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)
if exist "%REQUIREMENTS_FILE%" (
    pip install -r "%REQUIREMENTS_FILE%"
    if errorlevel 1 (
        echo Failed to install dependencies. Check %REQUIREMENTS_FILE% or network connection.
        pause
        exit /b 1
    )
    echo Dependencies installed or already satisfied.
) else (
    echo Warning: '%REQUIREMENTS_FILE%' not found. Skipping dependency installation.
)

REM Check if the icon file exists
if not exist "%ICON_PATH%" (
    echo Warning: Icon file '%ICON_PATH%' not found. Shortcut will use default icon.
)

REM Create Start Menu shortcut using pythonw.exe to hide console
echo Creating Start Menu shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$Shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%CURRENT_DIR%\%VENV_DIR%\Scripts\pythonw.exe'; $Shortcut.Arguments = '%CURRENT_DIR%\%PYTHON_SCRIPT%'; $Shortcut.WorkingDirectory = '%CURRENT_DIR%'; $Shortcut.IconLocation = '%ICON_PATH%'; $Shortcut.Description = 'Convert images to LaTeX'; $Shortcut.Save()" 2> install_error.log
if errorlevel 1 (
    echo Failed to create Start Menu shortcut. Check install_error.log for details.
    type install_error.log
    pause
    exit /b 1
) else (
    echo Start Menu shortcut created successfully.
)

echo Setup complete! You can now launch 'Im2Latex' from Windows Search or the Start Menu without a console window.
echo To run manually without a console, use: %VENV_DIR%\Scripts\pythonw %PYTHON_SCRIPT%

pause