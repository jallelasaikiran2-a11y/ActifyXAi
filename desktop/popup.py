"""
popup.py — Contextual Action Toolbar for ActifyXAI Desktop
Minimal, dark glassmorphism, near-cursor, temporary launcher.
"""
import webbrowser
import tkinter as tk
import customtkinter as ctk
from urllib.parse import quote

from intent_bridge import get_actions, detect_intent, APPS, build_smart_query, LLM_URLS
from overlay_ui import InlineAICard
from clipboard_manager import ClipboardManager
from api_client import APIClient

ctk.set_appearance_mode("dark")

# ── Premium Palette ──────────────────────────────────────────
BG_VOID     = "#06060a"
BG_GLASS    = "#0c0c14"
BG_SURFACE  = "#10101a"
BG_ELEV     = "#181824"
BORDER_GLOW = "#252538"
BORDER_IN   = "#1c1c2c"
BORDER_SFT  = "#17172a"

FG_TEXT     = "#eeeef5"
FG_DIM      = "#5a5a78"
FG_SUB      = "#8888a8"
FG_ACCENT   = "#5b72f5"
FG_VIOLET   = "#9d7df0"

FONT_BODY   = ("Segoe UI Variable", 12)
FONT_SMALL  = ("Segoe UI Variable", 10)
FONT_BADGE  = ("Segoe UI Variable Semibold", 9)
FONT_BTN    = ("Segoe UI Variable", 11)

BADGE_LABELS = {
    "transact_food": "food",
    "transact_shop": "shop",
    "navigate":      "navigate",
    "fix":           "code",
    "transform":     "transform",
    "writing":       "writing",
    "search":        "search",
    "informational": "info",
    "explore":       "explore",
}

POPUP_WIDTH = 330


