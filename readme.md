# Im2Latex

![Im2Latex Logo](assets/scissor.png)  
**Convert mathematical images to LaTeX code with a single shortcut.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.8+-yellow.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-lightgrey.svg)]()
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Latest Release](https://img.shields.io/badge/release-v1.0-orange.svg)](https://github.com/username/im2latex/releases)

Capture a screenshot of mathematical expressions and instantly convert to LaTeX code, copied to the clipboard.

![Demo](.github/new_demo.gif)

## Features

- **Instant Conversion**: Capture any math expression and get LaTeX code on your clipboard.
- **System Tray**: Runs quietly in the background.
- **Custom Shortcuts**: Configurable via `config.json` (Windows default: `Win+Shift+Z`).
- **Sound Feedback**: Audio queue when conversion is done and LaTeX ready to paste.
- **Platform Goals**: Windows-ready now; Linux/macOS support coming soon.

---

## Installation

### From Release

1. Download the latest `Im2Latex.exe` from [Releases](https://github.com/username/im2latex/releases).
2. Run `install.bat` from the same directory.
   - Enter an installation directory when prompted (press Enter for default: `%LOCALAPPDATA%\Im2Latex`).
   - The script copies the `.exe` to this directory and adds a Start Menu shortcut, making it accessible via Windows Search or Start Menu.
3. Proceed to [Configuration](#configuration).

### Build Manually

#### Option 1: Use the script
- Run `build.bat` in the project root. It creates a virtual environment, installs dependencies from `requirements.txt`, and builds the `.exe` using PyInstaller. The executable will be in the `dist` folder.
- Run `install.bat` from the project root to copy the `.exe` from `dist` to your chosen directory and add it to Windows Search/Start Menu.

#### Option 2: Manual steps
- Create a virtual environment: `python -m venv .venv`
- Activate it: `.venv\Scripts\activate.bat`
- Install dependencies: `pip install -r requirements.txt`
- Build the executable: `pyinstaller --onefile --windowed --add-data "assets;assets" --hidden-import=google.generativeai --icon=assets/scissor.png --name=Im2Latex main.py`
- Find the `.exe` in the `dist` folder.
- Run `install.bat` to copy the `.exe` from `dist` to your chosen directory and add it to Windows Search/Start Menu.

### Configuration

1. Launch `Im2Latex.exe` once after installation. This creates a default `config.json` file in the installation directory.
2. Edit `config.json` to add your Google Generative AI API key:
   ```json
   {
     "api_key": "YOUR_API_KEY_HERE",
     "prompt": "Convert the mathematical content in this image to raw LaTeX math code. Use \\text{} for plain text within equations. For one equation, return only its code. For multiple equations, use \\begin{array}{l}...\\end{array} with \\\\ between equations, matching the image's visual structure. Never use standalone environments like equation or align, and never wrap output in code block markers (e.g., ```). Return NA if no math is present.",
     "shortcuts": {
       "windows": [
         {"shortcut_str": "win+shift+z", "action": "trigger_screenshot"}
       ]
     }
   }
   ```

## Customizing Shortcuts

You can modify the default shortcut (`Win+Shift+Z`) by editing the `config.json` file:

1. Open `config.json` in your installation directory
2. Locate the `shortcuts` section
3. Modify the `shortcut_str` value to your preferred key combination

Example for a different shortcut:
```json
"shortcuts": {
  "windows": [
    {"shortcut_str": "ctrl+alt+m", "action": "trigger_screenshot"}
  ]
}
```

Supported modifiers include: `win`, `ctrl`, `alt`, and `shift`  
Supported keys include: letters (`a-z`) and numbers (`0-9`)

## Usage

1. Press the shortcut key (default: `Win+Shift+Z`) to capture a screenshot.
2. Select the area containing mathematical expressions.
3. The LaTeX code will be automatically copied to your clipboard.
4. Paste the LaTeX code into your document editor.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](https://github.com/username/im2latex/issues)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.