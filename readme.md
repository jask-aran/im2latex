# Im2Latex

![Im2Latex Logo](assets/scissor.png)  
**Convert mathematical images to LaTeX code with a single shortcut.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.8+-yellow.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-lightgrey.svg)]()
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Latest Release](https://img.shields.io/badge/release-v1.0-orange.svg)](https://github.com/username/im2latex/releases)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](https://github.com/username/im2latex/issues)


Capture a screenshot of mathematical expressions and instantly convert it to LaTeX code, copied to your clipboard, using Google Gemini Flash 2.0 or another LLM API.

![Demo](.github/new_demo.gif)

## Features

- **Instant Conversion**: Capture any math expression and get LaTeX code on your clipboard.
- **System Tray**: Runs quietly in the background.
- **Custom Shortcuts**: Configurable via `config.json` (Windows default: `Win+Shift+Z`).
- **Sound Feedback**: Audio cue when conversion is done and LaTeX is ready to paste.
- **Platform Goals**: Windows-ready now; Linux/macOS support coming soon.

---

## Setup

### Basic Setup
1. **Clone or Download the Repository**  
   Clone this project to a folder of your choice or download and extract the ZIP:
   ```
   git clone https://github.com/jask-aran/im2latex.git
   cd im2latex
   ```

2. **Set Up Virtual Environment & Install Dependencies**  
   Create and activate a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/macOS

   pip install -r requirements.txt
   ```

3. **Configure API Key**  
   - Run `main.py` once to generate a default `config.json`:
    ```
    .venv\Scripts\activate
    python main.py
    ```
   - Edit `config.json` in the project folder to add your Google Generative AI API key

5. **Run the Application**  
   Start the app directly:
   ```
   .venv\Scripts\activate
   python main.py
   ```

### Optional: Install as a Windows App
To make Im2Latex act like an installed application (accessible via Windows Search or Start Menu):
1. Run the provided `install.bat` script from the repository root:
   ```
   install.bat
   ```
2. What `install.bat` does:
   - Creates a virtual environment (`.venv`) in the current directory if it doesn’t exist.
   - Installs dependencies from `requirements.txt` into the venv.
   - Adds a Start Menu shortcut named "Im2Latex" that runs `main.py` using the venv’s Python, with the `scissor.ico` icon from `assets/`.
3. Launch Im2Latex from Windows Search or Start Menu as "Im2Latex".

**Note:** If you move the repository folder after running `install.bat`, the shortcut will break unless you rerun the script to update it.

---

## Customizing Shortcuts

Modify the default shortcut (`Win+Shift+Z`) by editing `config.json`:
1. Open `config.json` in the project folder.
2. Update the `shortcuts` section:
   ```json
   "shortcuts": {
     "windows": [
       {"shortcut_str": "ctrl+alt+m", "action": "trigger_screenshot"}
     ]
   }
   ```
3. Supported modifiers: `win`, `ctrl`, `alt`, `shift`  
   Supported keys: `a-z`, `0-9`


#### Pyinstaller
- Create a virtual environment: `python -m venv .venv`
- Activate it: `.venv\Scripts\activate.bat`
- Install dependencies: `pip install -r requirements.txt`
- Build the executable: `pyinstaller --onefile --windowed --add-data "assets;assets" --hidden-import=google.generativeai --hidden-import=tzdata --hidden-import=sip --icon=assets/scissor.png --name=Im2Latex main.py`
- Find the `.exe` in the `dist` folder.
