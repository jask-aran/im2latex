# Im2Latex

![Im2Latex Logo](assets/scissor.png)  
**Convert mathematical images to LaTeX code with a single shortcut.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.8+-yellow.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-lightgrey.svg)]()

Capture a screenshot of mathematical expressions and instantly convert to LaTeX code, copied to your clipboard. 



## Features

- **Instant Conversion**: Capture any math expression and get LaTeX code on your clipboard.
- **System Tray**: Runs quietly in the background with right-click options.
- **Custom Shortcuts**: Configurable via `config.json` (Windows default: `Win+Shift+Z`).
- **Sound Feedback**: Hear a beep when conversion is done.
- **Platform Goals**: Windows-ready now; Linux/macOS support coming soon.

---

# Installation

### From Release
1. Grab the latest `Im2Latex.exe` from [Releases](https://github.com/username/im2latex/releases).
2. Run `install.bat` from the same directory to make it searchable via Windows Search/Start Menu.
3. Proceed to [Configuration](#configuration).


### Build Manually
- Option 1: Use the script
   - Run `build.bat` in the project root. It creates a virtual environment, installs dependencies from `requirements.txt`, and builds the `.exe` using PyInstaller. The executable will be in the `dist` folder.
- Option 2: Manual steps
   - Create a virtual environment: `python -m venv .venv`
   - Activate it: `.venv\Scripts\activate.bat`
   - Install dependencies: `pip install -r requirements.txt`
   - Build the executable: `pyinstaller --onefile --windowed --add-data "assets;assets" --hidden-import=google.generativeai --icon=assets/scissor.png --name=Im2Latex main.py`
   - Find the `.exe` in the `dist` folder.

### Configuration

1. Launch Im2Latex once after installation. This will create a default `config.json` file.
2. Edit `config.json` to add your Google Generative AI API key:
   ```json
   {
     "api_key": "YOUR_API_KEY_HERE",
     "prompt": "...",
     "shortcuts": {
       "windows": [
         {"shortcut_str": "win+shift+z", "action": "trigger_screenshot"}
       ]
     }
   }
   ```
3. Restart Im2Latex for the changes to take effect.

The default shortcut for capturing screenshots is `Win+Shift+Z` on Windows.