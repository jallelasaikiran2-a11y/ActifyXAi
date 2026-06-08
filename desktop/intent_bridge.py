"""
intent_bridge.py — Desktop Intent & Action Engine for ActifyXAI
Mirrors the browser content.js scoring logic in pure Python.
No DOM, no browser APIs — works on any selected text.
"""
import re


# ================================================================
# INTENT SCORING ENGINE  (mirrors content.js scoreIntent())
# ================================================================

def score_intent(raw: str) -> dict:
    t = raw.lower().strip()
    wc = len(t.split())
    nlc = raw.count("\n")

    scores = {
        "transact_food": 0,
        "transact_shop": 0,
        "navigate":      0,
        "fix":           0,
        "transform":     0,
        "writing":       0,
        "search":        0,
        "informational": 0,
        "explore":       1,   # fallback baseline
    }

    # ── PROSE DETECTION ─────────────────────────────────────────
    IS_LONG_PROSE  = wc > 40
    HAS_SENTENCES  = len(re.findall(r"[.!?]\s+[A-Z]", raw)) >= 2
    IS_ARTICLE     = IS_LONG_PROSE and HAS_SENTENCES
    SHOP_MULTIPLIER = 0 if IS_ARTICLE else 1

    # ── FOOD ────────────────────────────────────────────────────
    if re.search(r"\b(biryani|pizza|burger|sushi|pasta|noodle|ramen|taco|kebab|thali|dosa|idli|paratha|momos|waffle|pancake|gelato|fries|mutton|paneer|dal|sandwich|boba|shawarma|pho|nachos|burrito|lasagna|risotto|naan|chapati|samosa|pakora|halwa|jalebi)\b", t):
        scores["transact_food"] += 5
    if re.search(r"\b(chicken|steak|salad|coffee|tea|juice|cake|dessert|snack|meal|dish|food|breakfast|lunch|dinner|drink|soup|curry|rice|bread|egg|fish|prawn|beef|pork|lamb|tofu|vegan)\b", t):
        scores["transact_food"] += (0 if IS_ARTICLE else 2)
    if re.search(r"\b(swiggy|zomato|ubereats|grubhub|doordash)\b", t):
        scores["transact_food"] += 4
    if re.search(r"\b(restaurant|cafe|eatery|recipe|ingredient|food\s+delivery)\b", t):
        scores["transact_food"] += (0 if IS_ARTICLE else 3)

    # ── SHOP ────────────────────────────────────────────────────
    TECH_BRANDS = bool(re.search(r"\b(iphone|samsung|galaxy|pixel|oneplus|realme|redmi|xiaomi|oppo|macbook|ipad|airpods|laptop|tablet|headphones|earbuds|charger|keyboard|mouse|monitor|gpu|cpu|ssd|router|playstation|xbox|nintendo|dyson|gopro|canon\s+camera|nikon|sony\s+camera)\b", t))
    if TECH_BRANDS:
        scores["transact_shop"] += 5 * SHOP_MULTIPLIER
    if re.search(r"\b(\d{2,4}\s?gb|\d+\s?tb|\d+\s?mp|\d+\s?hz|pro\s+max|ultra\s+edition)\b", t):
        scores["transact_shop"] += 3 * SHOP_MULTIPLIER
    if re.search(r"\b(buy\s+now|purchase\s+now|add\s+to\s+cart|checkout)\b", t):
        scores["transact_shop"] += 4 * SHOP_MULTIPLIER
    if re.search(r"\b(best\s+price|lowest\s+price|free\s+shipping|in\s+stock|out\s+of\s+stock)\b", t):
        scores["transact_shop"] += 3 * SHOP_MULTIPLIER

    # ── NAVIGATE ────────────────────────────────────────────────
    if re.search(r"\b(near\s?(by|me|you)?|directions?\s+to|navigate\s+to|take\s+me\s+to|how\s+to\s+reach|open\s+in\s+maps|get\s+directions)\b", t):
        scores["navigate"] += 5
    if re.search(r"\b(branch|outlet|clinic|hospital|park|stadium|airport|station|hotel|mall|market|school|college|office|gym|temple|church|mosque|atm|bank|salon|spa|pharmacy|museum|zoo)\b", t):
        scores["navigate"] += (1 if IS_ARTICLE else 3)
    if re.search(r"\b(map|gps|route|address|location|street|city\s+of|town\s+of|locality|pincode)\b", t):
        scores["navigate"] += (0 if IS_ARTICLE else 2)

    # ── FIX / CODE ───────────────────────────────────────────────
    if re.search(r"\b(def\s+\w+\s*\(|function\s*\w*\s*\(|class\s+\w+\s*[:{(]|import\s+[\w{*]|from\s+\w[\w.]+\s+import|#include\s*<|public\s+\w+\s+\w+\s*\()", raw):
        scores["fix"] += 6
    if re.search(r"\b\w+\s*=\s*[\d.'\"[{\(]", raw):
        scores["fix"] += 3
    if re.search(r"(===|!==|&&|\|\||=>|\+\+|--|::|<<|>>|\?\?)", raw):
        scores["fix"] += 2
    if re.search(r"\b(const|let|var|return|async|await|yield|lambda|elif|printf|cout|nil|undefined|boolean|void\s+\w+|int\s+\w+|float\s+\w+|ArrayList|HashMap|struct\s+\w+|enum\s+\w+)\b", t):
        scores["fix"] += 3
    if re.search(r"[{}\[\]]{2,}", raw):
        scores["fix"] += 2
    if re.search(r"\b(error:|exception:|traceback|stacktrace|undefined\s+is\s+not|null\s+pointer|segfault|not\s+working|syntax\s+error|type\s+error|reference\s+error|index\s+error|uncaught|4\d\d\s+error|5\d\d\s+error)\b", t):
        scores["fix"] += 5
    if re.search(r"\b(fix\s+(this|my|the)|debug\s+(this|my)|resolve\s+(this|the)|what.?s\s+wrong\s+with|review\s+my\s+code)\b", t):
        scores["fix"] += 5
    if nlc >= 1 and re.search(r"\b\w+\s*=\s*[\d.'\"[{\(]|\b(const|let|var|return|async|await|elif|printf)\b", t):
        scores["fix"] += 3

    # ── TRANSFORM ───────────────────────────────────────────────
    if re.search(r"\b(rewrite|rephrase|paraphrase|summarize|shorten|expand|translate|proofread|improve\s+(this|my)|polish|simplify|formali[sz]e|make\s+it\s+(formal|casual|shorter|longer|concise)|condense|edit\s+(this|my)|revise|tldr|tl;dr|bullet\s+points|key\s+points)\b", t):
        scores["transform"] += 6
        if IS_ARTICLE:
            scores["transform"] += 3

    # ── WRITING ─────────────────────────────────────────────────
    if re.search(r"\b(subject:|dear\s+\w|sincerely|regards|hi\s+team|hello\s+\w|attached\s+(please|herewith)|please\s+find|as\s+per|followup|follow.?up|revert\s+back|kindly|best\s+regards|warm\s+regards|yours\s+(sincerely|truly|faithfully))\b", t):
        scores["writing"] += 6
    if re.search(r"\b(application\s+for|cover\s+letter|job\s+title|position\s+of|years\s+of\s+experience|i\s+am\s+interested|enclosed\s+(is|are)|resume|curriculum\s+vitae|linkedin|portfolio|salary|notice\s+period)\b", t):
        scores["writing"] += 5

    # ── INFORMATIONAL ───────────────────────────────────────────
    if re.search(r"\b(artificial\s+intelligence|machine\s+learning|deep\s+learning|neural\s+network|large\s+language\s+model|llm|gpt|transformer|algorithm|natural\s+language|computer\s+science|data\s+science|blockchain|quantum|robotics|automation|technology|science|history|biology|physics|chemistry|economics|psychology|philosophy|sociology|research|study|theory|concept|overview|introduction)\b", t):
        scores["informational"] += (4 if IS_ARTICLE else 2)
    if IS_ARTICLE and not re.search(r"\b(rewrite|rephrase|paraphrase|summarize|shorten|expand|translate|proofread)\b", t):
        scores["informational"] += 5
    if re.search(r"\b(according\s+to|published|studies\s+show|researchers|experts\s+say|in\s+\d{4}|was\s+(founded|developed|invented|discovered)|is\s+defined\s+as|refers\s+to)\b", t):
        scores["informational"] += 3

    # ── SEARCH ──────────────────────────────────────────────────
    if re.search(r"\b(what\s+(is|are|was|were)|how\s+(to|do|does|can|should|much|many)|why\s+(is|are|does|do|did)|who\s+(is|are|was)|when\s+(is|was|did)|where\s+(is|are)|explain\s+(what|how|why|the)|define\s+\w+|meaning\s+of|difference\s+between|vs\.?\s+\w+|tell\s+me\s+about)\b", t):
        scores["search"] += 4
    if t.endswith("?"):
        scores["search"] += 3

    return scores


