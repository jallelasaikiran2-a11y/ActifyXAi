import os
from pathlib import Path
from groq import Groq, AuthenticationError, APIConnectionError, RateLimitError
from dotenv import load_dotenv

# Always resolve .env from this file's parent directory (backend/)
# This fixes silent failures when uvicorn is run from a different working directory
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


class ExecutionLayer:
    """Executes the prompt against the selected Groq model."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        # Strip surrounding quotes if user accidentally included them in .env
        self.api_key = self.api_key.strip('"').strip("'")

        if self.api_key and self.api_key != "YOUR_GROQ_API_KEY_HERE":
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None

    def execute(self, prompt: str, model: str) -> str:
        if not self.client:
            return (
                "⚠️ Backend not configured: GROQ_API_KEY is missing or still set to placeholder. "
                f"Edit {_ENV_PATH} and add your key from https://console.groq.com"
            )

        try:
            completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are ActifyXAI, an intelligent assistant. "
                            "Provide concise, accurate, and helpful answers."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                model=model,
                temperature=0.3,
                max_tokens=1024,
            )
            return completion.choices[0].message.content

        except AuthenticationError:
            return (
                "⚠️ Groq API key is invalid or expired (401). "
                "Please generate a new key at https://console.groq.com/keys "
                f"and update {_ENV_PATH}"
            )
        except RateLimitError:
            return (
                "⚠️ Groq rate limit reached. "
                "Wait a moment and try again, or upgrade your Groq plan."
            )
        except APIConnectionError:
            return (
                "⚠️ Cannot reach Groq API. "
                "Check your internet connection and try again."
            )
        except Exception as e:
            return f"⚠️ Execution error: {str(e)}"

    def execute_with_system(self, system: str, user_content: str, model: str) -> str:
        """Separates system and user roles — gives Groq cleaner context for better output."""
        if not self.client:
            return (
                "⚠️ Backend not configured: GROQ_API_KEY is missing or still set to placeholder. "
                f"Edit {_ENV_PATH} and add your key from https://console.groq.com"
            )
        try:
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user_content},
                ],
                model=model,
                temperature=0.3,
                max_tokens=1024,
            )
            return completion.choices[0].message.content
        except AuthenticationError:
            return (
                "⚠️ Groq API key is invalid or expired (401). "
                "Please generate a new key at https://console.groq.com/keys "
                f"and update {_ENV_PATH}"
            )
        except RateLimitError:
            return "⚠️ Groq rate limit reached. Wait a moment and try again."
        except APIConnectionError:
            return "⚠️ Cannot reach Groq API. Check your internet connection."
        except Exception as e:
            return f"⚠️ Execution error: {str(e)}"



    def health_check(self) -> dict:
        """Run a minimal test call to verify the key is working."""
        if not self.client:
            return {"ok": False, "error": "no_key", "detail": "GROQ_API_KEY not set"}
        try:
            self.client.chat.completions.create(
                messages=[{"role": "user", "content": "ping"}],
                model="llama-3.1-8b-instant",
                max_tokens=1,
            )
            return {"ok": True, "error": None}
        except AuthenticationError:
            return {"ok": False, "error": "invalid_key",
                    "detail": "401 — key is invalid or expired. Regenerate at console.groq.com/keys"}
        except RateLimitError:
            return {"ok": False, "error": "rate_limit",
                    "detail": "Rate limit hit — key is valid but quota exceeded"}
        except Exception as e:
            return {"ok": False, "error": "unknown", "detail": str(e)}
