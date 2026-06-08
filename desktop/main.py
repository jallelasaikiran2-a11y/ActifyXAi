"""
main.py -- ActifyXAI Desktop Orchestration Layer
Entry point: global hotkey, clipboard capture, tray icon, Tkinter shell.

Run: python main.py
"""
import sys
import io
# Ensure UTF-8 output on Windows terminals (fixes cp1252 box-char errors)
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding='utf-8',
        errors='replace'
    )

if sys.stderr and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer,
        encoding='utf-8',
        errors='replace'
    )
import time
import threading
import tkinter as tk
import customtkinter as ctk
from pynput import keyboard as pynput_kb

import ctypes

from clipboard_manager import ClipboardManager
from api_client import APIClient
from settings import settings_mgr, get_logger
from settings_ui import SettingsWindow

logger = get_logger()

# ================================================================
# LOCAL COORDINATION SERVER  (port 27182)
# Browser extension polls this to detect the desktop controller.
# Serves: /status  /config  /health
# Runs as a daemon thread — never blocks the main loop.
# ================================================================

import json
from http.server import HTTPServer, BaseHTTPRequestHandler

COORD_PORT = 27182   # desktop controller port

class _CoordHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for browser-extension coordination."""
    app_ref = None  # set to ActifyDesktopApp instance before server starts

    def log_message(self, *args):
        pass  # silence default HTTP log spam

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")  # allow extension access
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        # Pre-flight for extension fetch()
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        app = _CoordHandler.app_ref
        if self.path == "/status":
            self._send_json({
                "running": True,
                "enabled": settings_mgr.get("orchestration_enabled"),
                "version": "1.0",
                "backend": settings_mgr.get("backend_url"),
            })
        elif self.path == "/config":
            self._send_json({
                "backend_url": f"{settings_mgr.get('backend_url')}/api",
                "orchestration_enabled": settings_mgr.get("orchestration_enabled"),
            })
        elif self.path == "/health":
            self._send_json({"ok": True})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        app = _CoordHandler.app_ref
        if self.path == "/toggle":
            if app:
                app.toggle_enabled()
            self._send_json({"enabled": settings_mgr.get("orchestration_enabled")})
        else:
            self._send_json({"error": "not found"}, 404)


def _start_coord_server(app_instance):
    """Start coordination server in a daemon thread."""
    _CoordHandler.app_ref = app_instance
    try:
        server = HTTPServer(("127.0.0.1", COORD_PORT), _CoordHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server
    except OSError:
        # Port already in use — another instance is running; that's fine
        return None


# ── Optional tray icon (graceful fallback if pystray not installed) ─
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

ctk.set_appearance_mode("dark")


# ================================================================
# NOTIFICATION TOAST
# ================================================================

def show_toast(root: tk.Tk, message: str, duration_ms: int = 2500):
    """Lightweight bottom-right toast notification."""
    try:
        toast = ctk.CTkToplevel(root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(fg_color="#1c2230")

        sw = toast.winfo_screenwidth()
        sh = toast.winfo_screenheight()

        lbl = ctk.CTkLabel(toast, text=message,
                           font=("Segoe UI", 10), text_color="#e6edf3",
                           fg_color="#1c2230", corner_radius=8,
                           padx=14, pady=8)
        lbl.pack()
        toast.update_idletasks()
        w = toast.winfo_reqwidth()
        h = toast.winfo_reqheight()
        toast.geometry(f"{w}x{h}+{sw - w - 20}+{sh - h - 50}")
        toast.after(duration_ms, toast.destroy)
    except Exception:
        pass


# ================================================================
# SYSTEM TRAY
# ================================================================

def _make_tray_icon_image():
    """Create a small coloured square icon for the tray."""
    img = Image.new("RGB", (64, 64), color="#0d1117")
    d = ImageDraw.Draw(img)
    d.ellipse([8, 8, 56, 56], fill="#1f6feb")
    d.text((18, 16), "AI", fill="white")
    return img


def setup_tray(root: tk.Tk, app):
    if not TRAY_AVAILABLE:
        return None

    icon_img = _make_tray_icon_image()

    def on_quit(icon, _item):
        icon.stop()
        root.after(0, root.quit)

    def on_status(icon, _item):
        root.after(0, lambda: show_toast(root, "✅ ActifyXAI is active"))

    def on_toggle(icon, _item):
        app.toggle_enabled()
        state = "enabled" if settings_mgr.get("orchestration_enabled") else "disabled"
        root.after(0, lambda: show_toast(root, f"Orchestration {state}"))

    def on_settings(icon, _item):
        root.after(0, app.open_settings)

    menu = pystray.Menu(
        pystray.MenuItem("Status",       on_status),
        pystray.MenuItem("Enable/Disable Orchestration", on_toggle),
        pystray.MenuItem("Settings",     on_settings),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit",         on_quit),
    )

    icon = pystray.Icon("ActifyXAI", icon_img, "ActifyXAI", menu)
    t = threading.Thread(target=icon.run, daemon=True)
    t.start()
    return icon


# ================================================================
# MAIN APPLICATION
# ================================================================

class ActifyDesktopApp:
    """
    Core orchestration shell.
    Manages: global hotkey, clipboard capture, popup lifecycle.
    """

    def __init__(self):
        self._ctrl_held  = False
        self._shift_held = False
        self._active_toolbar = None
        self._command_bar    = None
        self._trigger_lock   = threading.Lock()
        self._settings_win   = None

        # Sub-systems
        self.clipboard  = ClipboardManager(capture_wait=0.20)
        self.api_client = APIClient()

        # Tkinter root (invisible shell, event bus)
        self.root = ctk.CTk()
        self.root.withdraw()
        self.root.title("ActifyXAI")
        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)

    # ── Public ──────────────────────────────────────────────────
    def toggle_enabled(self):
        current = settings_mgr.get("orchestration_enabled")
        settings_mgr.set("orchestration_enabled", not current)

    def open_settings(self):
        if self._settings_win and self._settings_win.winfo_exists():
            self._settings_win.focus_force()
            return
        self._settings_win = SettingsWindow(self.root)

    def _on_key_press(self, key):
        if key in (pynput_kb.Key.ctrl_l, pynput_kb.Key.ctrl_r):
            self._ctrl_held = True
        if key in (pynput_kb.Key.shift_l, pynput_kb.Key.shift_r):
            self._shift_held = True

    def _on_key_release(self, key):
        if key in (pynput_kb.Key.ctrl_l, pynput_kb.Key.ctrl_r):
            self._ctrl_held = False
            self._shift_held = False

        if key == pynput_kb.Key.space and self._ctrl_held:
            if settings_mgr.get("orchestration_enabled"):
                if getattr(self, "_shift_held", False):
                    # Ctrl + Shift + Space
                    threading.Thread(target=self._handle_command_bar, daemon=True).start()
                else:
                    # Ctrl + Space
                    threading.Thread(target=self._handle_trigger, daemon=True).start()

        if key == pynput_kb.Key.esc:
            self.root.after(0, self._dismiss_toolbar)

    # ── Trigger handler ─────────────────────────────────────────
    def _handle_trigger(self):
        if not self._trigger_lock.acquire(blocking=False):
            return   # ignore double-trigger
        try:
            # Get cursor BEFORE Ctrl+C so it reflects selection origin
            try:
                import pyautogui
                cx, cy = pyautogui.position()
            except Exception:
                cx, cy = 100, 100

            text = self.clipboard.capture_selection()

            if not text or len(text) < 3:
                self.root.after(0, lambda: show_toast(
                    self.root, "ℹ️  No text selected — select text first", 2000))
                return

            # Check backend health (non-blocking, cached)
            # Fire-and-forget health check; popup still opens regardless
            self.root.after(0, lambda: self._show_toolbar(text, cx, cy))
        finally:
            self._trigger_lock.release()

    # ── Toolbar lifecycle ────────────────────────────────────────
    def _show_toolbar(self, text: str, cx: int, cy: int):
        # Dismiss any existing toolbar first
        self._dismiss_toolbar()

        # Import here to avoid circular issues at startup
        from popup import ActionToolbar

        def on_dismissed():
            self._active_toolbar = None

        toolbar = ActionToolbar(
            parent_root=self.root,
            text=text,
            cursor_x=cx,
            cursor_y=cy,
            api_client=self.api_client,
            clipboard=self.clipboard,
            on_dismissed=on_dismissed,
        )
        self._active_toolbar = toolbar

    def _dismiss_toolbar(self):
        if self._active_toolbar:
            try:
                self._active_toolbar._dismiss()
            except Exception:
                pass
            self._active_toolbar = None

    # ── Command Bar ──────────────────────────────────────────────
    def _handle_command_bar(self):
        if not self._trigger_lock.acquire(blocking=False):
            return
        try:
            self.root.after(0, self._show_command_bar)
        finally:
            self._trigger_lock.release()

    def _show_command_bar(self):
        if self._command_bar:
            try:
                if self._command_bar.winfo_exists():
                    self._command_bar.focus_force()
                    self._command_bar.inp.focus_set()
                    return
            except Exception:
                pass
            self._command_bar = None

        from command_bar import CommandBar
        from overlay_ui import InlineAICard

        def on_close(command_query=None, window_title=None, selected_text=None):
            self._command_bar = None
            if command_query:
                # Compile rich RAG context
                full_query = f"Command: {command_query}\nApp Context: {window_title}"
                if selected_text:
                    full_query += f"\nSelected Content:\n{selected_text[:1000]}"
                
                # Launch InlineAICard centered
                sw = self.root.winfo_screenwidth()
                sh = self.root.winfo_screenheight()
                InlineAICard(
                    parent_root=self.root,
                    text=full_query,
                    action="command",
                    intent="command",
                    anchor_x=(sw - 440) // 2,
                    anchor_y=(sh - 480) // 2,
                    api_client=self.api_client,
                    clipboard=self.clipboard,
                )

        self._command_bar = CommandBar(
            parent_root=self.root,
            api_client=self.api_client,
            clipboard=self.clipboard,
            on_close=on_close
        )

    # ── Backend health ────────────────────────────────────────────
    def _check_backend(self):
        ok = self.api_client.check_health()
        if not ok:
            self.root.after(0, lambda: show_toast(
                self.root,
                "⚠️  Backend offline — start: uvicorn main:app --reload",
                4000))

    # ── Main run loop ─────────────────────────────────────────────
    def run(self):
        logger.info("Starting ActifyXAI Desktop Orchestration")

        # Background health check
        threading.Thread(target=self._check_backend, daemon=True).start()

        # Start desktop coordination server (for browser extension bridge)
        _start_coord_server(self)

        # Tray icon
        setup_tray(self.root, self)

        # Keyboard listener in daemon thread
        listener = pynput_kb.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release)
        listener.daemon = True
        listener.start()

        # Startup toast
        self.root.after(1200, lambda: show_toast(
            self.root, "✅ ActifyXAI ready — Press Ctrl+Space on any text", 3000))

        # Tkinter main loop (blocking)
        self.root.mainloop()

    def _on_quit(self):
        self.root.quit()


# ================================================================
# ENTRY POINT WITH SINGLE INSTANCE LOCK
# ================================================================

if __name__ == "__main__":
    # Ensure single instance via Windows Mutex
    mutex_name = "ActifyXAI_Global_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    
    if last_error == 183: # ERROR_ALREADY_EXISTS
        print("ActifyXAI is already running.")
        sys.exit(0)
        
    try:
        app = ActifyDesktopApp()
        app.run()
    finally:
        if mutex:
            ctypes.windll.kernel32.ReleaseMutex(mutex)
