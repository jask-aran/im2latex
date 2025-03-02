@echo off

REM Set installation directory (changeable by the user)
set /p INSTALL_DIR="Enter installation directory (default: %LOCALAPPDATA%\Im2Latex): "
if "%INSTALL_DIR%"=="" set INSTALL_DIR="%LOCALAPPDATA%\Im2Latex"

set SHORTCUT_PATH="%APPDATA%\Microsoft\Windows\Start Menu\Programs\Im2Latex.lnk"

echo Installing Im2Latex to %INSTALL_DIR%...

REM Create installation directory if it doesn't exist
if not exist %INSTALL_DIR% (
    echo Creating installation directory...
    mkdir %INSTALL_DIR%
)

REM Copy the built executable instead of moving it
if exist "dist\Im2Latex.exe" (
    echo Copying executable to installation directory...
    copy /Y "dist\Im2Latex.exe" %INSTALL_DIR% >nul
) else (
    echo Error: 'Im2Latex.exe' not found in 'dist'. Run build.bat first.
    pause
    exit /b 1
)

REM Create Start Menu shortcut
echo Creating Start Menu shortcut...
powershell -Command "$Shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%INSTALL_DIR%\Im2Latex.exe'; $Shortcut.Save()"

echo Installation complete! You can now launch 'Im2Latex' from Windows Search or the Start Menu.

pause
