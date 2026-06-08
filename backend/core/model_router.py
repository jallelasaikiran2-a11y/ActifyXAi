class ModelRouter:
    """Routes the prompt to the most suitable LLM based on task complexity."""

    # Current Groq free-tier models (2026-05)
    FAST_MODEL    = "llama-3.1-8b-instant"     # default — lowest latency
    CAPABLE_MODEL = "llama-3.3-70b-versatile"  # complex code / long text

    def route(self, context: dict, action: str) -> str:
        is_complex_code = (
            context.get("content_type") == "code"
            and context.get("complexity") == "high"
        )
        needs_depth = action in ("refactor", "research")
        is_long_text = context.get("length", 0) > 200  # word count

        if is_complex_code or needs_depth or is_long_text:
            return self.CAPABLE_MODEL
        return self.FAST_MODEL