def detect_intent(raw: str) -> str:
    scores = score_intent(raw)

    winner = "explore"
    top_score = 1
    for intent, score in scores.items():
        if score > top_score:
            top_score = score
            winner = intent

    # Tie-break food vs shop
    if abs(scores["transact_food"] - scores["transact_shop"]) <= 1 and scores["transact_food"] > 2:
        winner = "transact_food"  # desktop default — no URL context

    return winner


# ================================================================
# ACTION SET MAP  (mirrors content.js getActions())
# ================================================================

ACTION_MAP = {
    "transact_food": [
        {"label": "🍽  Order Food",    "type": "selector", "category": "food_order"},
        {"label": "📍  Nearby",        "type": "selector", "category": "maps"},
        {"label": "▶  Watch Recipe",   "type": "selector", "category": "video_tutorial"},
    ],
    "transact_shop": [
        {"label": "💰  Compare Price", "type": "selector", "category": "price_compare"},
        {"label": "🛒  Buy Online",    "type": "selector", "category": "shopping"},
        {"label": "▶  Watch Reviews",  "type": "selector", "category": "video_review"},
    ],
    "navigate": [
        {"label": "📍  Open Maps",     "type": "selector", "category": "maps"},
        {"label": "🔍  Search Area",   "type": "selector", "category": "search"},
    ],
    "fix": [
        {"label": "🛠  Fix Error",     "type": "DIRECT_ACTION", "action": "fix"},
        {"label": "🧠  Explain Cause", "type": "DIRECT_ACTION", "action": "explain"},
        {"label": "▶  Watch Tutorial", "type": "selector",      "category": "video_tutorial"},
    ],
    "transform": [
        {"label": "✍  Rewrite",        "type": "DIRECT_ACTION", "action": "rewrite"},
        {"label": "✨  Improve Tone",  "type": "DIRECT_ACTION", "action": "improve"},
        {"label": "📏  Shorten",       "type": "DIRECT_ACTION", "action": "shorten"},
    ],
    "writing": [
        {"label": "✏  Rewrite Pro",    "type": "DIRECT_ACTION", "action": "rewrite"},
        {"label": "✨  Improve Tone",  "type": "DIRECT_ACTION", "action": "improve"},
        {"label": "📏  Shorten",       "type": "DIRECT_ACTION", "action": "shorten"},
    ],
    "informational": [
        {"label": "🧠  Explain",       "type": "DIRECT_ACTION", "action": "explain"},
        {"label": "📝  Summarize",     "type": "DIRECT_ACTION", "action": "summarize"},
        {"label": "▶  Watch Video",    "type": "selector",      "category": "video_tutorial"},
    ],
    "search": [
        {"label": "🧠  Explain",       "type": "DIRECT_ACTION", "action": "explain"},
        {"label": "🔍  Search",        "type": "selector",      "category": "search"},
        {"label": "▶  Watch",          "type": "selector",      "category": "video_tutorial"},
    ],
    "explore": [
        {"label": "🧠  Explain",       "type": "DIRECT_ACTION", "action": "explain"},
        {"label": "📝  Summarize",     "type": "DIRECT_ACTION", "action": "summarize"},
        {"label": "🔍  Search",        "type": "selector",      "category": "search"},
    ],
}


