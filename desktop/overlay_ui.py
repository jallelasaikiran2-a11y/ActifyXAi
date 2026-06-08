"""
overlay_ui.py — Inline AI Conversation Card for ActifyXAI Desktop
Dark glassmorphism design, draggable, scrollable, conversational.
"""
import threading
import webbrowser
import tkinter as tk
import customtkinter as ctk
from urllib.parse import quote

from api_client import APIClient
from clipboard_manager import ClipboardManager
from intent_bridge import LLM_URLS


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Exact Premium Palette ──
BG_BASE    = "#0a0a0a"
BG_SURFACE = "#121218"
BG_ELEV    = "#1c1c24"
BG_INPUT   = "#23232d"
BG_MSG_USR = "#1e1e2d"
BORDER     = "#26262b"
BORDER_SFT = "#212126"
FG_TEXT    = "#f5f5f5"
FG_DIM     = "#a3a3a3"
FG_ACCENT  = "#3b82f6"
FG_VIOLET  = "#8b5cf6"
FG_GREEN   = "#3fb950"
FG_YELLOW  = "#d29922"
FONT_BODY  = ("Segoe UI Variable", 12)
FONT_BOLD  = ("Segoe UI Variable Semibold", 12)
FONT_SMALL = ("Segoe UI Variable", 10)
FONT_MONO  = ("Cascadia Code", 11)

ACTION_LABELS = {
    "fix": "🛠 Fix Error",    "explain": "🧠 Explain",
    "summarize": "📝 Summarize", "rewrite": "✍ Rewrite",
    "refactor": "♻ Refactor", "improve": "✨ Improve",
    "shorten": "📏 Shorten",  "research": "🔬 Research",
    "translate": "🌐 Translate",
}

CONVO_WIDTH  = 440
CONVO_HEIGHT = 480