class ActionToolbar(ctk.CTkToplevel):
    """
    Temporary contextual action toolbar.
    Appears near cursor, shows intent-aware action buttons.
    """

    def __init__(self, parent_root, text: str,
                 cursor_x: int, cursor_y: int,
                 api_client: APIClient,
                 clipboard: ClipboardManager,
                 on_dismissed=None):
        super().__init__(parent_root)

        self.text         = text
        self.cursor_x     = cursor_x
        self.cursor_y     = cursor_y
        self.api_client   = api_client
        self.clipboard    = clipboard
        self.on_dismissed = on_dismissed
        self._ia_card     = None
        self._sub_popup   = None

        self.intent  = detect_intent(text)
        self.actions = get_actions(self.intent)

        # ── Window chrome ────────────────────────────────────
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "#000001")
        self.attributes("-alpha", 0.97)
        self.configure(fg_color="#000001")
        self.resizable(False, False)

        self._build_ui()
        self._place()
        self._make_draggable()

        self.bind("<FocusOut>", self._maybe_close)
        self.after(200, self._bind_outside_click)

    # ── Positioning (untouched) ──────────────────────────────
    def _place(self):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        h  = self.winfo_reqheight() or 60

        x = self.cursor_x - POPUP_WIDTH // 2
        y = self.cursor_y - h - 16

        if x < 8:                    x = 8
        if x + POPUP_WIDTH > sw - 8: x = sw - POPUP_WIDTH - 8
        if y < 8:                    y = self.cursor_y + 24
        if y + h > sh - 8:           y = sh - h - 8

        self.geometry(f"{POPUP_WIDTH}x{h}+{x}+{y}")

    # ── UI construction ──────────────────────────────────────
    def _build_ui(self):
        # ── Root glass card ──
        outer = ctk.CTkFrame(
            self,
            fg_color=BG_GLASS,
            corner_radius=20,
            border_width=1,
            border_color=BORDER_GLOW
        )
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        # ── Header: intent badge + close ──
        header_row = ctk.CTkFrame(outer, fg_color="transparent")
        header_row.pack(fill="x", padx=10, pady=(10, 0))

        # Intent badge — small rounded chip
        badge_pill = ctk.CTkLabel(
            header_row,
            text=f"  ◈ {BADGE_LABELS.get(self.intent, self.intent)}  ",
            font=FONT_BADGE,
            text_color=FG_VIOLET,
            fg_color=BG_ELEV,
            corner_radius=8,
            height=22
        )
        badge_pill.pack(side="left")

        close_btn = ctk.CTkButton(
            header_row,
            text="✕",
            width=24,
            height=20,
            fg_color="transparent",
            text_color=FG_DIM,
            hover_color=BG_ELEV,
            corner_radius=6,
            font=("Segoe UI Variable", 9),
            command=self._dismiss
        )
        close_btn.pack(side="right")

        # ── Hairline separator ──
        ctk.CTkFrame(
            outer, fg_color=BORDER_IN, height=1, corner_radius=0
        ).pack(fill="x", padx=10, pady=(8, 0))

        # ── Action button row ──
        btn_row = ctk.CTkFrame(outer, fg_color="transparent")
        btn_row.pack(fill="x", padx=8, pady=(6, 10))

        for item in self.actions:
            btn = ctk.CTkButton(
                btn_row,
                text=item["label"],
                width=0,
                height=30,
                fg_color="transparent",
                text_color=FG_SUB,
                hover_color=BG_ELEV,
                corner_radius=10,
                font=FONT_BTN,
                command=lambda i=item: self._on_action(i)
            )
            btn.pack(side="left", padx=2, pady=0, fill="x", expand=True)

        self._outer = outer   # drag handle

    # ── Action handler (untouched logic) ────────────────────
    def _on_action(self, item: dict):
        atype = item["type"]

        if atype == "DIRECT_ACTION":
            ax, ay = self.winfo_x() + POPUP_WIDTH + 6, self.winfo_y()
            action = item["action"]
            self._open_ia_card(action, ax, ay)

        elif atype == "LLM_ACTION":
            from intent_bridge import build_smart_query
            prompt = f"Help me with: {self.text[:500]}"
            self.clipboard.copy_to_clipboard(prompt)
            llm = item.get("llm", "chatgpt")
            webbrowser.open(LLM_URLS.get(llm, LLM_URLS["chatgpt"]))
            self._close_toolbar()

        elif atype == "selector":
            category = item["category"]
            apps     = APPS.get(category, [])
            if not apps:
                return
            self._open_app_selector(apps, category)

    def _open_ia_card(self, action: str, ax: int, ay: int):
        self._close_sub()
        self.withdraw()

        def on_ia_closed():
            self._ia_card = None
            self._dismiss()

        self._ia_card = InlineAICard(
            parent_root=self.master,
            text=self.text,
            action=action,
            intent=self.intent,
            anchor_x=ax,
            anchor_y=ay,
            api_client=self.api_client,
            clipboard=self.clipboard,
            on_close=on_ia_closed,
        )

    def _open_app_selector(self, apps: list, category: str):
        self._close_sub()
        sub = AppSelectorPopup(
            parent_root=self.master,
            apps=apps,
            category=category,
            text=self.text,
            intent=self.intent,
            clipboard=self.clipboard,
            anchor_x=self.winfo_x(),
            anchor_y=self.winfo_y() + self.winfo_height() + 4,
            on_chosen=self._close_all,
        )
        self._sub_popup = sub

    # ── Lifecycle (untouched) ────────────────────────────────
    def _close_toolbar(self):
        self._close_sub()
        self.destroy()
        if callable(self.on_dismissed):
            self.on_dismissed()

    def _close_sub(self):
        if self._sub_popup:
            try:
                self._sub_popup.destroy()
            except Exception:
                pass
            self._sub_popup = None

    def _close_all(self):
        self._close_sub()
        self._dismiss()

    def _dismiss(self):
        try:
            self.destroy()
        except Exception:
            pass
        if callable(self.on_dismissed):
            self.on_dismissed()

    def _bind_outside_click(self):
        self.master.bind("<Button-1>", self._on_root_click, "+")

    def _on_root_click(self, e):
        try:
            if self.winfo_exists():
                wx, wy = self.winfo_x(), self.winfo_y()
                ww, wh = self.winfo_width(), self.winfo_height()
                if not (wx <= e.x_root <= wx + ww and wy <= e.y_root <= wy + wh):
                    self._dismiss()
        except Exception:
            pass

    def _maybe_close(self, e):
        self.after(100, self._check_focus)

    def _check_focus(self):
        focused = self.focus_get()
        if focused is None or focused is self.master:
            self._dismiss()

    # ── Drag (untouched) ─────────────────────────────────────
    def _make_draggable(self):
        self._dx = self._dy = 0

        def down(e):
            self._dx = e.x_root - self.winfo_x()
            self._dy = e.y_root - self.winfo_y()

        def move(e):
            x = e.x_root - self._dx
            y = e.y_root - self._dy
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = max(0, min(x, sw - POPUP_WIDTH))
            self.geometry(f"+{x}+{y}")

        self._outer.bind("<ButtonPress-1>", down)
        self._outer.bind("<B1-Motion>", move)


# ================================================================
# APP SELECTOR SUB-POPUP
# ================================================================

