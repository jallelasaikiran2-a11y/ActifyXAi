from fastapi import APIRouter, HTTPException
from models.schemas import ActionRequest, ActionResponse, QuickRequest, QuickResponse
from core.context_engine import ContextEngine
from core.action_engine import ActionEngine
from core.prompt_builder import PromptBuilder
from core.model_router import ModelRouter
from core.execution_layer import ExecutionLayer

router = APIRouter()

# Initialize pipeline (singletons — loaded once at startup)
context_engine  = ContextEngine()
action_engine   = ActionEngine()
prompt_builder  = PromptBuilder()
model_router    = ModelRouter()
execution_layer = ExecutionLayer()


@router.post("/execute", response_model=ActionResponse)
async def execute_action(request: ActionRequest):
    """Full pipeline: context → action → prompt → model → result."""
    try:
        context = context_engine.analyze(request.text, request.context_url)
        action  = action_engine.determine_action(request.action, context)
        prompt  = prompt_builder.build(action, request.text, context)
        model   = model_router.route(context, action)
        result  = execution_layer.execute(prompt, model)
        return ActionResponse(result=result, action_taken=action, model_used=model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick", response_model=QuickResponse)
async def quick_answer(request: QuickRequest):
    """
    IA (Instant Answer) endpoint — intent-aware prompts, fastest Groq model.
    Accepts optional `intent` field from extension for better routing.
    """
    try:
        action  = (request.action or "explain").lower().strip()
        text    = request.text[:600].strip()
        intent  = getattr(request, "intent", "") or ""
        hostname = ""
        if request.context_url:
            from urllib.parse import urlparse
            hostname = urlparse(request.context_url).hostname or ""

        # ── Intent-aware prompt builders ──────────────────────────
        def is_code(t):
            signals = ["def ", "function ", "class ", "import ", "const ", "let ",
                       "var ", "=>", "->", "{", "}", "return ", "async ", "await "]
            return sum(1 for s in signals if s in t) >= 2

        code = is_code(text)

        if action == "fix":
            if code:
                system = (
                    "You are a senior software engineer and debugger. "
                    "Analyze the code or error below. "
                    "Respond with: 1) ✅ Root cause (1-2 sentences) "
                    "2) 🔧 Fixed version (code block) "
                    "3) 💡 Prevention tip. Be concise and precise."
                )
            else:
                system = (
                    "You are a professional editor. Fix grammatical or clarity issues. "
                    "Show: 1) ✅ Fixed version 2) 📝 Key changes. Be brief."
                )

        elif action == "explain":
            if code or intent == "fix":
                system = (
                    "You are a senior developer and educator. "
                    "Explain this code or error clearly: "
                    "1) 📖 What it does/means (plain language) "
                    "2) 🔑 Why this happens "
                    "3) 💡 Simple analogy or example. "
                    "Be concise — max 200 words."
                )
            elif intent == "informational":
                system = (
                    "You are a knowledgeable expert. Explain this concept clearly: "
                    "1) 📖 What it means "
                    "2) 🌍 Why it matters "
                    "3) ⚡ Key insight or real-world use. "
                    "Keep it under 180 words. Use bullet points where helpful."
                )
            else:
                system = (
                    "You are a helpful expert. Explain this clearly and concisely. "
                    "Use simple language, a real-world analogy if helpful, "
                    "and highlight the single most important insight. Max 150 words."
                )

        elif action == "summarize":
            system = (
                "You are an expert analyst. Summarize this content: "
                "1) 🎯 One-line summary "
                "2) 📌 3-5 key points (bullets) "
                "3) 💬 Main takeaway. "
                "Be crisp — max 160 words."
            )

        elif action in ("rewrite", "improve"):
            if intent == "transform" or not code:
                system = (
                    "You are a professional writer. Rewrite this text to be clearer, "
                    "more professional, and more impactful while keeping the original meaning. "
                    "Show: 1) ✍️ Rewritten version 2) 📝 Key improvements. "
                    "Be concise."
                )
            else:
                system = "Improve this text professionally. Show the improved version and briefly explain changes."

        elif action == "shorten":
            system = (
                "Shorten this text to its essential meaning. "
                "Remove filler, keep every important point. "
                "Show the shortened version only — no explanation needed."
            )

        elif action == "refactor":
            system = (
                "You are a senior software architect. Refactor this code: "
                "1) ♻️ Refactored version (code block) "
                "2) 📋 Changes made (bullets) "
                "3) ⚡ Why it's better. "
                "Preserve all functionality. Be concise."
            )

        elif action == "research":
            source = f" (from {hostname})" if hostname else ""
            system = (
                f"You are a research expert. Give a focused overview of this topic{source}: "
                "1) 📖 Core concept "
                "2) 🔑 Key facts "
                "3) 🌍 Real-world significance. "
                "Max 200 words. Use bullets."
            )

        elif action == "translate":
            system = (
                "Detect the source language and translate to English. "
                "If already English, translate to Spanish. "
                "Show: Language detected → Translation. No extra commentary."
            )

        elif action == "command":
            # Advanced RAG-enhanced orchestration
            # Analyzes the app context embedded in the text
            system = (
                "You are ActifyXAI, a premium spatial AI orchestration layer integrated into the desktop.\n"
                "Acknowledge the context and user's intent conversationally. Do not jump directly into robotic API-like answers.\n"
                "Feel highly intelligent and human-aware.\n"
                "Example - User: 'This bug is driving me crazy'\n"
                "GOOD: 'Yeah — bugs like this are frustrating because the visible error often isn’t the real cause. Here’s what’s likely happening...'\n"
                "BAD: 'The issue is caused by...'\n"
                "Adapt your style:\n"
                "- Coding/Development (e.g., VS Code context, code snippets): Concise technical guidance.\n"
                "- Learning: Educational and approachable.\n"
                "- Confusion: Guided explanation.\n"
                "- Frustration: Calming and solution-oriented.\n"
                "- Research (e.g., Browser context): Structured and insightful.\n"
                "- Casual chat: Conversational.\n"
                "Format cleanly with markdown. Be conversational yet professional."
            )

        else:
            system = (
                "You are ActifyXAI, a premium AI assistant. "
                "Acknowledge the context, respond naturally, and feel collaborative and intelligent. "
                "Analyze the following content and provide a clear, concise, and helpful response. "
                "Format cleanly with markdown. Max 200 words."
            )

        prompt = f'"""\n{text}\n"""'
        model  = ModelRouter.FAST_MODEL
        # Use capable model for complex code refactoring or long research
        if action in ("refactor", "research") or len(text.split()) > 150:
            model = ModelRouter.CAPABLE_MODEL

        result = execution_layer.execute_with_system(system, prompt, model)
        return QuickResponse(result=result, model_used=model)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/health")
async def health():
    """
    Health check — does a live 1-token Groq ping to verify key validity.
    GET http://localhost:8000/api/health
    Returns: { status, groq_live, fast_model, capable_model, error? }
    """
    ping = execution_layer.health_check()
    return {
        "status": "ok",
        "groq_configured": execution_layer.client is not None,
        "groq_live": ping["ok"],
        "fast_model": ModelRouter.FAST_MODEL,
        "capable_model": ModelRouter.CAPABLE_MODEL,
        **({"error": ping["error"], "detail": ping.get("detail")} if not ping["ok"] else {}),
    }
