@echo off

echo Activating virtual environment...
call C:\Dev\im2latex\.venv\Scripts\activate.bat

echo Building the executable...
pyinstaller --onefile --windowed --add-data "assets;assets" --hidden-import=google.generativeai --icon=assets/scissor.png --name=Im2Latex test.py

echo Build complete!
pause