def get_actions(intent: str) -> list:
    return ACTION_MAP.get(intent, ACTION_MAP["explore"])


# ================================================================
# SEMANTIC PROGRAMMING CONCEPT EXTRACTOR
# Converts raw code/error text into human-readable YouTube queries.
# Fast, deterministic — no LLM needed.
# ================================================================

_ALGO_MAP = [
    # Algorithms & data structures
    (r"\btwo\s*sum\b|nums\s*=\s*\[.*\].*target", "Two Sum"),
    (r"\bfibonacci\b", "Fibonacci"),
    (r"\bbinary\s*search\b", "Binary Search"),
    (r"\bbubble\s*sort\b", "Bubble Sort"),
    (r"\bmerge\s*sort\b", "Merge Sort"),
    (r"\bquick\s*sort\b", "Quick Sort"),
    (r"\bdynamic\s*programming\b|\bdp\[\b", "Dynamic Programming"),
    (r"\bbfs\b|\bbreadth.?first\b", "Breadth First Search"),
    (r"\bdfs\b|\bdepth.?first\b", "Depth First Search"),
    (r"\blinked\s*list\b|ListNode", "Linked List"),
    (r"\bbinary\s*tree\b|TreeNode", "Binary Tree"),
    (r"\bhash\s*map\b|\bdict\b.*\bfor\b.*\bin\b", "HashMap"),
    (r"\brecursion\b|\brecursive\b", "Recursion"),
    (r"\bstack\b.*\bpop\b|\bpush\(\)", "Stack"),
    (r"\bqueue\b.*\bdequeue\b|from\s+collections\s+import\s+deque", "Queue"),
    # React / JS
    (r"\buseEffect\b", "useEffect"),
    (r"\buseState\b", "useState"),
    (r"\buseCallback\b", "useCallback"),
    (r"\buseMemo\b", "useMemo"),
    (r"\bpromise\b.*\.then\b|async.*await", "async await"),
    (r"\bcallback\s+hell\b", "callback hell"),
    (r"\bwebpack\b", "Webpack"),
    (r"\bvite\.config\b", "Vite config"),
    # Python-specific patterns
    (r"\bpandas\b|import\s+pandas", "Pandas"),
    (r"\bnumpy\b|import\s+numpy", "NumPy"),
    (r"\bmatplotlib\b", "Matplotlib"),
    (r"\bdjango\b", "Django"),
    (r"\bflask\b", "Flask"),
    (r"\bfastapi\b", "FastAPI"),
    (r"\bsqlalchemy\b", "SQLAlchemy"),
    (r"\bdecorator\b|@\w+\s*\n\s*def ", "Python decorator"),
    (r"\bgenerator\b|yield\b", "Python generator"),
    (r"\blist\s+comprehension\b|\[.*for.*in.*\]", "list comprehension"),
    # Common error semantics
    (r"str.*object.*not.*callable|str.*is.*not.*callable", "str object not callable"),
    (r"nonetype.*has\s+no\s+attribute|NoneType.*AttributeError", "NoneType AttributeError"),
    (r"index.*out.*of.*range|IndexError", "index out of range"),
    (r"key.*error|KeyError", "KeyError"),
    (r"name.*not\s+defined|NameError", "NameError"),
    (r"import.*error|ImportError|ModuleNotFoundError", "ImportError ModuleNotFoundError"),
    (r"missing.*parenthes|print.*hello.*syntaxerror", "print syntax fix"),
    (r"indentation.*error|IndentationError|unexpected.*indent", "indentation error"),
    (r"type.*error|TypeError", "TypeError"),
    (r"attribute.*error|AttributeError", "AttributeError"),
    (r"value.*error|ValueError", "ValueError"),
    (r"runtime.*error|RuntimeError", "RuntimeError"),
    (r"segmentation\s+fault|segfault", "segmentation fault"),
    (r"null\s+pointer|NullPointerException", "null pointer exception"),
    (r"dependency.*(warn|array|issue)|useEffect.*dep", "useEffect dependency"),
    (r"cors.*error|cross.origin", "CORS error"),
    (r"401|unauthorized", "401 unauthorized"),
    (r"404|not\s+found", "404 not found"),
    (r"500|internal\s+server\s+error", "500 internal server error"),
]


