import os
import json
import logging
from logging.handlers import RotatingFileHandler
import winreg

# App Data Directory
APP_NAME = "ActifyXAI"
LOCAL_APP_DATA = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
DATA_DIR = os.path.join(LOCAL_APP_DATA, APP_NAME)
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
LOG_FILE = os.path.join(DATA_DIR, "actifyxai.log")

# Ensure dir exists
os.makedirs(DATA_DIR, exist_ok=True)

# Default configuration
DEFAULT_SETTINGS = {
    "orchestration_enabled": True,
    "run_on_startup": True,
    "backend_url": "http://localhost:8000",
    "ai_provider": "ia",
    "theme": "dark"
}

# ── LOGGING SETUP ───────────────────────────────────────────
logger = logging.getLogger("ActifyXAI")
logger.setLevel(logging.INFO)
if not logger.handlers:
    # 5MB max size, keep 2 backups
    handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def get_logger():
    return logger

# ── SETTINGS MANAGEMENT ─────────────────────────────────────
class SettingsManager:
    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self._load()
    
    def _load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                
    def save(self):
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            
    def get(self, key):
        return self.settings.get(key, DEFAULT_SETTINGS.get(key))
        
    def set(self, key, value):
        self.settings[key] = value
        self.save()
        if key == "run_on_startup":
            self._apply_startup(value)

    # ── STARTUP REGISTRY ──────────────────────────────────────
    def _apply_startup(self, enable: bool):
        """Register or unregister app in Windows Startup registry."""
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if enable:
                # Use sys.executable if running as Python, or sys.argv[0] if compiled
                exe_path = sys.executable if "python" in sys.executable.lower() else sys.argv[0]
                # If running as script, you might want to package it first. 
                # For safety, point to the current executable
                import sys
                exe_path = sys.executable if not getattr(sys, 'frozen', False) else sys.executable
                
                # We need quotes around path if there are spaces
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
                logger.info("Enabled Run on Startup")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    logger.info("Disabled Run on Startup")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to configure startup registry: {e}")

# Global instance
settings_mgr = SettingsManager()
