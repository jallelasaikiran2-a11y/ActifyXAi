"""
command_bar.py — Universal "Ask Anything" Command Bar for ActifyXAI
Floating, premium dark glassmorphism interface triggered by Ctrl+Shift+Space.
"""
import ctypes
import tkinter as tk
import customtkinter as ctk

from api_client import APIClient
from clipboard_manager import ClipboardManager

ctk.set_appearance_mode("dark")

# ── Palette (Exact Spatial) ───────────────────────────────────
BG_BASE    = "#0a0a0a"
BG_SURFACE = "#121218"
BG_ELEV    = "#1c1c24"
BG_INPUT   = "#23232d"
BORDER     = "#26262b"
BORDER_SFT = "#212126"
FG_TEXT    = "#f5f5f5"
FG_DIM     = "#a3a3a3"
FG_ACCENT  = "#3b82f6"
FG_VIOLET  = "#8b5cf6"
FONT_BODY  = ("Segoe UI Variable", 15)
FONT_META  = ("Segoe UI Variable", 10)

def get_active_window_title() -> str:
    """Uses ctypes to get the foreground window title on Windows."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value or ""
    except Exception:
        return ""

class CommandBar(ctk.CTkToplevel):
    """
    Floating premium command interface.
    """
    def __init__(self, parent_root, api_client: APIClient, clipboard: ClipboardManager, on_close=None):
        super().__init__(parent_root)
        self.api_client = api_client
        self.clipboard = clipboard
        self.on_close = on_close
        
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "#000001")
        self.attributes("-alpha", 0.96)
        self.configure(fg_color="#000001")
        
        # Center on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 640, 60
        x = (sw - w) // 2
        y = (sh - h) // 4
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        self._build_ui()
        
        # Bindings
        self.bind("<Escape>", lambda e: self._dismiss())
        self.bind("<FocusOut>", lambda e: self.after(100, self._maybe_dismiss))
        self.focus_force()
        self.inp.focus_set()

        # Gather context silently
        self._context_title = get_active_window_title()
        self.context_lbl.configure(text=f"App Context: {self._context_title}" if self._context_title else "Ready")

    def _build_ui(self):
        # Outer frame for pill shape and border
        outer = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=30, border_width=1, border_color=BORDER)
        outer.pack(fill="both", expand=True)

        # Elevated Input Field Container
        self.query_var = tk.StringVar()
        
        inp_container = ctk.CTkFrame(outer, fg_color=BG_INPUT, corner_radius=16, border_width=1, border_color=BORDER_SFT)
        inp_container.pack(fill="x", padx=10, pady=(10, 0))
        
        self.inp = ctk.CTkEntry(
            inp_container,
            textvariable=self.query_var,
            placeholder_text="Ask ActifyXAI anything...",
            fg_color="transparent",
            border_width=0,
            text_color=FG_TEXT,
            placeholder_text_color=FG_DIM,
            font=FONT_BODY,
            height=32,
        )
        self.inp.pack(fill="x", padx=14, pady=2)
        self.inp.bind("<Return>", lambda e: self._execute())

        # Footer meta row
        footer = ctk.CTkFrame(outer, fg_color="transparent", height=18)
        footer.pack(fill="x", padx=22, pady=(4, 6))
        
        self.context_lbl = ctk.CTkLabel(footer, text="Gathering context...", font=FONT_META, text_color=FG_DIM)
        self.context_lbl.pack(side="left")
        
        ctk.CTkLabel(footer, text="Press Esc to close", font=FONT_META, text_color=FG_DIM).pack(side="right")

    def _maybe_dismiss(self):
        foc = self.focus_get()
        if foc is None or foc.winfo_toplevel() != self:
            self._dismiss()

    def _dismiss(self):
        if callable(self.on_close):
            self.on_close()
        self.destroy()

    def _execute(self):
        q = self.query_var.get().strip()
        if not q:
            return
            
        # Freeze UI
        self.inp.configure(state="disabled")
        self.context_lbl.configure(text="Generating response...", text_color=FG_VIOLET)
        
        # Capture selection fallback
        selected_text = self.clipboard.capture_selection()
        
        # We invoke the api_client. We need a way to open the InlineAICard or show results.
        # To avoid circular imports and keep it clean, we'll ask api_client to run 'command' action
        # and then open the InlineAICard with the result, or pass the request back to main.py
        
        if callable(self.on_close):
            self.on_close(command_query=q, window_title=self._context_title, selected_text=selected_text)
        self.destroy()
