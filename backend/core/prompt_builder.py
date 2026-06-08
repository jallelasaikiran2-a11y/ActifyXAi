class PromptBuilder:
    """Constructs the optimal prompt based on action and context."""

    def build(self, action: str, text: str, context: dict) -> str:
        builder = getattr(self, f"_build_{action}", self._build_default)
        return builder(text, context)

    # ── per-action builders ─────────────────────────────────────────

    def _build_explain(self, text: str, context: dict) -> str:
        if context.get("content_type") == "code":
            return (
                "You are a senior developer and technical educator.\n\n"
                "Explain this code step-by-step so a junior developer can fully understand it.\n\n"
                f'"""\n{text}\n"""'
            )
        return (
            "You are a knowledgeable expert who explains complex topics in plain language.\n\n"
            "Explain the following clearly and concisely. Use simple language, real-world "
            "analogies, and examples where helpful.\n\n"
            f'"""\n{text}\n"""'
        )

    def _build_fix(self, text: str, context: dict) -> str:
        if context.get("content_type") == "code":
            return (
                "You are a senior software engineer specializing in debugging.\n\n"
                "Fix all bugs in the code below. For each fix, explain what was wrong "
                "and why the fix works. Preserve the original language and style.\n\n"
                "Output format:\n"
                "1. ✅ Fixed code\n"
                "2. 🔍 What was wrong (brief)\n"
                "3. 💡 Best-practice tip\n\n"
                f'"""\n{text}\n"""'
            )
        return (
            "You are a professional editor.\n\n"
            "Review and fix any grammatical, logical, or clarity errors in the text below. "
            "Explain each correction briefly.\n\n"
            f'"""\n{text}\n"""'
        )

    def _build_summarize(self, text: str, context: dict) -> str:
        length = context.get("length", 0)
        depth = "detailed" if length > 150 else "concise"
        return (
            "You are an expert analyst and clear communicator.\n\n"
            f"Provide a {depth} summary of the following content.\n\n"
            "Output format:\n"
            "1. 🎯 One-line summary\n"
            "2. 📌 Key points (3–5 bullets)\n"
            "3. 💬 Main takeaway\n\n"
            f'"""\n{text}\n"""'
        )

    def _build_rewrite(self, text: str, context: dict) -> str:
        return (
            "You are a professional writer and communication expert.\n\n"
            "Rewrite the following text to be clearer, more concise, and more impactful "
            "while preserving the original meaning and tone.\n\n"
            "Output format:\n"
            "1. ✍️ Rewritten version\n"
            "2. 🔄 Alternative version (different tone)\n"
            "3. 📝 Key changes made\n\n"
            f'"""\n{text}\n"""'
        )

    def _build_refactor(self, text: str, context: dict) -> str:
        return (
            "You are a senior software architect focused on clean, maintainable code.\n\n"
            "Refactor the code below to improve readability, performance, and maintainability. "
            "Do NOT change the core logic. Follow best practices for the detected language.\n\n"
            "Output format:\n"
            "1. ♻️ Refactored code\n"
            "2. 📋 Changes made (bullet list)\n"
            "3. ⚡ Improvement summary\n\n"
            f'"""\n{text}\n"""'
        )

    def _build_research(self, text: str, context: dict) -> str:
        hostname = context.get("hostname", "")
        source_hint = f" (sourced from {hostname})" if hostname else ""
        return (
            "You are a research expert and analyst.\n\n"
            f"Provide a comprehensive research overview of the following topic{source_hint}.\n\n"
            "Output format:\n"
            "1. 📖 Core concept explanation\n"
            "2. 🔑 Key facts and context\n"
            "3. 🌍 Real-world implications or applications\n"
            "4. 🔗 Related concepts worth exploring\n"
            "5. ⚠️ Caveats or limitations\n\n"
            f'"""\n{text}\n"""'
        )

    def _build_translate(self, text: str, context: dict) -> str:
        return (
            "You are an expert translator.\n\n"
            "Detect the source language and translate the following text into English. "
            "If it is already in English, translate it to Spanish as a default.\n\n"
            f'"""\n{text}\n"""'
        )

    def _build_default(self, text: str, context: dict) -> str:
        return (
            "You are ActifyXAI, an intelligent assistant.\n\n"
            f"Perform an intelligent analysis of the following content:\n\n"
            f'"""\n{text}\n"""'
        )