class AppSelectorPopup(ctk.CTkToplevel):
    """Small floating app picker shown when user clicks a 'selector' action."""

    def __init__(self, parent_root, apps: list, category: str, text: str,
                 intent: str, clipboard: ClipboardManager,
                 anchor_x: int, anchor_y: int, on_chosen=None):
        super().__init__(parent_root)

        self.apps      = apps
        self.category  = category
        self.text      = text
        self.intent    = intent
        self.clipboard = clipboard
        self.on_chosen = on_chosen

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "#000001")
        self.attributes("-alpha", 0.97)
        self.configure(fg_color="#000001")

        self._build_ui()
        self._place(anchor_x, anchor_y)

    def _place(self, ax, ay):
        self.update_idletasks()
        w = 230
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = min(ax, sw - w - 8)
        y = ay
        if y + self.winfo_reqheight() > sh - 8:
            y = ay - self.winfo_reqheight() - 8
        self.geometry(f"{w}x{self.winfo_reqheight() + 4}+{x}+{y}")

    def _build_ui(self):
        frame = ctk.CTkFrame(
            self,
            fg_color=BG_GLASS,
            corner_radius=16,
            border_width=1,
            border_color=BORDER_GLOW
        )
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        ctk.CTkLabel(
            frame,
            text="  Open with",
            font=FONT_BADGE,
            text_color=FG_DIM
        ).pack(anchor="w", padx=12, pady=(10, 4))

        ctk.CTkFrame(
            frame, fg_color=BORDER_IN, height=1, corner_radius=0
        ).pack(fill="x", padx=10, pady=(0, 4))

        for app in self.apps:
            btn = ctk.CTkButton(
                frame,
                text=f'{app["icon"]}  {app["name"]}',
                height=32,
                fg_color="transparent",
                text_color=FG_TEXT,
                hover_color=BG_ELEV,
                anchor="w",
                corner_radius=8,
                font=FONT_BODY,
                command=lambda a=app: self._open_app(a)
            )
            btn.pack(fill="x", padx=8, pady=2)

        ctk.CTkFrame(
            frame, fg_color=BORDER_IN, height=1, corner_radius=0
        ).pack(fill="x", padx=10, pady=(4, 0))

        ctk.CTkLabel(
            frame,
            text="Opens in browser tab",
            font=FONT_BADGE,
            text_color=FG_DIM
        ).pack(pady=(6, 10))

    def _open_app(self, app: dict):
        query = build_smart_query(self.text, self.category, self.intent)
        url   = app["url"] + quote(query, safe="")
        self.clipboard.copy_to_clipboard(query)
        webbrowser.open(url)
        if callable(self.on_chosen):
            self.on_chosen()


# ================================================================
# LLM CHOOSER SUB-POPUP
# ================================================================

class LLMChooserPopup(ctk.CTkToplevel):
    """AI LLM picker for 'Ask AI' actions."""

    LLMS = [
        {"name": "⚡ Instant Answer", "llm": "ia"},
        {"name": "🤖 ChatGPT",        "llm": "chatgpt"},
        {"name": "🟠 Claude",         "llm": "claude"},
        {"name": "🔷 Gemini",         "llm": "gemini"},
        {"name": "🟣 Perplexity",     "llm": "perplexity"},
        {"name": "🐋 DeepSeek",       "llm": "deepseek"},
    ]

    def __init__(self, parent_root, text: str, action: str, intent: str,
                 clipboard: ClipboardManager, api_client: APIClient,
                 anchor_x: int, anchor_y: int,
                 on_ia=None, on_chosen=None):
        super().__init__(parent_root)

        self.text       = text
        self.action     = action
        self.intent     = intent
        self.clipboard  = clipboard
        self.api_client = api_client
        self.on_ia      = on_ia
        self.on_chosen  = on_chosen

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "#000001")
        self.attributes("-alpha", 0.97)
        self.configure(fg_color="#000001")

        self._build_ui()
        w = 230
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = min(anchor_x, sw - w - 8)
        y = min(anchor_y, sh - 300)
        self.geometry(f"{w}+{x}+{y}")

    def _build_ui(self):
        frame = ctk.CTkFrame(
            self,
            fg_color=BG_GLASS,
            corner_radius=16,
            border_width=1,
            border_color=BORDER_GLOW
        )
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        ctk.CTkLabel(
            frame,
            text="  Choose AI",
            font=FONT_BADGE,
            text_color=FG_ACCENT
        ).pack(anchor="w", padx=12, pady=(10, 4))

        ctk.CTkFrame(
            frame, fg_color=BORDER_IN, height=1, corner_radius=0
        ).pack(fill="x", padx=10, pady=(0, 4))

        for entry in self.LLMS:
            btn = ctk.CTkButton(
                frame,
                text=entry["name"],
                height=32,
                fg_color="transparent",
                text_color=FG_TEXT,
                hover_color=BG_ELEV,
                anchor="w",
                corner_radius=8,
                font=FONT_BODY,
                command=lambda e=entry: self._choose(e)
            )
            btn.pack(fill="x", padx=8, pady=2)

    def _choose(self, entry: dict):
        llm = entry["llm"]
        if llm == "ia":
            if callable(self.on_ia):
                self.on_ia()
        else:
            prompt = f"Help me with the following ({self.action}):\n\n{self.text[:500]}"
            self.clipboard.copy_to_clipboard(prompt)
            webbrowser.open(LLM_URLS.get(llm, LLM_URLS["chatgpt"]))
        self.destroy()
        if callable(self.on_chosen):
            self.on_chosen()