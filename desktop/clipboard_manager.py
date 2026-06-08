"""
clipboard_manager.py — Safe clipboard capture for ActifyXAI Desktop
Handles: backup, Ctrl+C capture, restore, empty guard
"""
import time
import threading
import pyperclip
import pyautogui


class ClipboardManager:
    """
    Thread-safe clipboard capture with backup/restore.
    Simulates Ctrl+C, waits for update, restores previous state.
    """

    _lock = threading.Lock()

    def __init__(self, capture_wait: float = 0.18):
        self.capture_wait = capture_wait  # seconds to wait after Ctrl+C

    def capture_selection(self) -> str:
        """
        Main capture method.
        1. Backs up current clipboard content.
        2. Simulates Ctrl+C to copy active selection.
        3. Reads new clipboard content.
        4. Schedules restore of original clipboard.
        Returns the selected text (empty string if none).
        """
        with self._lock:
            # Backup
            try:
                original = pyperclip.paste() or ""
            except Exception:
                original = ""

            # Clear clipboard so we can detect if Ctrl+C actually set anything
            try:
                pyperclip.copy("")
            except Exception:
                pass

            # Simulate copy
            try:
                pyautogui.hotkey("ctrl", "c")
            except Exception:
                return ""

            # Wait for clipboard to update — poll for speed
            selected = ""
            deadline = time.time() + self.capture_wait
            while time.time() < deadline:
                time.sleep(0.03)
                try:
                    candidate = pyperclip.paste() or ""
                except Exception:
                    candidate = ""
                if candidate and candidate != original:
                    selected = candidate
                    break

            # Fallback: if polling didn't catch it, read anyway
            if not selected:
                try:
                    selected = pyperclip.paste() or ""
                except Exception:
                    selected = ""

            # Restore original clipboard after a short delay
            # (delay so the calling code can read `selected` first)
            if original:
                def _restore():
                    time.sleep(0.4)
                    try:
                        pyperclip.copy(original)
                    except Exception:
                        pass
                threading.Thread(target=_restore, daemon=True).start()

            return selected.strip()

    @staticmethod
    def copy_to_clipboard(text: str) -> bool:
        """Copy `text` to clipboard. Returns True on success."""
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            return False

    @staticmethod
    def paste_from_clipboard() -> str:
        """Read current clipboard content."""
        try:
            return pyperclip.paste() or ""
        except Exception:
            return ""
