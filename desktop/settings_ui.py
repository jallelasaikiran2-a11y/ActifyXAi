import tkinter as tk
import customtkinter as ctk
import webbrowser
from settings import settings_mgr

class SettingsWindow(ctk.CTkToplevel):
    """
    Lightweight Settings Window for ActifyXAI.
    """
    def __init__(self, parent_root):
        super().__init__(parent_root)
        self.title("ActifyXAI Settings")
        self.geometry("400x500")
        self.resizable(False, False)
        
        # Center on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = 400
        h = 500
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "#000001")
        self.attributes("-alpha", 0.96)
        self.configure(fg_color="#000001")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        
        self._build_ui()
        self.focus_force()

    def _build_ui(self):
        # Outer frame for rounded background
        outer = ctk.CTkFrame(self, fg_color="#0a0a0a", corner_radius=16, border_width=1, border_color="#26262b")
        outer.pack(fill="both", expand=True)

        header = ctk.CTkLabel(outer, text="ActifyXAI Control Center", font=("Segoe UI Variable Semibold", 18), text_color="#f5f5f5")
        header.pack(pady=(20, 10))
        
        frame = ctk.CTkFrame(outer, fg_color="#121218", corner_radius=14, border_width=1, border_color="#26262b")
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        # ── General Settings ──
        ctk.CTkLabel(frame, text="Orchestration & Runtime", font=("Segoe UI Variable Semibold", 12), text_color="#3b82f6").pack(anchor="w", padx=15, pady=(15, 5))
        
        self.var_startup = tk.BooleanVar(value=settings_mgr.get("run_on_startup"))
        startup_cb = ctk.CTkCheckBox(frame, text="Run on Windows Startup", font=("Segoe UI Variable", 12), variable=self.var_startup, command=self._on_startup_change)
        startup_cb.pack(anchor="w", padx=15, pady=5)
        
        self.var_enabled = tk.BooleanVar(value=settings_mgr.get("orchestration_enabled"))
        enabled_cb = ctk.CTkCheckBox(frame, text="Enable Global Orchestration (Ctrl+Space)", font=("Segoe UI Variable", 12), variable=self.var_enabled, command=self._on_enabled_change)
        enabled_cb.pack(anchor="w", padx=15, pady=5)

        # ── Backend ──
        ctk.CTkLabel(frame, text="Backend Integration", font=("Segoe UI Variable Semibold", 12), text_color="#8b5cf6").pack(anchor="w", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(frame, text="Backend API URL", font=("Segoe UI Variable", 11), text_color="#a3a3a3").pack(anchor="w", padx=15, pady=(0, 2))
        self.backend_entry = ctk.CTkEntry(frame, width=300, fg_color="#23232d", border_color="#212126", text_color="#f5f5f5", font=("Segoe UI Variable", 12))
        self.backend_entry.insert(0, settings_mgr.get("backend_url"))
        self.backend_entry.pack(anchor="w", padx=15, pady=2)
        self.backend_entry.bind("<FocusOut>", self._on_backend_change)

        # ── Quick Actions ──
        ctk.CTkLabel(frame, text="Quick Actions", font=("Segoe UI Variable Semibold", 12), text_color="#3b82f6").pack(anchor="w", padx=15, pady=(20, 5))
        
        btn_dash = ctk.CTkButton(frame, text="Open Local Dashboard", font=("Segoe UI Variable", 12), command=lambda: webbrowser.open(self.backend_entry.get().replace("/api", "")), fg_color="#1c1c24", hover_color="#3b82f6")
        btn_dash.pack(fill="x", padx=15, pady=3)
        
        btn_ask = ctk.CTkButton(frame, text="Open Ask Anything (Ctrl+Shift+Space)", font=("Segoe UI Variable", 12), fg_color="#1c1c24", hover_color="#8b5cf6")
        btn_ask.pack(fill="x", padx=15, pady=3)

        # Close
        btn_close = ctk.CTkButton(outer, text="Close Control Center", font=("Segoe UI Variable", 12), command=self.destroy, fg_color="transparent", border_width=1, border_color="#26262b", text_color="#a3a3a3", hover_color="#1c1c24")
        btn_close.pack(pady=15)

    def _on_startup_change(self):
        settings_mgr.set("run_on_startup", self.var_startup.get())

    def _on_enabled_change(self):
        settings_mgr.set("orchestration_enabled", self.var_enabled.get())

    def _on_backend_change(self, event):
        val = self.backend_entry.get().strip()
        if val:
            settings_mgr.set("backend_url", val)