def _extract_programming_concept(text: str, lang: str) -> str:
    """
    Returns a clean concept label if the text matches a known programming pattern.
    Returns empty string if no match — caller falls back to error extraction.
    """
    t = text.lower()
    for pattern, label in _ALGO_MAP:
        if re.search(pattern, t, re.IGNORECASE):
            return label
    return ""


def build_smart_query(text: str, category: str, intent: str) -> str:
    """
    Advanced semantic query builder for ActifyXAI.
    Cleans raw selections and generates intelligent YouTube/search queries.
    """

    original = text.strip()

    # ============================================================
    # STEP 1 — REMOVE URLS
    # ============================================================

    cleaned = re.sub(r"https?://[^\s]+", " ", original)

    cleaned = re.sub(
        r"\b(www\.)?[a-zA-Z0-9\-]+\.(com|org|net|io|in|co|ai|dev)\S*\b",
        " ",
        cleaned,
        flags=re.IGNORECASE
    )

    # ============================================================
    # STEP 2 — REMOVE GARBAGE WORDS
    # ============================================================

    garbage_patterns = [
        r"\bwikipedia\b",
        r"\bwiki\b",
        r"\barticle\b",
        r"\bdocumentation\b",
        r"\bexplained article\b",
        r"\breview page\b",
        r"\bwith intentional\b",
        r"\btutorial page\b",
        r"\bwatch now\b",
        r"\bread more\b",
        r"\bclick here\b",
        r"\bhomepage\b",
        r"\byoutube\b",
        r"\bgoogle\b",
    ]

    for pattern in garbage_patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    # ============================================================
    # STEP 3 — REMOVE PAGE TITLE SUFFIXES
    # ============================================================

    cleaned = re.sub(
        r"-\s*(Wikipedia|YouTube|Google|Amazon|Flipkart).*",
        " ",
        cleaned,
        flags=re.IGNORECASE
    )

    # ============================================================
    # STEP 4 — CLEAN SYMBOLS
    # ============================================================

    cleaned = re.sub(r"[\[\]\(\)\{\}|<>]", " ", cleaned)
    cleaned = re.sub(r"[^\w\s+#.-]", " ", cleaned)

    # ============================================================
    # STEP 5 — NORMALIZE SPACES
    # ============================================================

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # ============================================================
    # STEP 6 — DETECT LANGUAGE
    # ============================================================

    detected_lang = ""

    lang_patterns = {
        "Python": r"\bpython\b",
        "JavaScript": r"\bjavascript\b|\bjs\b",
        "React": r"\breact\b",
        "FastAPI": r"\bfastapi\b",
        "Django": r"\bdjango\b",
        "Flask": r"\bflask\b",
        "Java": r"\bjava\b",
        "C++": r"\bc\+\+\b",
    }

    for lang, pattern in lang_patterns.items():
        if re.search(pattern, cleaned, re.IGNORECASE):
            detected_lang = lang
            break

    # ============================================================
    # STEP 7 — SEMANTIC CONCEPT EXTRACTION
    # ============================================================

    concept = _extract_programming_concept(cleaned, detected_lang)

    # ============================================================
    # STEP 8 — ERROR EXTRACTION
    # ============================================================

    error_match = re.search(
        r"(TypeError|IndexError|KeyError|ValueError|AttributeError|NameError|SyntaxError|RuntimeError|ImportError|ModuleNotFoundError)",
        cleaned,
        re.IGNORECASE
    )

    if error_match:
        concept = error_match.group(1)

    # ============================================================
    # STEP 9 — FALLBACK SHORTENING
    # ============================================================

    if not concept:
        words = cleaned.split()

        if len(words) > 8:
            cleaned = " ".join(words[:8])

        concept = cleaned.strip()

    # ============================================================
    # STEP 10 — REMOVE DUPLICATED WORDS
    # ============================================================

    tokens = concept.split()

    deduped = []
    seen_prev = None

    for token in tokens:
        low = token.lower()

        if low != seen_prev:
            deduped.append(token)

        seen_prev = low

    concept = " ".join(deduped)

    # ============================================================
    # STEP 11 — SPECIAL PYTHON CLEANUP
    # ============================================================

    concept = re.sub(
        r"\b(Python)\s+\1\b",
        r"\1",
        concept,
        flags=re.IGNORECASE
    )

    # ============================================================
    # STEP 12 — BUILD CONTEXTUAL QUERY
    # ============================================================

    final_query = concept

    if category == "video_tutorial":

        lower = concept.lower()

        # ERROR / DEBUGGING
        if re.search(
            r"(error|exception|bug|debug|typeerror|indexerror|syntaxerror|attributeerror)",
            lower
        ):
            final_query = f"{concept} fix"

        # FOOD
        elif re.search(
            r"(biryani|pizza|burger|pasta|recipe|curry|dosa|idli)",
            lower
        ):
            final_query = f"{concept} recipe"

        # PROGRAMMING
        elif detected_lang or intent == "fix":
            final_query = f"{concept} tutorial"

        # GENERAL EDUCATIONAL
        else:
            final_query = f"{concept} explained"

    elif category == "video_review":
        final_query = f"{concept} review"

    elif category == "price_compare":
        final_query = f"{concept} price comparison"

    # ============================================================
    # STEP 13 — FINAL NORMALIZATION
    # ============================================================

    final_query = re.sub(r"\s+", " ", final_query).strip()

    return final_query

