# ActifyXAI

A context-aware AI orchestration system.
"Select → Intelligent Action → Optimized Execution"

## Project Structure

- **extension/**: Chrome browser extension for on-page text selection.
- **backend/**: FastAPI-based orchestrator handling context analysis, prompt building, and model routing.
- **desktop/**: Global system-wide shortcut listener (Ctrl+Space) that captures clipboard and displays inline popups.
- **shared/**: Shared constants and utility functions.

## Setup Instructions

### 1. Browser Extension
1. Open Chrome and go to `chrome://extensions/`.
2. Enable "Developer mode".
3. Click "Load unpacked" and select the `extension` folder.
4. Select any text on a webpage to see the inline popup. The extension MVP will automatically open ChatGPT and inject the built prompt.

### 2. Backend Server
1. Navigate to the `backend` directory.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file by copying `.env.example` and adding your `GROQ_API_KEY`.
   ```bash
   cp .env.example .env
   ```
4. Run the server:
   ```bash
   python main.py
   ```
5. The API will run on `http://localhost:8000`.

### 3. Desktop Application
1. Ensure the Backend Server is running.
2. Navigate to the `desktop` directory.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the desktop application:
   ```bash
   python main.py
   ```
5. Select any text globally (browser, text editor, etc.), hold `Ctrl` and press `Space`. A popup will appear at your cursor to explain or fix the text using the AI backend.

## Execution Strategy Implementation
All phases (1 to 5) have been built exactly as defined:
- **Phase 1**: Chrome Extension MVP (content scripts, popups, background tasks).
- **Phase 2**: Modular FastAPI backend system.
- **Phase 3**: Intelligence layer (Context Engine, Prompt Builder, Action Engine).
- **Phase 4**: Desktop Integration via `pynput` and `tkinter`.
- **Phase 5**: Model Routing logic implemented in `model_router.py` (selecting between lightweight and advanced models depending on the context).
