"""
api_client.py — Backend HTTP client for ActifyXAI Desktop
Communicates with the existing FastAPI backend.
"""
import threading
import requests
from settings import settings_mgr

TIMEOUT = 25  # seconds

class APIClient:
    """Async-friendly API client with callbacks."""

    def __init__(self):
        self._health_ok = None

    @property
    def base_url(self):
        return f"{settings_mgr.get('backend_url').rstrip('/')}/api"

    # ── Health check ─────────────────────────────────────────────
    def check_health(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/health", timeout=4)
            ok = r.status_code == 200 and r.json().get("groq_live", False)
            self._health_ok = ok
            return ok
        except Exception:
            self._health_ok = False
            return False

    # ── Quick/Instant Answer ─────────────────────────────────────
    def quick_async(
        self,
        text: str,
        action: str,
        intent: str,
        on_success,
        on_error,
        context_url: str = "",
    ):
        """Call /api/quick in a daemon thread; invoke callback on completion."""
        def _run():
            try:
                payload = {
                    "text": text,
                    "action": action,
                    "intent": intent,
                    "context_url": context_url,
                }
                r = requests.post(
                    f"{self.base_url}/quick",
                    json=payload,
                    timeout=TIMEOUT,
                )
                if r.status_code == 200:
                    data = r.json()
                    result  = data.get("result", "No result returned.")
                    model   = data.get("model_used", "")
                    on_success(result, model)
                else:
                    on_error(f"⚠️ Backend error {r.status_code}: {r.text[:200]}")
            except requests.exceptions.ConnectionError:
                on_error("⚠️ Cannot connect to backend.\nMake sure the FastAPI server is running:\n  uvicorn main:app --reload")
            except requests.exceptions.Timeout:
                on_error("⚠️ Request timed out. The model may be busy — please retry.")
            except Exception as exc:
                on_error(f"⚠️ Unexpected error: {exc}")

        threading.Thread(target=_run, daemon=True).start()

    # ── Follow-up conversation ────────────────────────────────────
    def followup_async(
        self,
        messages: list,
        on_success,
        on_error,
    ):
        """
        Send conversation history as follow-up.
        Uses /quick with the concatenated context baked into the text.
        """
        if not messages:
            on_error("⚠️ No conversation history.")
            return

        # Build a compact context string from history
        context_parts = []
        for msg in messages[:-1]:  # everything except latest
            role = "User" if msg["role"] == "user" else "AI"
            context_parts.append(f"{role}: {msg['content'][:300]}")
        last_user = messages[-1]["content"] if messages else ""

        combined_text = "\n\n".join(context_parts) + f"\n\nFollow-up question: {last_user}"

        self.quick_async(
            text=combined_text[:700],
            action="explain",
            intent="",
            on_success=on_success,
            on_error=on_error,
        )