# ================================================================
# APP REGISTRY  (external tool URL map)
# ================================================================

APPS = {
    "food_order": [
        {"name": "Swiggy",    "icon": "🧡", "url": "https://www.swiggy.com/search?query="},
        {"name": "Zomato",    "icon": "🔴", "url": "https://www.zomato.com/search?q="},
        {"name": "Uber Eats", "icon": "🟢", "url": "https://www.ubereats.com/search?q="},
    ],
    "shopping": [
        {"name": "Amazon",   "icon": "📦", "url": "https://www.amazon.in/s?k="},
        {"name": "Flipkart", "icon": "🛒", "url": "https://www.flipkart.com/search?q="},
        {"name": "Meesho",   "icon": "🛍", "url": "https://www.meesho.com/search?q="},
    ],
    "price_compare": [
        {"name": "Google Shopping", "icon": "🛒", "url": "https://www.google.com/search?tbm=shop&q="},
        {"name": "Amazon",          "icon": "📦", "url": "https://www.amazon.in/s?k="},
        {"name": "Flipkart",        "icon": "🔵", "url": "https://www.flipkart.com/search?q="},
    ],
    "video_tutorial": [
        {"name": "YouTube", "icon": "▶", "url": "https://www.youtube.com/results?search_query="},
        {"name": "Google",  "icon": "🔵", "url": "https://www.google.com/search?q="},
    ],
    "video_review": [
        {"name": "YouTube", "icon": "▶", "url": "https://www.youtube.com/results?search_query="},
        {"name": "Google",  "icon": "🔵", "url": "https://www.google.com/search?q="},
    ],
    "maps": [
        {"name": "Google Maps", "icon": "🗺", "url": "https://www.google.com/maps/search/?api=1&query="},
        {"name": "Waze",        "icon": "🚗", "url": "https://waze.com/ul?q="},
    ],
    "search": [
        {"name": "Google", "icon": "🔵", "url": "https://www.google.com/search?q="},
        {"name": "Bing",   "icon": "⬜", "url": "https://www.bing.com/search?q="},
    ],
}

LLM_URLS = {
    "chatgpt":    "https://chatgpt.com/",
    "claude":     "https://claude.ai/new",
    "gemini":     "https://gemini.google.com/app",
    "perplexity": "https://www.perplexity.ai/",
    "deepseek":   "https://chat.deepseek.com/",
}
