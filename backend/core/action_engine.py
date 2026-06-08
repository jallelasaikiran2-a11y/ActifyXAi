class ActionEngine:
    """Determines the appropriate action based on user input and context."""

    VALID_ACTIONS = {
        "explain", "fix", "summarize", "refactor",
        "rewrite", "research", "translate", "informational",
    }
    # Map informational back to explain for prompt building
    _ALIAS = {"informational": "explain"}

    def determine_action(self, requested_action: str, context: dict) -> str:
        action = requested_action.lower().strip()

        # Resolve alias (e.g. informational → explain)
        action = self._ALIAS.get(action, action)

        if action in self.VALID_ACTIONS:
            # Honour domain suppression — fall back gracefully
            if action in context.get("domain_suppress", []):
                return self._from_domain_boost(context)
            return action

        # Unknown action: try domain boost or smart default
        return self._from_domain_boost(context)

    def _from_domain_boost(self, context: dict) -> str:
        for boosted in context.get("domain_boost", []):
            candidate = self._ALIAS.get(boosted, boosted)
            if candidate in self.VALID_ACTIONS:
                return candidate
        # Ultimate fallback based on content type
        return "fix" if context.get("content_type") == "code" else "explain"