class InlineAICard(ctk.CTkToplevel):
    """
    Persistent conversational AI workspace.
    Appears beside or below the action toolbar.
    """

    def __init__(self, parent_root, text: str, action: str, intent: str,
                 anchor_x: int, anchor_y: int,
                 api_client: APIClient,
                 clipboard: ClipboardManager,
                 on_close=None):
        super().__init__(parent_root)

        self.text       = text
        self.action     = action
        self.intent     = intent
        self.api_client = api_client
        self.clipboard  = clipboard
        self.on_close   = on_close
        self.history    = []   # conversation memory

        # ── Window chrome ───────────────────────────────────────
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "#000001")
        self.attributes("-alpha", 0.96)
        self.configure(fg_color="#000001")
        self.resizable(False, False)

        # Position: smart placement near anchor
        self._place(anchor_x, anchor_y)

        self._build_ui()
        self._make_draggable()

        # Kick off first AI call immediately
        self._call_api(text, action)

    # ── Positioning ─────────────────────────────────────────────
    def _place(self, ax, ay):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = CONVO_WIDTH, CONVO_HEIGHT

        # Prefer right of anchor; fall back left
        x = ax + 12
        if x + w > sw - 10:
            x = ax - w - 12
        if x < 10:
            x = max(10, (sw - w) // 2)

        # Prefer below anchor
        y = ay
        if y + h > sh - 40:
            y = sh - h - 40
        if y < 10:
            y = 10

        self.geometry(f"{w}x{h}+{x}+{y}")

    # ── UI construction ─────────────────────────────────────────
    def _build_ui(self):
        self.outer = ctk.CTkFrame(self, fg_color=BG_BASE, corner_radius=18, border_width=1, border_color=BORDER)
        self.outer.pack(fill="both", expand=True)

        title = ACTION_LABELS.get(self.action, "🧠 ActifyXAI")

        # Header
        hdr = ctk.CTkFrame(self.outer, fg_color="transparent", corner_radius=0,
                           height=42, border_width=0)
        hdr.pack(fill="x", padx=4, pady=(4, 0))
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="🔶", font=("Segoe UI Variable", 14), text_color=FG_ACCENT).pack(side="left", padx=(12, 4), pady=10)
        ctk.CTkLabel(hdr, text=title, font=FONT_BOLD, text_color=FG_PRIMARY).pack(side="left", pady=10)

        close_btn = ctk.CTkButton(hdr, text="✕", width=30, height=26,
                                  fg_color="transparent", text_color=FG_DIM,
                                  hover_color="#2d333b", corner_radius=6,
                                  font=("Segoe UI Variable", 12),
                                  command=self._close)
        close_btn.pack(side="right", padx=8, pady=8)
        self._hdr = hdr  # drag handle

        # Conversation scroll area
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.outer, fg_color="transparent", corner_radius=0,
            scrollbar_button_color="#222226",
            scrollbar_button_hover_color=FG_ACCENT)
        self.scroll_frame.pack(fill="both", expand=True, padx=4, pady=0)

        # Loading indicator (typing effect style)
        self.loading_lbl = ctk.CTkLabel(
            self.scroll_frame,
            text="✨ Orchestrating...",
            font=("Segoe UI Variable", 12, "italic"), text_color=FG_VIOLET,
            justify="left", anchor="w")
        self.loading_lbl.pack(fill="x", padx=16, pady=(20, 4))

        # Separator
        sep = ctk.CTkFrame(self.outer, fg_color=BORDER, height=1, corner_radius=0)
        sep.pack(fill="x")

        # Footer: model info + copy + send
        footer = ctk.CTkFrame(self.outer, fg_color="transparent", corner_radius=0, height=40)
        footer.pack(fill="x", padx=4)
        footer.pack_propagate(False)

        self.model_lbl = ctk.CTkLabel(footer, text="", font=FONT_SMALL,
                                      text_color=FG_DIM, anchor="w")
        self.model_lbl.pack(side="left", padx=12)

        self.send_btn = ctk.CTkButton(
            footer, text="↗ ChatGPT", width=84, height=26,
            fg_color=BG_ELEV, text_color=FG_TEXT,
            hover_color=BORDER_SFT, corner_radius=6,
            font=FONT_SMALL, command=self._send_to_chatgpt)
        self.send_btn.pack(side="right", padx=(4, 10), pady=7)

        self.copy_btn = ctk.CTkButton(
            footer, text="📋 Copy", width=72, height=26,
            fg_color=BG_ELEV, text_color=FG_TEXT,
            hover_color=BORDER_SFT, corner_radius=6,
            font=FONT_SMALL, command=self._copy_result)
        self.copy_btn.pack(side="right", padx=4, pady=7)

        # Input row (follow-up)
        inp_frame = ctk.CTkFrame(self.outer, fg_color="transparent", corner_radius=0, height=52)
        inp_frame.pack(fill="x", padx=4, pady=(0, 4))
        inp_frame.pack_propagate(False)

        self.followup_var = tk.StringVar()
        
        # Follow-up elevated container
        inp_container = ctk.CTkFrame(inp_frame, fg_color=BG_INPUT, corner_radius=14, border_width=1, border_color=BORDER_SFT)
        inp_container.pack(side="left", fill="x", expand=True, padx=(10, 4), pady=6)
        
        self.inp = ctk.CTkEntry(
            inp_container, textvariable=self.followup_var,
            placeholder_text="Ask a follow-up…",
            fg_color="transparent", border_width=0,
            text_color=FG_TEXT, placeholder_text_color=FG_DIM,
            font=FONT_BODY, height=32)
        self.inp.pack(fill="x", padx=10, pady=4)
        self.inp.bind("<Return>", lambda e: self._send_followup())

        send_icon = ctk.CTkButton(
            inp_frame, text="➤", width=36, height=32,
            fg_color=FG_ACCENT, text_color="white",
            hover_color=FG_VIOLET, corner_radius=6,
            font=("Segoe UI Variable", 13), command=self._send_followup)
        send_icon.pack(side="right", padx=(0, 10), pady=7)

        self._last_result = ""

    # ── Message rendering ────────────────────────────────────────
    def _add_message(self, role: str, content: str):
        """Render a chat bubble in the scroll area."""
        bg = BG_ELEV if role == "assistant" else BG_MSG_USR
        border_c = BORDER_SFT if role == "assistant" else BORDER
        
        # Spacer for breathable margins
        spacer = ctk.CTkFrame(self.scroll_frame, fg_color="transparent", height=10)
        spacer.pack(fill="x")

        bubble = ctk.CTkFrame(self.scroll_frame, fg_color=bg, corner_radius=16, border_width=1, border_color=border_c)
        bubble.pack(fill="x", padx=12, pady=4)

        # Header for copy button
        hdr_frame = ctk.CTkFrame(bubble, fg_color="transparent", height=20)
        hdr_frame.pack(fill="x", padx=14, pady=(6, 0))
        
        copy_btn = ctk.CTkButton(
            hdr_frame, text="📋", width=20, height=20,
            fg_color="transparent", text_color=FG_DIM,
            hover_color=BORDER_SFT, corner_radius=6,
            font=("Segoe UI", 11),
            command=lambda: self.clipboard.copy_to_clipboard(lbl.cget("text"))
        )
        copy_btn.pack(side="right")

        # We don't prepend prefixes anymore for a cleaner chat look, but format Markdown nicely.
        lbl = ctk.CTkLabel(bubble, text="",
                     font=FONT_BODY, text_color=FG_TEXT,
                     justify="left", anchor="w", wraplength=380)
        lbl.pack(fill="x", padx=18, pady=(0, 16))

        if role == "assistant":
            # Simulate streaming
            self._type_text(lbl, content, 0)
        else:
            lbl.configure(text=content)
            self.after(20, self._smooth_scroll)

    def _type_text(self, lbl, full_text, index):
        if not lbl.winfo_exists(): return
        
        chunk = 5 # characters per tick for smooth but fast typing
        if index <= len(full_text):
            lbl.configure(text=full_text[:index])
            self._smooth_scroll()
            self.after(10, self._type_text, lbl, full_text, index + chunk)
        else:
            lbl.configure(text=full_text)
            self._smooth_scroll()

    def _smooth_scroll(self):
        try:
            self.scroll_frame._parent_canvas.yview_moveto(1)
        except Exception:
            pass

    # ── API call ─────────────────────────────────────────────────
    def _call_api(self, text: str, action: str):
        self._last_result = ""

        def on_ok(result, model):
            self._last_result = result
            self.history.append({"role": "assistant", "content": result})
            self.after(0, self._on_result, result, model)

        def on_err(msg):
            self.after(0, self._on_error, msg)

        self.api_client.quick_async(
            text=text, action=action,
            intent=self.intent, on_success=on_ok, on_error=on_err)

    def _on_result(self, result: str, model: str):
        if self.loading_lbl:
            self.loading_lbl.destroy()
            self.loading_lbl = None
        self._add_message("assistant", result)
        short_model = model.split("-")[0] if model else ""
        if short_model:
            self.model_lbl.configure(text=f"⚡ {short_model}", text_color=FG_GREEN)
        # Scroll to bottom
        self.after(50, lambda: self.scroll_frame._parent_canvas.yview_moveto(1))

    def _on_error(self, msg: str):
        if self.loading_lbl:
            self.loading_lbl.destroy()
            self.loading_lbl = None
        self._add_message("assistant", msg)

    # ── Follow-up ────────────────────────────────────────────────
    def _send_followup(self):
        q = self.followup_var.get().strip()
        if not q:
            return
        self.followup_var.set("")
        self.history.append({"role": "user", "content": q})
        self._add_message("user", q)

        # Show loading
        self.loading_lbl = ctk.CTkLabel(
            self.scroll_frame, text="✨ Orchestrating...",
            font=("Segoe UI Variable", 12, "italic"), text_color=FG_VIOLET,
            justify="left", anchor="w")
        self.loading_lbl.pack(fill="x", padx=16, pady=(4, 4))
        self.after(50, lambda: self.scroll_frame._parent_canvas.yview_moveto(1))

        self.api_client.followup_async(
            messages=self.history,
            on_success=lambda r, m: self.after(0, self._on_result, r, m),
            on_error=lambda e: self.after(0, self._on_error, e))

    # ── Actions ──────────────────────────────────────────────────
    def _copy_result(self):
        if self._last_result:
            self.clipboard.copy_to_clipboard(self._last_result)
            self.copy_btn.configure(text="✅ Copied!")
            self.after(1800, lambda: self.copy_btn.configure(text="📋 Copy"))

    def _send_to_chatgpt(self):
        prompt = f"Help me with the following:\n\n{self.text[:500]}"
        if self._last_result:
            prompt += f"\n\nContext from previous analysis:\n{self._last_result[:400]}"
        self.clipboard.copy_to_clipboard(prompt)
        webbrowser.open(LLM_URLS["chatgpt"])
        self.send_btn.configure(text="✅ Prompt Copied")
        self.after(2000, lambda: self.send_btn.configure(text="↗ ChatGPT"))

    def _close(self):
        if callable(self.on_close):
            self.on_close()
        self.destroy()

    # ── Drag ────────────────────────────────────────────────────
    def _make_draggable(self):
        self._drag_x = 0
        self._drag_y = 0

        def on_down(e):
            self._drag_x = e.x_root - self.winfo_x()
            self._drag_y = e.y_root - self.winfo_y()

        def on_move(e):
            nx = e.x_root - self._drag_x
            ny = e.y_root - self._drag_y
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            nx = max(0, min(nx, sw - CONVO_WIDTH))
            ny = max(0, min(ny, sh - CONVO_HEIGHT))
            self.geometry(f"+{nx}+{ny}")

        self._hdr.bind("<ButtonPress-1>", on_down)
        self._hdr.bind("<B1-Motion>", on_move)
