# Im2Latex

A tool to convert mathematical images to LaTeX code using Google Generative AI.

## Setup
1. Install Python 3.8+ (https://www.python.org/downloads/).
2. Create a virtual environment:
   - Windows: `python -m venv .venv`
   - Linux/Mac: `python3 -m venv .venv`
3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Linux/Mac: `source .venv/bin/activate`
4. Install dependencies:
   - pip install -r requirements.txt
5. Copy `config.json.example` to `config.json` and replace `YOUR_API_KEY_HERE` with your Google Generative AI API key.

## Building the App
1. Ensure the virtual environment is activated.
2. Run the following command to build the executable:
   - pyinstaller --onefile --windowed --add-data "assets;assets" --hidden-import=google.generativeai --icon=assets/scissor.png --name=Im2Latex main.py
3. Find the executable in the `dist` folder.

## Usage
- Run the executable from the `dist` folder.
- Press Win+Shift+Z to capture a screenshot region.
- The converted LaTeX code will be copied to your clipboard.

## Notes
- The `assets` folder and `config.json` must be in the same directory as `main.py` during development.
- The build process uses PyInstaller with the provided `.spec` file for consistency.