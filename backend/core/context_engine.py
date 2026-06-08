import re
from urllib.parse import urlparse


class ContextEngine:
    """Analyzes selected text + page URL to produce a rich context dictionary."""

    # hostname regex → actions to boost or suppress
    DOMAIN_SIGNALS = {
        r"(wikipedia|britannica|encyclopaedia)\.": {
            "boost": ["informational", "explain", "summarize"], "suppress": ["fix"]
        },
        r"(stackoverflow|github|gitlab|dev\.to|hackernoon|replit|codepen)\.": {
            "boost": ["fix", "refactor"], "suppress": []
        },
        r"(amazon|flipkart|myntra|ebay|etsy|croma|meesho|tatacliq|ajio)\.": {
            "boost": ["compare", "shop"], "suppress": ["fix", "explain"]
        },
        r"(medium|substack|towardsdatascience|techcrunch|theverge|wired|"
        r"bloomberg|reuters|bbc|cnn|nytimes|thehindu|ndtv|techradar)\.": {
            "boost": ["informational", "summarize", "research"], "suppress": ["fix"]
        },
        r"(zomato|swiggy|ubereats|doordash|grubhub|blinkit|zepto)\.": {
            "boost": ["food_order"], "suppress": ["fix", "explain"]
        },
        r"(google|bing|duckduckgo|yahoo)\.": {
            "boost": ["research"], "suppress": ["search"]
        },
        r"(youtube|vimeo|dailymotion)\.": {
            "boost": ["summarize", "explain"], "suppress": ["fix"]
        },
    }

    def analyze(self, text: str, context_url: str = None) -> dict:
        words = text.split()
        length = len(words)
        content_type = "code" if self._is_code(text) else "text"
        complexity = "high" if length > 50 else "low"

        hostname = self._extract_hostname(context_url) if context_url else ""
        domain_boost, domain_suppress = self._get_domain_signals(hostname)

        return {
            "content_type": content_type,
            "length": length,
            "complexity": complexity,
            "hostname": hostname,
            "domain_boost": domain_boost,
            "domain_suppress": domain_suppress,
        }

    # ── helpers ────────────────────────────────────────────────────

    def _is_code(self, text: str) -> bool:
        """Heuristic: count code-like signals; >= 2 means code."""
        signals = [
            "{", "}", "def ", "function ", "class ", "import ",
            "const ", "let ", "var ", "=>", "->", "#include",
            "public ", "private ", "return ", "async ", "await ",
        ]
        return sum(1 for s in signals if s in text) >= 2

    def _extract_hostname(self, url: str) -> str:
        try:
            return urlparse(url).hostname or ""
        except Exception:
            return ""

    def _get_domain_signals(self, hostname: str):
        boost, suppress = [], []
        for pattern, signals in self.DOMAIN_SIGNALS.items():
            if re.search(pattern, hostname, re.IGNORECASE):
                boost.extend(signals.get("boost", []))
                suppress.extend(signals.get("suppress", []))
        return boost, suppress
