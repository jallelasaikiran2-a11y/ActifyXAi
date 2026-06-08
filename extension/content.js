// ================================================================
// ActifyXAI — content.js  v7.0
// Works on ALL websites including ChatGPT, Claude, etc.
// AI actions → LLM Selector panel (never auto-open)
// Fixed: LLM injection via storage relay, no auto-select,
//        popup on AI tools via selectionchange+copy events
// ================================================================

'use strict';

// Guard: don't double-inject if already loaded
if (window.__actifyXAI_loaded) {
  // already running
} else {
  window.__actifyXAI_loaded = true;

  let popupEl = null;
  let selectorEl = null;
  let iaPanelEl = null;   // Instant Answer panel
  let currentText = '';
  let currentIntent = '';
  let currentAction = 'explain';
  let isClickingBtn = false;  // true while mouse is down inside UI
  let uiActive = false;       // true while IA panel is open (freezes text/close)
  let lastMouseX = 0;
  let lastMouseY = 0;
  let selChangedTimer = null;

  // ================================================================
  // DRAG SUPPORT — attach to any fixed-position element
  // ================================================================
  function makeDraggable(el, handle) {
    let ox = 0, oy = 0, startX = 0, startY = 0, dragging = false;
    const dragTarget = handle || el;

    const onDown = (e) => {
      // Only drag from the element itself, not interactive children
      if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT' ||
          e.target.tagName === 'A' || e.target.closest('button, input, a')) return;
      dragging = true;
      startX = e.clientX;
      startY = e.clientY;
      ox = parseInt(el.style.left, 10) || 0;
      oy = parseInt(el.style.top,  10) || 0;
      el.style.transition = 'none';
      e.stopPropagation();
      // prevent text selection while dragging
      document.body.style.userSelect = 'none';
    };

    const onMove = (e) => {
      if (!dragging) return;
      const nx = ox + (e.clientX - startX);
      const ny = oy + (e.clientY - startY);
      const vw = window.innerWidth, vh = window.innerHeight;
      const pw = el.offsetWidth, ph = el.offsetHeight;
      el.style.left = `${Math.max(0, Math.min(nx, vw - pw))}px`;
      el.style.top  = `${Math.max(0, Math.min(ny, vh - ph))}px`;
    };

    const onUp = () => {
      if (!dragging) return;
      dragging = false;
      el.style.transition = '';
      document.body.style.userSelect = '';
    };

    dragTarget.addEventListener('mousedown', onDown);
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    // cleanup fn returned so caller can remove if needed
    return () => {
      dragTarget.removeEventListener('mousedown', onDown);
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
  }

  // ================================================================
  // EVENTS
  // ================================================================

  // Track mouse position for selectionchange-based popups
  document.addEventListener('mousemove', (e) => {
    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
  });

  // Primary: mouseup — show popup on text selection
  document.addEventListener('mouseup', (e) => {
    // If mouse released inside our UI elements, never close/reopen
    const inUI = (popupEl && popupEl.contains(e.target)) ||
                 (selectorEl && selectorEl.contains(e.target)) ||
                 (iaPanelEl && iaPanelEl.contains(e.target));
    if (inUI) return;

    const isClick = Math.abs(e.clientX - clickStartX) < 5 && Math.abs(e.clientY - clickStartY) < 5;

    setTimeout(() => {
      const sel = window.getSelection();
      const text = sel ? sel.toString().trim() : '';

      // If IA panel is open but user selects text inside it, ignore
      if (iaPanelEl && iaPanelEl.contains(sel.anchorNode)) return;

      if (text.length > 2) {
        if (isClick && text === currentText) return; // do not reopen on outside click
        
        currentText = text;
        destroySelector(); // only destroys toolbar & selector
        renderPopup(e.clientX, e.clientY, text);
      } else {
        // user clicked outside and cleared selection → close temporary toolbar only
        if (popupEl) { popupEl.style.display = 'none'; }
        if (selectorEl) { selectorEl.remove(); selectorEl = null; }
        // We do NOT call destroyAll() here so the IA panel stays open
      }
    }, 30);
  });

  // selectionchange — keyboard selection / AI-tool selections
  document.addEventListener('selectionchange', () => {
    if (isClickingBtn) return; // never steal focus from active UI clicks
    clearTimeout(selChangedTimer);
    selChangedTimer = setTimeout(() => {
      const sel = window.getSelection();
      // Ignore selections inside the persistent IA panel
      if (iaPanelEl && iaPanelEl.contains(sel.anchorNode)) return;

      const text = sel ? sel.toString().trim() : '';
      if (text.length > 2) {
        if (text !== currentText || !popupEl || popupEl.style.display === 'none') {
          currentText = text;
          destroySelector();
          renderPopup(lastMouseX, lastMouseY, text);
        }
      }
    }, 300);
  });

  // copy event — Ctrl+C backup
  document.addEventListener('copy', () => {
    if (uiActive) return;
    const sel = window.getSelection();
    const text = sel ? sel.toString().trim() : '';
    if (text.length > 2) {
      currentText = text;
      destroySelector();
      renderPopup(lastMouseX, lastMouseY, text);
    }
  });

  let clickStartX = 0;
  let clickStartY = 0;

  // mousedown — close temporary UI when clicking genuinely outside
  document.addEventListener('mousedown', (e) => {
    clickStartX = e.clientX;
    clickStartY = e.clientY;

    const inPopup    = popupEl    && popupEl.contains(e.target);
    const inSelector = selectorEl && selectorEl.contains(e.target);
    const inIAPanel  = iaPanelEl  && iaPanelEl.contains(e.target);

    if (inPopup || inSelector || inIAPanel) {
      isClickingBtn = true;
      window.addEventListener('mouseup', () => {
        isClickingBtn = false;
      }, { once: true });
      return;
    }
    
    // Clicking outside completely: close temporary toolbar & selector
    if (popupEl)    { popupEl.style.display = 'none'; }
    if (selectorEl) { selectorEl.remove(); selectorEl = null; }
  });

  // scroll — hide temporary toolbar if scrolling away
  document.addEventListener('scroll', () => {
    if (popupEl && popupEl.style.display !== 'none') {
      popupEl.style.display = 'none';
      if (selectorEl) { selectorEl.remove(); selectorEl = null; }
    }
  }, { passive: true });

  document.addEventListener('touchstart', (e) => {
    const inPopup    = popupEl    && popupEl.contains(e.target);
    const inSelector = selectorEl && selectorEl.contains(e.target);
    const inIAPanel  = iaPanelEl  && iaPanelEl.contains(e.target);
    if (!inPopup && !inSelector && !inIAPanel) {
      if (!uiActive) destroyAll();
    }
  }, { passive: true });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') destroyAll();
  });

  // ================================================================
  // SOCIAL MEDIA RESILIENCE LAYER
  // MutationObserver + event delegation for dynamic React/SPA pages.
  // Ensures selection capture works on: LinkedIn, Twitter/X,
  // WhatsApp Web, Instagram, Facebook — even after DOM rebuilds.
  // ================================================================

  const SOCIAL_HOSTS = /linkedin\.com|twitter\.com|x\.com|instagram\.com|facebook\.com|wa\.me|web\.whatsapp\.com/i;

  if (SOCIAL_HOSTS.test(window.location.hostname)) {

    // Delegated mouseup on document — covers dynamically injected nodes
    // (React re-renders remove and re-add event targets, breaking static bindings)
    document.addEventListener('mouseup', (e) => {
      // Already handled by primary mouseup above — this is a safety net for
      // cases where React's synthetic event system swallowed the original.
      // Only fire if primary handler didn't catch a selection.
      setTimeout(() => {
        const sel = window.getSelection();
        const text = sel ? sel.toString().trim() : '';
        if (text.length > 2 && text !== currentText) {
          // Primary handler missed it — rescue the selection
          if (!popupEl || popupEl.style.display === 'none') {
            currentText = text;
            destroySelector();
            renderPopup(e.clientX, e.clientY, text);
          }
        }
      }, 80);  // slightly longer delay — waits for React state settle
    }, { capture: true });  // capture phase catches events before React does

    // MutationObserver: re-attach delegated listeners when React re-renders
    // major subtrees (e.g. feed updates, story transitions, chat loads).
    let _reattachTimer = null;
    const _socialObserver = new MutationObserver((mutations) => {
      // Only act on significant DOM changes (node additions, not attr tweaks)
      const significant = mutations.some(m => m.addedNodes.length > 2);
      if (!significant) return;

      clearTimeout(_reattachTimer);
      _reattachTimer = setTimeout(() => {
        // Re-read selection in case it was lost during re-render
        if (uiActive) return;  // don't interfere with open IA panel
        const sel = window.getSelection();
        const text = sel ? sel.toString().trim() : '';
        if (text.length > 2 && text !== currentText) {
          currentText = text;
          destroySelector();
          renderPopup(lastMouseX, lastMouseY, text);
        }
      }, 350);
    });

    // Observe body subtree — catches all React DOM mutations
    _socialObserver.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: false,   // ignore attribute-only changes (performance)
      characterData: false
    });

    // Touch support for mobile-style social UX (WhatsApp Web, Instagram)
    document.addEventListener('touchend', (e) => {
      if (uiActive) return;
      setTimeout(() => {
        const sel = window.getSelection();
        const text = sel ? sel.toString().trim() : '';
        if (text.length > 2 && text !== currentText) {
          const touch = e.changedTouches[0];
          currentText = text;
          destroySelector();
          renderPopup(touch.clientX, touch.clientY, text);
        }
      }, 120);
    }, { passive: true });

  } // end social media resilience block

  // ================================================================
  // MULTI-SIGNAL SCORING INTENT ENGINE  v6
  //
  // KEY FIX: Long prose (articles, Wikipedia, docs) gets a
  // "prose penalty" that suppresses transact_shop signals from
  // brand/company names mentioned IN articles (Amazon, Google etc.)
  // ================================================================

  function scoreIntent(raw) {
    const t = raw.toLowerCase().trim();
    const wc = t.split(/\s+/).length;
    const nlc = (raw.match(/\n/g) || []).length;

    const scores = {
      transact_food:  0,
      transact_shop:  0,
      navigate:       0,
      fix:            0,
      transform:      0,
      writing:        0,  // email, professional text, messages
      search:         0,
      informational:  0,  // articles, docs, AI/tech topics
      explore:        1   // fallback baseline
    };

    // ── PROSE DETECTION (article/paragraph/document) ─────────────
    // Long text with sentence structure = article, not a product query
    const IS_LONG_PROSE = wc > 40;
    const HAS_SENTENCES = (raw.match(/[.!?]\s+[A-Z]/g) || []).length >= 2;
    const IS_ARTICLE = IS_LONG_PROSE && HAS_SENTENCES;
    // Multiplier: brand mentions in articles should NOT score shop
    const SHOP_MULTIPLIER = IS_ARTICLE ? 0 : 1;

    // ── FOOD ─────────────────────────────────────────────────────
    const FOOD_STRONG = /\b(biryani|pizza|burger|sushi|pasta|noodle|ramen|taco|kebab|thali|dosa|idli|paratha|momos|waffle|pancake|gelato|fries|mutton|paneer|dal|sandwich|boba|shawarma|pho|nachos|burrito|lasagna|risotto|naan|chapati|samosa|pakora|halwa|jalebi|gulab\s?jamun)\b/i;
    const FOOD_WEAK = /\b(chicken|steak|salad|coffee|tea|juice|cake|dessert|snack|meal|dish|food|breakfast|lunch|dinner|drink|soup|curry|rice|bread|egg|fish|prawn|beef|pork|lamb|tofu|vegan)\b/i;
    const FOOD_PLATFORM = /\b(swiggy|zomato|uber\s?eats|grubhub|deliveroo|dunzo|blinkit|zepto|doordash|foodpanda)\b/i;
    const FOOD_CONTEXT = /\b(restaurant|cafe|eatery|diner|takeaway|takeout|menu|cuisine|recipe|ingredient|delivery\s+food|food\s+delivery)\b/i;
    const ORDER_FOOD = /\b(order\s+(food|delivery)|food\s+order|deliver(y|ed)?|pick\s?up\s+food)\b/i;

    if (FOOD_STRONG.test(t)) scores.transact_food += 5;
    if (FOOD_WEAK.test(t)) scores.transact_food += (IS_ARTICLE ? 0 : 2);
    if (FOOD_PLATFORM.test(t)) scores.transact_food += 4;
    if (FOOD_CONTEXT.test(t)) scores.transact_food += (IS_ARTICLE ? 0 : 3);
    if (ORDER_FOOD.test(t)) scores.transact_food += 4;

    // ── SHOP ─────────────────────────────────────────────────────
    const TECH_BRANDS = /\b(iphone|samsung|galaxy|pixel|oneplus|realme|redmi|xiaomi|oppo|vivo|nokia|motorola|asus|lenovo|dell|hp\s+laptop|acer|macbook|ipad|airpods|apple\s+watch|laptop|tablet|headphones|earbuds|charger|keyboard|mouse|monitor|gpu|cpu|ssd|router|playstation|xbox|nintendo|dyson|gopro|canon\s+camera|nikon|sony\s+camera)\b/i;
    const TECH_SPECS = /\b(\d{2,4}\s?gb|\d+\s?tb|\d+\s?mp|\d+\s?hz|\d+\s?w|\d+\s?inch|\d+"|pro\s+max|ultra\s+edition|storage\s+\d|silver\s+color|black\s+color)\b/i;
    const SHOP_VERBS = /\b(buy\s+(this|now|online|it)|purchase\s+(this|now)|add\s+to\s+cart|place\s+order|checkout|rent\s+(this|a)|subscribe\s+to)\b/i;
    const SHOP_CONTEXT = /\b(best\s+price|lowest\s+price|price\s+in\s+india|emi\s+available|cash\s+on\s+delivery|free\s+shipping|warranty\s+included|in\s+stock|out\s+of\s+stock)\b/i;
    const SHOP_SITES = /\b(amazon\.in|flipkart\.com|myntra\.com|nykaa\.com|meesho\.com|ajio\.com|croma\.com|vijay\s?sales\.com|tata\s?cliq\.com)\b/i;
    const ORDER_PRODUCT = /\b(order\s+online|buy\s+online|order\s+at\s+amazon|available\s+on\s+amazon|sold\s+by\s+amazon|ships\s+from\s+amazon)\b/i;

    // Apply SHOP_MULTIPLIER — zero for articles
    if (TECH_BRANDS.test(t)) scores.transact_shop += 5 * SHOP_MULTIPLIER;
    if (TECH_SPECS.test(t)) scores.transact_shop += 3 * SHOP_MULTIPLIER;
    if (SHOP_VERBS.test(t)) scores.transact_shop += 4 * SHOP_MULTIPLIER;
    if (SHOP_CONTEXT.test(t)) scores.transact_shop += 3 * SHOP_MULTIPLIER;
    if (SHOP_SITES.test(t)) scores.transact_shop += 5 * SHOP_MULTIPLIER;
    if (ORDER_PRODUCT.test(t)) scores.transact_shop += 4 * SHOP_MULTIPLIER;

    // Disambiguate: tech brand + no article context → suppress food
    if (TECH_BRANDS.test(t) && scores.transact_shop > 2) {
      scores.transact_food = Math.min(scores.transact_food, 1);
    }

    // ── NAVIGATE ─────────────────────────────────────────────────
    const NAV_STRONG = /\b(near\s?(by|me|you)?|directions?\s+to|navigate\s+to|take\s+me\s+to|how\s+(do\s+i\s+get|to\s+reach|far\s+(is|from))|open\s+in\s+maps|get\s+directions)\b/i;
    const NAV_PLACE = /\b(branch|outlet|clinic|hospital|park|stadium|airport|station|hotel|mall|market|school|college|office|gym|temple|church|mosque|atm|bank|salon|spa|pharmacy|museum|zoo)\b/i;
    const GEO_WORDS = /\b(map|gps|route|address|location|street|avenue|road\s+to|city\s+of|town\s+of|locality|pincode|zip\s+code|coordinates)\b/i;
    const FIND_NEAR = /\bfind\s+.{1,30}\s+(near|in|at|around)\b/i;

    if (NAV_STRONG.test(t)) scores.navigate += 5;
    if (NAV_PLACE.test(t)) scores.navigate += (IS_ARTICLE ? 1 : 3);
    if (GEO_WORDS.test(t)) scores.navigate += (IS_ARTICLE ? 0 : 2);
    if (FIND_NEAR.test(t)) scores.navigate += 4;

    // ── FIX / CODE ───────────────────────────────────────────────
    const CODE_DEF = /\b(def\s+\w+\s*\(|function\s*\w*\s*\(|class\s+\w+\s*[:{(]|import\s+[\w{*]|from\s+\w[\w.]+\s+import|#include\s*<|public\s+\w+\s+\w+\s*\()/m;
    const CODE_ASSIGN = /\b\w+\s*=\s*[\d.'"[\]{(]/m;
    const CODE_OPS = /(===|!==|&&|\|\||=>|\+\+|--|::|<<|>>|\?\?)/;
    const CODE_KW = /\b(const|let|var|return|async|await|yield|lambda|elif|printf|cout|nil|undefined|boolean|void\s+\w+|int\s+\w+|float\s+\w+|double\s+\w+|ArrayList|HashMap|struct\s+\w+|enum\s+\w+|interface\s+\w+)\b/;
    const CODE_BRACKETS = /[\{\}\[\]]{2,}/;
    const ERROR_MSG = /\b(error:|exception:|traceback|stacktrace|undefined\s+is\s+not|null\s+pointer|segfault|not\s+working|bug\s+in|warning:|syntax\s+error|type\s+error|reference\s+error|index\s+error|uncaught|4\d\d\s+error|5\d\d\s+error)\b/i;
    const FIX_VERBS = /\b(fix\s+(this|my|the)|debug\s+(this|my)|resolve\s+(this|the)|refactor\s+(this|my)|optimize\s+(this|my)|what'?s\s+wrong\s+with|review\s+my\s+code)\b/i;

    if (CODE_DEF.test(raw)) scores.fix += 6;
    if (CODE_ASSIGN.test(raw)) scores.fix += 3;
    if (CODE_OPS.test(raw)) scores.fix += 2;
    if (CODE_KW.test(t)) scores.fix += 3;
    if (CODE_BRACKETS.test(raw)) scores.fix += 2;
    if (ERROR_MSG.test(t)) scores.fix += 5;
    if (FIX_VERBS.test(t)) scores.fix += 5;
    // Multi-line code structure
    if (nlc >= 1 && (CODE_ASSIGN.test(raw) || CODE_KW.test(t))) scores.fix += 3;

    // ── TRANSFORM ────────────────────────────────────────────────
    const TRANSFORM_V = /\b(rewrite|rephrase|paraphrase|summarize|shorten|expand|translate|proofread|improve\s+(this|my)|polish|simplify|formali[sz]e|make\s+it\s+(formal|casual|shorter|longer|concise)|condense|edit\s+(this|my)|revise|tldr|tl;dr|bullet\s+points|key\s+points)\b/i;

    if (TRANSFORM_V.test(t)) scores.transform += 6;
    // Long prose with explicit transform verb → transform wins
    if (IS_ARTICLE && TRANSFORM_V.test(t)) scores.transform += 3;

    // ── WRITING (email, professional messages, formal docs) ───────────
    const EMAIL_SIGNALS = /\b(subject:|dear\s+\w|sincerely|regards|hi\s+team|hello\s+\w|attached\s+(please|herewith)|please\s+find|as\s+per|followup|follow.?up|revert\s+back|kindly|please\s+(let\s+me\s+know|confirm|review|find|note)|i\s+am\s+writing|hope\s+(this|you)|looking\s+forward|best\s+regards|warm\s+regards|yours\s+(sincerely|truly|faithfully))\b/i;
    const PROFESSIONAL = /\b(application\s+for|cover\s+letter|job\s+title|position\s+of|years\s+of\s+experience|i\s+am\s+interested|i\s+would\s+like\s+to|enclosed\s+(is|are)|resume|curriculum\s+vitae|linkedin|portfolio|references\s+available|salary\s+(expectation|negotiable)|notice\s+period|immediate\s+joiner)\b/i;
    const MSG_PATTERNS = /\b(send\s+me|let\s+me\s+know|get\s+back|ping\s+me|asap|fyi|btw|eod|cob|please\s+send|thanks\s+for|thank\s+you\s+for|reaching\s+out|heads.?up)\b/i;

    if (EMAIL_SIGNALS.test(t)) scores.writing += 6;
    if (PROFESSIONAL.test(t))  scores.writing += 5;
    if (MSG_PATTERNS.test(t))  scores.writing += (IS_ARTICLE ? 0 : 3);
    // Short casual text that's clearly a message
    if (!IS_ARTICLE && wc < 30 && MSG_PATTERNS.test(t)) scores.writing += 2;

    // ── INFORMATIONAL (articles, docs, AI/tech/science content) ──
    const INFORM_TOPIC = /\b(artificial\s+intelligence|machine\s+learning|deep\s+learning|neural\s+network|large\s+language\s+model|llm|gpt|transformer|algorithm|natural\s+language|computer\s+science|data\s+science|blockchain|quantum|robotics|automation|technology|science|history|biology|physics|chemistry|economics|psychology|philosophy|sociology|research|study|theory|concept|overview|introduction|explained?|guide|tutorial|documentation|framework|architecture|system\s+design|best\s+practice)\b/i;
    const INFORM_STRUCTURE = /\b(according\s+to|published|studies\s+show|researchers|experts\s+say|in\s+\d{4}|was\s+(founded|developed|invented|discovered)|is\s+defined\s+as|refers\s+to|is\s+known\s+as)\b/i;

    // Core informational signal: IS_ARTICLE without explicit transform verb
    if (IS_ARTICLE && !TRANSFORM_V.test(t)) scores.informational += 5;
    // Topic-specific boost for AI/tech/science keywords
    if (INFORM_TOPIC.test(t)) scores.informational += (IS_ARTICLE ? 4 : 2);
    // Encyclopaedic / citation-style prose
    if (INFORM_STRUCTURE.test(t)) scores.informational += 3;
    // Short but clearly conceptual ("what is X" style)
    if (!IS_ARTICLE && SEARCH_Q_CHECK(t) && INFORM_TOPIC.test(t)) scores.informational += 3;

    // ── SEARCH ───────────────────────────────────────────────────
    // Define SEARCH_Q here so INFORM check above can reference it
    function SEARCH_Q_CHECK(s) {
      return /\b(what\s+(is|are|was|were)|how\s+(to|do|does|can|should|much|many)|why\s+(is|are|does|do|did)|who\s+(is|are|was)|when\s+(is|was|did)|where\s+(is|are)|explain\s+(what|how|why|the)|define\s+\w+|meaning\s+of|difference\s+between|vs\.?\s+\w+|compared\s+to|tell\s+me\s+about|give\s+me\s+info)\b/i.test(s);
    }
    const ENDS_Q = t.endsWith('?');

    if (SEARCH_Q_CHECK(t)) scores.search += 4;
    if (ENDS_Q) scores.search += 3;

    return scores;
  }

  function detectIntent(raw) {
    const scores = scoreIntent(raw);

    console.log('╔═ ActifyXAI v8 ══════════════════════════════════');
    console.log('║ TEXT   :', raw.substring(0, 80));
    console.log('║ SCORES :', JSON.stringify(scores));

    let winner = 'explore';
    let topScore = 1;

    for (const [intent, score] of Object.entries(scores)) {
      if (score > topScore) { topScore = score; winner = intent; }
    }

    // Tie-break: food vs shop → use page URL
    if (Math.abs(scores.transact_food - scores.transact_shop) <= 1 &&
      scores.transact_food > 2) {
      const url = window.location.href.toLowerCase();
      winner = /amazon|flipkart|myntra|croma|shop|product|phone|laptop|gadget/.test(url)
        ? 'transact_shop' : 'transact_food';
    }

    // ── PAGE CONTEXT OVERRIDES (hostname-based) ────────────────
    // Applied AFTER signal scoring — these are hard domain rules
    const hostname = window.location.hostname.replace(/^www\./, '');

    // Code/dev sites: weak intents → promote to fix
    if (/^(stackoverflow\.com|github\.com|gitlab\.com|replit\.com|codepen\.io|dev\.to|hackernoon\.com)/.test(hostname)) {
      if (winner === 'explore' || winner === 'search') winner = 'fix';
    }

    // Product/shopping sites: non-code text → promote to shop
    if (/amazon\.|flipkart\.|myntra\.|croma\.|meesho\.|ebay\./.test(hostname)) {
      if (!['fix', 'navigate'].includes(winner)) winner = 'transact_shop';
    }

    // Wikipedia / encyclopaedia: always informational
    if (/wikipedia\.org|britannica\.com/.test(hostname)) {
      if (winner !== 'fix') winner = 'informational';
    }

    // Food delivery sites: promote to food
    if (/zomato\.com|swiggy\.com|ubereats\.com|doordash\.com/.test(hostname)) {
      if (winner !== 'fix') winner = 'transact_food';
    }

    // News / tech-media sites: promote informational for long text
    if (/medium\.com|substack\.com|techcrunch\.com|theverge\.com|wired\.com|bloomberg\.com|reuters\.com|bbc\.(com|co\.uk)|cnn\.com|ndtv\.com/.test(hostname)) {
      if (winner === 'explore' || winner === 'transform') winner = 'informational';
    }

    // LinkedIn / Gmail / Outlook: professional writing
    if (/linkedin\.com|mail\.google\.com|outlook\.live|outlook\.com/.test(hostname)) {
      if (!['fix'].includes(winner)) winner = 'writing';
    }

    // YouTube: video content → informational
    if (/youtube\.com|youtu\.be/.test(hostname)) {
      if (winner === 'explore' || winner === 'search') winner = 'informational';
    }

    console.log('║ WINNER :', winner, `(score: ${topScore}) [host: ${hostname}]`);
    console.log('╚═══════════════════════════════════════════════════');
    return winner;
  }

  // ================================================================
  // ACTION SETS — pure per-intent
  // ================================================================

  function getActions(intent) {
    // Page context: suppress redundant Search button on search engines
    const hostname = window.location.hostname.replace(/^www\./, '');
    const isOnSearchEngine = /^(google\.|bing\.|duckduckgo\.|yahoo\.)/.test(hostname);
    const isOnCodeSite = /^(stackoverflow\.|github\.|gitlab\.|replit\.|codepen\.|dev\.to|hackernoon\.)/.test(hostname);
    const isOnYouTube = /^(youtube\.com|youtu\.be)/.test(hostname);

    // Execution type: DIRECT_ACTION = inline Groq, LLM_ACTION = chooser panel
    const map = {
      transact_food: [
        { label: '🍽 Order Food',    type: 'selector', category: 'food_order' },
        { label: '📍 Nearby',        type: 'selector', category: 'maps' },
        { label: '▶️ Watch Recipe',  type: 'selector', category: 'video_tutorial' }
      ],
      transact_shop: [
        { label: '💰 Compare Price', type: 'selector', category: 'price_compare' },
        { label: '🛒 Buy Online',    type: 'selector', category: 'shopping' },
        { label: '▶️ Watch Reviews', type: 'selector', category: 'video_review' }
      ],
      navigate: [
        { label: '📍 Open Maps',     type: 'selector', category: 'maps' },
        { label: '🔍 Search Area',   type: 'selector', category: 'search' }
      ],
      fix: [
        { label: '🛠 Fix Error',     type: 'DIRECT_ACTION', action: 'fix' },
        { label: '🧠 Explain Cause', type: 'DIRECT_ACTION', action: 'explain' },
        { label: '▶️ Watch Tutorial',type: 'selector',      category: 'video_tutorial' }
      ],
      transform: [
        { label: '✍️ Rewrite',       type: 'DIRECT_ACTION', action: 'rewrite' },
        { label: '✨ Improve Tone',  type: 'DIRECT_ACTION', action: 'improve' },
        { label: '📏 Shorten',       type: 'DIRECT_ACTION', action: 'shorten' }
      ],
      writing: [
        { label: '✏ Rewrite Pro',   type: 'DIRECT_ACTION', action: 'rewrite' },
        { label: '✨ Improve Tone',  type: 'DIRECT_ACTION', action: 'improve' },
        { label: '📏 Shorten',       type: 'DIRECT_ACTION', action: 'shorten' }
      ],
      informational: (
        isOnYouTube || intent === 'informational' && window.location.href.includes('youtube.com')
          ? [
              { label: '📝 Summarize Video', type: 'DIRECT_ACTION', action: 'summarize' },
              { label: '🧠 Explain Ideas',   type: 'DIRECT_ACTION', action: 'explain' },
              { label: '🔬 Research Topic',  type: 'LLM_ACTION',    action: 'research', llm: 'perplexity' }
            ]
          : [
              { label: '🧠 Explain',       type: 'DIRECT_ACTION', action: 'explain' },
              { label: '📝 Summarize',     type: 'DIRECT_ACTION', action: 'summarize' },
              { label: '▶️ Watch Video',   type: 'selector',      category: 'video_tutorial' }
            ]
      ),
      search: (
        isOnSearchEngine
          ? [
              { label: '🧠 Explain',   type: 'DIRECT_ACTION', action: 'explain' },
              { label: '📝 Summarize', type: 'DIRECT_ACTION', action: 'summarize' },
              { label: '🔬 Research',  type: 'LLM_ACTION',    action: 'research', llm: 'perplexity' }
            ]
          : [
              { label: '🧠 Explain',   type: 'DIRECT_ACTION', action: 'explain' },
              { label: '🔍 Search',    type: 'selector',      category: 'search' },
              { label: '▶️ Watch',     type: 'selector',      category: 'video_tutorial' }
            ]
      ),
      explore: (
        isOnCodeSite
          ? [
              { label: '🛠 Fix',       type: 'DIRECT_ACTION', action: 'fix' },
              { label: '🧠 Explain',   type: 'DIRECT_ACTION', action: 'explain' }
            ]
          : [
              { label: '🧠 Explain',   type: 'DIRECT_ACTION', action: 'explain' },
              { label: '💬 Ask AI',    type: 'LLM_ACTION',    action: 'explain', llm: 'chatgpt' }
            ]
      )
    };
    return map[intent] || map.explore;
  }

  // ================================================================
  // APP REGISTRY
  // ================================================================

  const APPS = {
    food_order: [
      { name: 'Swiggy', icon: '🧡', url: 'https://www.swiggy.com/search?query=', type: 'tool' },
      { name: 'Zomato', icon: '🔴', url: 'https://www.zomato.com/search?q=', type: 'tool' },
      { name: 'Uber Eats', icon: '🟢', url: 'https://www.ubereats.com/search?q=', type: 'tool' },
      { name: 'Dunzo', icon: '🟡', url: 'https://www.dunzo.com/search?q=', type: 'tool' }
    ],
    shopping: [
      { name: 'Amazon', icon: '📦', url: 'https://www.amazon.in/s?k=', type: 'tool' },
      { name: 'Flipkart', icon: '🛒', url: 'https://www.flipkart.com/search?q=', type: 'tool' },
      { name: 'Meesho', icon: '🛍', url: 'https://www.meesho.com/search?q=', type: 'tool' },
      { name: 'Croma', icon: '🟢', url: 'https://www.croma.com/searchB?q=', type: 'tool' }
    ],
    price_compare: [
      { name: 'Google Shopping', icon: '🛒', url: 'https://www.google.com/search?tbm=shop&q=', type: 'tool' },
      { name: 'Amazon', icon: '📦', url: 'https://www.amazon.in/s?k=', type: 'tool' },
      { name: 'Flipkart', icon: '🔵', url: 'https://www.flipkart.com/search?q=', type: 'tool' }
    ],
    video_review: [
      { name: 'YouTube', icon: '▶️', url: 'https://www.youtube.com/results?search_query=', type: 'tool' },
      { name: 'Google', icon: '🔵', url: 'https://www.google.com/search?q=', type: 'tool' }
    ],
    video_tutorial: [
      { name: 'YouTube', icon: '▶️', url: 'https://www.youtube.com/results?search_query=', type: 'tool' },
      { name: 'Google', icon: '🔵', url: 'https://www.google.com/search?q=', type: 'tool' }
    ],
    maps: [
      { name: 'Google Maps', icon: '🗺', url: 'https://www.google.com/maps/search/?api=1&query=', type: 'tool' },
      { name: 'Apple Maps', icon: '📍', url: 'https://maps.apple.com/?q=', type: 'tool' },
      { name: 'Waze', icon: '🚗', url: 'https://waze.com/ul?q=', type: 'tool' }
    ],
    reviews: [
      { name: 'Zomato', icon: '🔴', url: 'https://www.zomato.com/search?q=', type: 'tool' },
      { name: 'Google', icon: '🔵', url: 'https://www.google.com/search?q=', type: 'tool' },
      { name: 'TripAdvisor', icon: '🟢', url: 'https://www.tripadvisor.com/Search?q=', type: 'tool' }
    ],
    // ── LLM selector (shown when user clicks any AI action) ──────
    // IA = Instant Answer via Groq (inline, no new tab)
    ai_llm: [
      { name: '⚡ IA', icon: '🧠', llm: 'ia', type: 'ia',
        desc: 'Instant Answer' },
      { name: 'ChatGPT', icon: '🤖', llm: 'chatgpt', type: 'llm' },
      { name: 'Claude', icon: '🟠', llm: 'claude', type: 'llm' },
      { name: 'Gemini', icon: '🔷', llm: 'gemini', type: 'llm' },
      { name: 'Perplexity', icon: '🟣', llm: 'perplexity', type: 'llm' },
      { name: 'DeepSeek', icon: '🐋', llm: 'deepseek', type: 'llm' }
    ],
    search: [
      { name: 'Google', icon: '🔵', url: 'https://www.google.com/search?q=', type: 'tool' },
      { name: 'Bing', icon: '⬜', url: 'https://www.bing.com/search?q=', type: 'tool' }
    ],
    research: [
      { name: 'Perplexity', icon: '🟣', llm: 'perplexity', type: 'llm' },
      { name: 'ChatGPT', icon: '🤖', llm: 'chatgpt', type: 'llm' },
      { name: 'Wikipedia', icon: '📚', url: 'https://en.wikipedia.org/wiki/Special:Search?search=', type: 'tool' },
      { name: 'YouTube', icon: '▶️', url: 'https://www.youtube.com/results?search_query=', type: 'tool' }
    ],
    translate: [
      { name: 'Google Translate', icon: '🌐', url: 'https://translate.google.com/?text=', type: 'tool' },
      { name: 'DeepL', icon: '💙', url: 'https://www.deepl.com/translator#auto/en/', type: 'tool' }
    ]
  };

  // LLM base URLs — prompt stored in background relay, no URL params
  function getLLMBaseUrl(llm) {
    const map = {
      chatgpt:  'https://chatgpt.com/',
      claude:   'https://claude.ai/new',
      gemini:   'https://gemini.google.com/app',
      perplexity: 'https://www.perplexity.ai/',
      deepseek: 'https://chat.deepseek.com/'
    };
    return map[llm] || map.chatgpt;
  }

  // ================================================================
  // ADVANCED PROMPT BUILDER
  // Role + Context + Task + Constraints + Output Format
  // ================================================================

  function buildAdvancedPrompt(action, text) {
    const isCode = /[{}()[\];]|\bdef\b|\bfunction\b|\bconst\b|\blet\b|\bvar\b|\bimport\b|\bclass\b|=>/.test(text);

    const builders = {
      fix: () => {
        const role = isCode
          ? 'You are a senior software engineer specializing in debugging and code quality.'
          : 'You are a professional editor and language expert.';
        const ctx = isCode
          ? 'The following code or error was selected from a development environment.'
          : 'The following text contains errors that need to be corrected.';
        return `${role}

Context:
${ctx}

Task:
Identify and fix all issues in the content below. Explain what was wrong and why the fix works.

Content:
"""
${text}
"""

Constraints:
- Be precise and beginner-friendly
- Do not change logic unless it is broken
- Preserve the original language and coding style

Output format:
1. ✅ Fixed version
2. 🔍 What was wrong (brief explanation)
3. 💡 Best practice tip`;
      },

      explain: () => {
        const role = isCode
          ? 'You are a senior developer and technical educator.'
          : 'You are a knowledgeable expert who explains complex topics in plain language.';
        return `${role}

Context:
The following ${isCode ? 'code or technical snippet' : 'text or concept'} was selected by a user who wants to understand it better.

Task:
Explain this clearly so that someone with basic knowledge can fully understand it.

Content:
"""
${text}
"""

Constraints:
- Use simple, clear language
- Avoid jargon unless you define it
- Use real-world analogies or examples where helpful

Output format:
1. 📖 Plain explanation
2. 🔑 Key concepts
3. 💡 Example or analogy`;
      },

      refactor: () =>
        `You are a senior software architect focused on clean, maintainable code.

Context:
The following code was selected for refactoring.

Task:
Refactor this code to improve readability, performance, and maintainability. Do not change the core logic.

Code:
"""
${text}
"""

Constraints:
- Preserve all existing functionality
- Follow best practices for the detected language
- Use meaningful variable and function names

Output format:
1. ♻️ Refactored code
2. 📋 Changes made (bullet list)
3. ⚡ Improvement summary`,

      rewrite: () =>
        `You are a professional writer and communication expert.

Context:
The following text was selected for improvement.

Task:
Rewrite this text to be clearer, more concise, and more impactful — while preserving the original meaning.

Text:
"""
${text}
"""

Constraints:
- Match the original tone (formal or casual) unless it is clearly poor
- Do not add new information
- Aim for clarity above all

Output format:
1. ✍️ Rewritten version
2. 🔄 Alternative version (different tone)
3. 📝 Key changes made`,

      summarize: () =>
        `You are an expert analyst and clear communicator.

Context:
The following content was selected for summarization.

Task:
Summarize the key ideas from the content below in a clear, structured way.

Content:
"""
${text}
"""

Constraints:
- Capture all important points
- Remove redundancy and filler
- Keep under 150 words unless the content is very complex

Output format:
1. 🎯 One-line summary
2. 📌 Key points (3–5 bullets)
3. 💬 Main takeaway`,
    };

    const builder = builders[action];
    return builder ? builder() : `Help me understand the following:\n\n"""\n${text}\n"""`;
  }

  // ================================================================
  // CONTEXTUAL INJECTION PROMPT — for LLM_ACTION (ChatGPT/Claude/etc.)
  // Short, human-readable, editable. NOT the structured Groq prompts.
  // ================================================================

  function buildContextualInjectionPrompt(action, text) {
    let cleanedSnippet = text
      .replace(/https?:\/\/[^\s]+/gi, ' ')
      .replace(/\b(www\.)?[a-zA-Z0-9-]+\.(com|org|net|io|in|co|ai|dev)\S*\b/gi, ' ')
      .replace(/-\s*(Wikipedia|YouTube|Google|Amazon|Flipkart).*/gi, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 500);

    const snippet  = cleanedSnippet;
    const intent   = currentIntent;
    const hostname = window.location.hostname.replace(/^www\./, '');

    // ── DEBUGGING / CODE ERROR ─────────────────────────────────
    if (intent === 'fix' || action === 'fix' || action === 'refactor') {
      const isError = /error:|exception:|traceback|typeerror|nameerror|syntaxerror/i.test(snippet);
      
      if (action === 'refactor') {
        return `Can you show a cleaner and safer version of this code/error?\n\n${snippet}`;
      }
      
      if (isError) {
        if (action === 'explain') {
          return `Explain this error in a beginner-friendly way with examples and how to fix it:\n\n${snippet}`;
        }
        return `Help me fix this error and explain why it happens:\n\n${snippet}`;
      }
      
      return `Help me fix this code and explain the issue:\n\n${snippet}`;
    }

    // ── PROFESSIONAL WRITING / EMAIL ───────────────────────────
    if (intent === 'writing' || hostname.includes('linkedin') || hostname.includes('mail.google')) {
      if (action === 'improve') {
        return `Improve the tone and clarity of this message while keeping it professional:\n\n${snippet}`;
      }
      if (action === 'shorten') {
        return `Make this message shorter and more direct:\n\n${snippet}`;
      }
      return `Can you rewrite this professionally while keeping it concise and polished?\n\n${snippet}`;
    }

    // ── PRODUCT / SHOPPING ─────────────────────────────────────
    if (intent === 'transact_shop') {
      const prodName = snippet.split('\n')[0].slice(0, 60);
      if (action === 'research') {
        return `What are the major pros and cons people mention about this product?\n\n${prodName}`;
      }
      return `Compare this product with similar alternatives and explain if it's worth buying:\n\n${prodName}`;
    }

    // ── GENERAL / INFORMATIONAL ────────────────────────────────
    if (action === 'summarize') {
      return `Summarize this in a concise and beginner-friendly way:\n\n${snippet}`;
    }

    if (action === 'research') {
      return `Can you explain this topic more deeply with real-world applications and examples?\n\n${snippet}`;
    }

    if (action === 'explain' || intent === 'informational') {
      return `Can you explain this concept in simple terms and why it matters?\n\n${snippet}`;
    }

    if (action === 'rewrite' || action === 'improve' || intent === 'transform') {
      return `Can you rewrite this to be clearer and more engaging?\n\n${snippet}`;
    }

    // ── DEFAULT ────────────────────────────────────────────────
    return `Can you help me understand this better?\n\n${snippet}`;
  }

  // ================================================================
  // SMART QUERY BUILDER for external tools
  // ================================================================

  function buildSmartQuery(text, category) {
    let original = text.trim();

    // STEP 1 - REMOVE URLS
    let cleaned = original.replace(/https?:\/\/[^\s]+/gi, ' ');
    cleaned = cleaned.replace(/\b(www\.)?[a-zA-Z0-9-]+\.(com|org|net|io|in|co|ai|dev)\S*\b/gi, ' ');

    // STEP 2 - REMOVE GARBAGE WORDS
    const garbagePatterns = [
      /\bwikipedia\b/gi, /\bwiki\b/gi, /\barticle\b/gi, /\bdocumentation\b/gi,
      /\bexplained article\b/gi, /\breview page\b/gi, /\bwith intentional\b/gi,
      /\btutorial page\b/gi, /\bwatch now\b/gi, /\bread more\b/gi,
      /\bclick here\b/gi, /\bhomepage\b/gi, /\byoutube\b/gi, /\bgoogle\b/gi
    ];
    garbagePatterns.forEach(p => {
      cleaned = cleaned.replace(p, ' ');
    });

    // STEP 3 - REMOVE PAGE TITLE SUFFIXES
    cleaned = cleaned.replace(/-\s*(Wikipedia|YouTube|Google|Amazon|Flipkart).*/gi, ' ');

    // STEP 4 - CLEAN SYMBOLS
    cleaned = cleaned.replace(/[\[\]\(\)\{\}|<>]/g, ' ');
    cleaned = cleaned.replace(/[^\w\s+#.-]/g, ' ');

    // STEP 5 - NORMALIZE SPACES
    cleaned = cleaned.replace(/\s+/g, ' ').trim();

    // STEP 6 - DETECT LANGUAGE
    let detectedLang = "";
    const langPatterns = {
        "Python": /\bpython\b/i,
        "JavaScript": /\bjavascript\b|\bjs\b/i,
        "React": /\breact\b/i,
        "FastAPI": /\bfastapi\b/i,
        "Django": /\bdjango\b/i,
        "Flask": /\bflask\b/i,
        "Java": /\bjava\b/i,
        "C++": /\bc\+\+\b/i,
    };
    for (const [lang, pattern] of Object.entries(langPatterns)) {
        if (pattern.test(cleaned)) {
            detectedLang = lang;
            break;
        }
    }

    // STEP 7 - SEMANTIC CONCEPT EXTRACTION
    let concept = "";
    const algoMap = [
      [/\btwo\s*sum\b|nums\s*=\s*\[.*\].*target/i, "Two Sum"],
      [/\bfibonacci\b/i, "Fibonacci"],
      [/\bbinary\s*search\b/i, "Binary Search"],
      [/\bmerge\s*sort\b/i, "Merge Sort"],
      [/\bquick\s*sort\b/i, "Quick Sort"],
      [/\buseEffect\b/i, "useEffect"],
      [/\buseState\b/i, "useState"],
      [/\bpandas\b|import\s+pandas/i, "Pandas"]
    ];
    for (const [pattern, label] of algoMap) {
        if (pattern.test(cleaned)) {
            concept = label;
            break;
        }
    }

    // STEP 8 - ERROR EXTRACTION
    const errorMatch = cleaned.match(/(TypeError|IndexError|KeyError|ValueError|AttributeError|NameError|SyntaxError|RuntimeError|ImportError|ModuleNotFoundError)/i);
    if (errorMatch) {
        concept = errorMatch[1];
    }

    // STEP 9 - FALLBACK SHORTENING
    if (!concept) {
        const words = cleaned.split(' ');
        if (words.length > 8) {
            cleaned = words.slice(0, 8).join(' ');
        }
        concept = cleaned.trim();
    }

    // STEP 10 - REMOVE DUPLICATED WORDS
    const tokens = concept.split(' ');
    let deduped = [];
    let seenPrev = null;
    for (const token of tokens) {
        let low = token.toLowerCase();
        if (low !== seenPrev) {
            deduped.push(token);
        }
        seenPrev = low;
    }
    concept = deduped.join(' ');

    // STEP 11 - SPECIAL PYTHON CLEANUP
    concept = concept.replace(/\b(Python)\s+\1\b/gi, '$1');

    // STEP 12 - BUILD CONTEXTUAL QUERY
    let finalQuery = concept;
    
    if (category === "video_tutorial") {
        let lower = concept.toLowerCase();
        if (/(error|exception|bug|debug|typeerror|indexerror|syntaxerror|attributeerror)/i.test(lower)) {
            finalQuery = `${concept} fix`;
        } else if (/(biryani|pizza|burger|pasta|recipe|curry|dosa|idli)/i.test(lower)) {
            finalQuery = `${concept} recipe`;
        } else if (detectedLang || currentIntent === "fix") {
            finalQuery = `${concept} tutorial`;
        } else {
            finalQuery = `${concept} explained`;
        }
    } else if (category === "video_review") {
        finalQuery = `${concept} review`;
    } else if (category === "price_compare") {
        finalQuery = `${concept} price comparison`;
    } else if (category === "food_order") {
        finalQuery = concept.replace(/near me|nearby|order|delivery|restaurant/gi, '').trim();
    } else if (category === "shopping") {
        finalQuery = concept.replace(/review|buy|price/gi, '').trim();
    } else if (category === "maps") {
        finalQuery = original.replace(/\b(find|near|nearby|me|you|navigate|directions?|go\s+to|take\s+me\s+to|open\s+in\s+maps|how\s+(far|to\s+get)\s+to|get\s+to|reach|visit)\b/gi, ' ').trim();
    }

    // STEP 13 - FINAL NORMALIZATION
    finalQuery = finalQuery.replace(/\s+/g, ' ').trim();
    return finalQuery;
  }

  // ================================================================
  // PREFERENCE MEMORY
  // ================================================================

  function getPref(cat) {
    try { return localStorage.getItem(`actify_pref_${cat}`); } catch { return null; }
  }
  function savePref(cat, name) {
    try { localStorage.setItem(`actify_pref_${cat}`, name); } catch { }
  }

  // ================================================================
  // POPUP RENDER
  // ================================================================

  function renderPopup(clientX, clientY, text) {
    if (!popupEl) {
      popupEl = document.createElement('div');
      popupEl.id = 'actifyxai-popup';
      document.body.appendChild(popupEl);
    }

    popupEl.innerHTML = '';
    popupEl.style.cssText = 'display:flex;visibility:hidden;';

    currentIntent = detectIntent(text);
    const actions = getActions(currentIntent);

    // Intent badge
    const badge = document.createElement('span');
    badge.className = 'actifyxai-badge';
    badge.textContent = currentIntent
      .replace('transact_food', 'food')
      .replace('transact_shop', 'shop');
    popupEl.appendChild(badge);

    const sep = document.createElement('div');
    sep.className = 'actifyxai-divider';
    popupEl.appendChild(sep);

    actions.forEach(item => {
      const btn = document.createElement('button');
      btn.className = 'actifyxai-btn';
      btn.textContent = item.label;

      btn.addEventListener('mousedown', (e) => {
        e.stopPropagation();
        isClickingBtn = true;
      });

      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        e.preventDefault();
        const rect = btn.getBoundingClientRect(); // capture BEFORE any DOM change
        onActionClick(item, text, rect);
      });

      popupEl.appendChild(btn);
    });

    // Smart position: above cursor, clamped to viewport
    requestAnimationFrame(() => {
      const pw = popupEl.offsetWidth || 300;
      const ph = popupEl.offsetHeight || 44;
      const vw = window.innerWidth;
      const vh = window.innerHeight;

      let left = clientX - pw / 2;
      let top = clientY - ph - 14;

      if (left < 8) left = 8;
      if (left + pw > vw - 8) left = vw - pw - 8;
      if (top < 8) top = clientY + 24;
      if (top + ph > vh - 8) top = vh - ph - 8;

      popupEl.style.left = `${Math.round(left)}px`;
      popupEl.style.top = `${Math.round(top)}px`;
      popupEl.style.visibility = 'visible';
      popupEl.style.cursor = 'grab';
      makeDraggable(popupEl);
    });
  }

  // ================================================================
  // ACTION CLICK — DIRECT_ACTION → inline IA, LLM_ACTION → chooser
  // ================================================================

  function onActionClick(item, text, anchorRect) {
    isClickingBtn = false;

    // DIRECT_ACTION: bypass chooser → call Groq inline immediately
    if (item.type === 'DIRECT_ACTION') {
      currentAction = item.action;
      destroySelector();
      showIAPanel(text, item.action, anchorRect);
      return;
    }

    // LLM_ACTION: open chooser panel (Ask AI, Research, Deep Dive)
    if (item.type === 'LLM_ACTION') {
      currentAction = item.action;
      const prompt = buildContextualInjectionPrompt(item.action, text);
      // Pre-select preferred LLM if specified
      const preferredCategory = item.llm ? '_llm_' + item.llm : 'ai_llm';
      renderSelector('ai_llm', text, anchorRect, prompt);
      return;
    }

    // selector: app picker (food, maps, shopping, etc.)
    if (item.type === 'selector') {
      const apps = APPS[item.category];
      if (!apps) return;
      renderSelector(item.category, text, anchorRect, null);
    }

    // Legacy 'ai' type fallback — treat as DIRECT_ACTION
    if (item.type === 'ai') {
      currentAction = item.action;
      destroySelector();
      showIAPanel(text, item.action, anchorRect);
    }
  }

  // ================================================================
  // OPEN APP — tool URL or LLM draft (NO auto-send)
  // ================================================================

  function openApp(app, text, category, prebuiltPrompt) {
    if (app.type === 'llm') {
      // Store prompt in background service worker FIRST (storage relay),
      // then open the base URL (no URL params — avoids SPA stripping)
      const prompt = prebuiltPrompt || buildContextualInjectionPrompt('explain', text);
      const baseUrl = getLLMBaseUrl(app.llm);
      
      // Graceful fallback: ALWAYS copy to clipboard before opening the new tab
      // in case the injection script fails due to SPA structure or CSP.
      navigator.clipboard.writeText(prompt).catch(() => {});
      
      try {
        chrome.runtime.sendMessage(
          { type: 'STORE_PROMPT', llm: app.llm, prompt },
          () => { window.open(baseUrl, '_blank'); }
        );
      } catch (e) {
        // Fallback: URL param approach if messaging fails
        const encoded = encodeURIComponent(prompt);
        window.open(`${baseUrl}?actify_prompt=${encoded}`, '_blank');
      }
    } else {
      // External tool — smart context-aware query
      const query = buildSmartQuery(text, category);
      if (app.name === 'YouTube') {
        navigator.clipboard.writeText(query).catch(() => {});
      }
      window.open(app.url + encodeURIComponent(query), '_blank');
    }
  }

  // ================================================================
  // SELECTOR PANEL — for both app pickers AND LLM pickers
  // ================================================================

  function renderSelector(category, text, anchorRect, prebuiltPrompt) {
    destroySelector();

    const apps = APPS[category];
    if (!apps || !apps.length) return;

    selectorEl = document.createElement('div');
    selectorEl.id = 'actifyxai-selector';
    selectorEl.style.cssText = 'visibility:hidden;';

    const isLLMPicker = category === 'ai_llm' || apps.some(a => a.type === 'llm');

    const label = document.createElement('div');
    label.className = 'actifyxai-sel-label';
    label.textContent = isLLMPicker ? '⚡ Choose AI' : 'Open with';
    selectorEl.appendChild(label);

    apps.forEach(app => {
      const btn = document.createElement('button');
      btn.className = 'actifyxai-app-btn' + (app.type === 'ia' ? ' actifyxai-ia-btn' : '');

      if (app.type === 'ia') {
        btn.innerHTML =
          `<span class="actifyxai-app-icon">🧠</span>` +
          `<span class="actifyxai-ia-label">IA <em>Instant Answer</em></span>`;
      } else {
        btn.innerHTML =
          `<span class="actifyxai-app-icon">${app.icon}</span><span>${app.name}</span>`;
      }

      btn.addEventListener('mousedown', (e) => {
        e.stopPropagation();
        isClickingBtn = true;
      });

      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        isClickingBtn = false;

        if (app.type === 'ia') {
          // Instant Answer — call Groq via backend, show inline
          showIAPanel(text, currentAction, anchorRect);
          return; // keep selector open while loading
        }

        if (category !== 'ai_llm') savePref(category, app.name);
        openApp(app, text, category, prebuiltPrompt);
        destroyAll();
      });

      selectorEl.appendChild(btn);
    });

    if (category !== 'ai_llm') {
      const hint = document.createElement('div');
      hint.className = 'actifyxai-sel-hint';
      hint.textContent = '✓ Your choice will be remembered';
      selectorEl.appendChild(hint);
    }

    document.body.appendChild(selectorEl);

    requestAnimationFrame(() => {
      const sw = selectorEl.offsetWidth || 220;
      const sh = selectorEl.offsetHeight || 160;
      const vw = window.innerWidth;
      const vh = window.innerHeight;

      let left = anchorRect.left;
      let top = anchorRect.bottom + 8;

      if (top + sh > vh - 8) top = anchorRect.top - sh - 8;
      if (top < 8) top = 8;
      if (left + sw > vw - 8) left = vw - sw - 8;
      if (left < 8) left = 8;

      selectorEl.style.left = `${Math.round(left)}px`;
      selectorEl.style.top = `${Math.round(top)}px`;
      selectorEl.style.visibility = 'visible';
    });
  }

  // ================================================================
  // IA — INSTANT ANSWER via Groq backend (Advanced Panel)
  // Positioned BESIDE the selector panel (right or left)
  // Features: Expand, Copy, Send to ChatGPT with combined prompt
  // ================================================================

  // Lightweight markdown → HTML (supports code blocks, inline code, bullets, headings, bold/italic)
  function renderMarkdown(md) {
    if (!md) return '';
    let html = md
      // Fenced code blocks
      .replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
        `<pre class="actifyxai-code-block"><code class="lang-${lang || 'text'}">${escHtml(code.trim())}</code></pre>`)
      // Inline code
      .replace(/`([^`]+)`/g, '<code class="actifyxai-inline-code">$1</code>')
      // Headings
      .replace(/^### (.+)$/gm, '<h3 class="actifyxai-h3">$1</h3>')
      .replace(/^## (.+)$/gm,  '<h2 class="actifyxai-h2">$1</h2>')
      .replace(/^# (.+)$/gm,   '<h1 class="actifyxai-h1">$1</h1>')
      // Bold / italic
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g,     '<em>$1</em>')
      // Bullets
      .replace(/^[\-\*] (.+)$/gm, '<li>$1</li>')
      // Numbered list
      .replace(/^\d+\.\s+(.+)$/gm, '<li class="actifyxai-num">$1</li>')
      // Line breaks (not inside pre blocks)
      .replace(/\n/g, '<br>');
    // Wrap consecutive <li> in <ul>
    html = html.replace(/(<li>.*?<\/li>)+/gs, m => `<ul class="actifyxai-ul">${m}</ul>`);
    return html;
  }

  function escHtml(s) {
    return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function showIAPanel(text, action, anchorRect) {
    if (iaPanelEl) { iaPanelEl.remove(); iaPanelEl = null; }

    uiActive = true;  // freeze close-on-click

    // Conversation history for follow-up
    const convoHistory = [{ role: 'user', content: text, action }];

    const actionLabels = {
      fix: '🛠 Fix Error', explain: '🧠 Explain', summarize: '📝 Summarize',
      rewrite: '✍️ Rewrite', refactor: '♻️ Refactor', improve: '✨ Improve',
      shorten: '📏 Shorten', research: '🔬 Research', translate: '🌐 Translate'
    };
    const headerLabel = actionLabels[action] || '🧠 ActifyXAI';

    iaPanelEl = document.createElement('div');
    iaPanelEl.id = 'actifyxai-ia-panel';
    iaPanelEl.className = 'actifyxai-ia-expanded'; // Always expanded now for continuous chat

    iaPanelEl.innerHTML =
      `<div class="actifyxai-ia-header" id="actifyxai-ia-header">` +
        `<span>🔶 <span class="actifyxai-ia-title">${headerLabel}</span></span>` +
        `<div class="actifyxai-ia-header-actions">` +
          `<button class="actifyxai-ia-close" id="actifyxai-ia-close" title="Close">✕</button>` +
        `</div>` +
      `</div>` +
      `<div class="actifyxai-ia-convo" id="actifyxai-ia-convo">` +
        `<div class="actifyxai-ia-loading" id="actifyxai-ia-loading"><span></span><span></span><span></span></div>` +
      `</div>` +
      `<div class="actifyxai-ia-footer" id="actifyxai-ia-footer" style="display:none">` +
        `<span class="actifyxai-ia-model" id="actifyxai-ia-model"></span>` +
        `<div class="actifyxai-ia-actions">` +
          `<button class="actifyxai-ia-copy" id="actifyxai-ia-copy">📋 Copy</button>` +
          `<button class="actifyxai-ia-send" id="actifyxai-ia-send">↗ ChatGPT</button>` +
        `</div>` +
      `</div>` +
      `<div class="actifyxai-ia-input-row" id="actifyxai-ia-input-row" style="display:none">` +
        `<input class="actifyxai-ia-input" id="actifyxai-ia-input" placeholder="Ask a follow-up…" type="text">` +
        `<button class="actifyxai-ia-send-btn" id="actifyxai-ia-send-btn">➤</button>` +
      `</div>`;

    document.body.appendChild(iaPanelEl);
    // Block all clicks inside panel from reaching the document close handler
    iaPanelEl.addEventListener('mousedown', e => e.stopPropagation());
    // Make the panel draggable ONLY by its header
    makeDraggable(iaPanelEl, document.getElementById('actifyxai-ia-header'));

    document.getElementById('actifyxai-ia-close').addEventListener('click', e => {
      e.stopPropagation();
      if (iaPanelEl) { iaPanelEl.remove(); iaPanelEl = null; }
      uiActive = false;  // re-enable normal close behavior
      if (popupEl) { popupEl.style.display = 'none'; }
    });

    positionIAPanel();

    // ── Render result into body ─────────────────────────────────
    function renderResult(resultText, modelUsed) {
      const convo = document.getElementById('actifyxai-ia-convo');
      const loader = document.getElementById('actifyxai-ia-loading');
      if (!convo || !iaPanelEl) return;
      if (loader) loader.remove();

      const isErr = resultText.startsWith('⚠️');
      if (isErr) {
        const isAuth = resultText.includes('invalid or expired') || resultText.includes('401');
        const isRate = resultText.includes('rate limit');
        const hint = isAuth
          ? `Get a free key at <a href="https://console.groq.com/keys" target="_blank" style="color:#a78bfa">console.groq.com/keys</a> → paste in <code>backend/.env</code>`
          : isRate ? 'Wait a moment and try again.'
          : 'Check terminal: <code>uvicorn main:app --reload</code>';
        
        const errBubble = document.createElement('div');
        errBubble.className = 'actifyxai-ia-error-bubble';
        errBubble.innerHTML = `<p class="actifyxai-ia-error">${escHtml(resultText)}</p><p class="actifyxai-ia-hint">${hint}</p>`;
        convo.appendChild(errBubble);
        return;
      }

      // Add AI bubble container
      const aiBubble = document.createElement('div');
      aiBubble.className = 'actifyxai-bubble actifyxai-bubble-ai actifyxai-ia-result';
      aiBubble.style.position = 'relative';
      
      const aiContent = document.createElement('div');
      aiContent.innerHTML = renderMarkdown(resultText);
      aiBubble.appendChild(aiContent);

      const copyBtn = document.createElement('button');
      copyBtn.textContent = '📋';
      copyBtn.className = 'actifyxai-ia-close'; // reuse transparent style
      copyBtn.style.position = 'absolute';
      copyBtn.style.right = '0px';
      copyBtn.style.top = '4px';
      copyBtn.style.background = 'rgba(10, 12, 28, 0.5)';
      copyBtn.title = "Copy message";
      copyBtn.onclick = (e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(resultText).catch(() => {});
        copyBtn.textContent = '✅';
        setTimeout(() => { copyBtn.textContent = '📋'; }, 1500);
      };
      aiBubble.appendChild(copyBtn);

      convo.appendChild(aiBubble);
      convo.scrollTop = convo.scrollHeight;

      // Show footer actions & input
      document.getElementById('actifyxai-ia-footer').style.display = 'flex';
      document.getElementById('actifyxai-ia-model').textContent = `via ${modelUsed || 'groq'}`;
      document.getElementById('actifyxai-ia-input-row').style.display = 'flex';

      // Re-position if it expanded downwards too much
      positionIAPanel();

      document.getElementById('actifyxai-ia-copy').onclick = (e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(resultText).catch(() => {});
        e.currentTarget.textContent = '✅ Copied!';
        setTimeout(() => { try { e.currentTarget.textContent = '📋 Copy'; } catch(_) {} }, 1800);
      };

      document.getElementById('actifyxai-ia-send').onclick = (e) => {
        e.stopPropagation();
        const combined = buildCombinedPrompt(text, resultText, action);
        
        // Graceful fallback: ALWAYS copy to clipboard before opening the new tab
        navigator.clipboard.writeText(combined).catch(() => {});

        try {
          chrome.runtime.sendMessage(
            { type: 'STORE_PROMPT', llm: 'chatgpt', prompt: combined },
            () => window.open('https://chatgpt.com/', '_blank')
          );
        } catch (_) {
          window.open(`https://chatgpt.com/?actify_prompt=${encodeURIComponent(combined)}`, '_blank');
        }
        destroyAll();
      };
      
      document.getElementById('actifyxai-ia-input').focus();
    }

    // ── Follow-up conversation ──────────────────────────────────
    function sendFollowUp(question) {
      const convo = document.getElementById('actifyxai-ia-convo');
      if (!convo) return;

      // Hide footer actions while loading new response
      document.getElementById('actifyxai-ia-footer').style.display = 'none';

      // Show user bubble
      const userBubble = document.createElement('div');
      userBubble.className = 'actifyxai-bubble actifyxai-bubble-user';
      userBubble.style.position = 'relative';
      userBubble.textContent = question;

      const userCopyBtn = document.createElement('button');
      userCopyBtn.textContent = '📋';
      userCopyBtn.className = 'actifyxai-ia-close'; // reuse transparent style
      userCopyBtn.style.position = 'absolute';
      userCopyBtn.style.right = '0px';
      userCopyBtn.style.top = '4px';
      userCopyBtn.style.background = 'rgba(10, 12, 28, 0.3)';
      userCopyBtn.title = "Copy message";
      userCopyBtn.onclick = (e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(question).catch(() => {});
        userCopyBtn.textContent = '✅';
        setTimeout(() => { userCopyBtn.textContent = '📋'; }, 1500);
      };
      userBubble.appendChild(userCopyBtn);

      convo.appendChild(userBubble);

      // Loading bubble
      const aiBubble = document.createElement('div');
      aiBubble.className = 'actifyxai-bubble actifyxai-bubble-ai actifyxai-ia-result';
      aiBubble.innerHTML = '<div class="actifyxai-ia-loading" style="margin:0"><span></span><span></span><span></span></div>';
      convo.appendChild(aiBubble);
      convo.scrollTop = convo.scrollHeight;

      convoHistory.push({ role: 'user', content: question });

      // Build context-aware follow-up query
      const lastAnswer = convoHistory.filter(m => m.role === 'assistant').slice(-1)[0];
      const contextPrompt = lastAnswer
        ? `Previous context:\n"${lastAnswer.content.slice(0, 300)}"\n\nFollow-up question: ${question}`
        : `Original selection: "${text.slice(0, 300)}"\n\nQuestion: ${question}`;

      fetch('http://localhost:8000/api/quick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: contextPrompt, action: 'explain', context_url: window.location.href })
      })
        .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(d.detail || r.status)))
        .then(data => {
          aiBubble.innerHTML = '';
          const aiContent = document.createElement('div');
          aiContent.innerHTML = renderMarkdown(data.result);
          aiBubble.appendChild(aiContent);
          aiBubble.style.position = 'relative';

          const copyBtn = document.createElement('button');
          copyBtn.textContent = '📋';
          copyBtn.className = 'actifyxai-ia-close';
          copyBtn.style.position = 'absolute';
          copyBtn.style.right = '0px';
          copyBtn.style.top = '4px';
          copyBtn.style.background = 'rgba(10, 12, 28, 0.5)';
          copyBtn.title = "Copy message";
          copyBtn.onclick = (e) => {
            e.stopPropagation();
            navigator.clipboard.writeText(data.result).catch(() => {});
            copyBtn.textContent = '✅';
            setTimeout(() => { copyBtn.textContent = '📋'; }, 1500);
          };
          aiBubble.appendChild(copyBtn);

          convoHistory.push({ role: 'assistant', content: data.result });
          
          // Re-show footer actions, update copy text to this newest response
          const footer = document.getElementById('actifyxai-ia-footer');
          footer.style.display = 'flex';
          document.getElementById('actifyxai-ia-model').textContent = `via ${data.model_used || 'groq'}`;
          
          document.getElementById('actifyxai-ia-copy').onclick = (e) => {
            e.stopPropagation();
            navigator.clipboard.writeText(data.result).catch(() => {});
            e.currentTarget.textContent = '✅ Copied!';
            setTimeout(() => { try { e.currentTarget.textContent = '📋 Copy'; } catch(_) {} }, 1800);
          };
          
          convo.scrollTop = convo.scrollHeight;
        })
        .catch(err => {
          aiBubble.textContent = typeof err === 'string' ? err : '⚠️ Error — check backend is running.';
          document.getElementById('actifyxai-ia-footer').style.display = 'flex'; // show so they can still copy old stuff maybe
        });
    }

    // Wire up follow-up input
    function wireFollowUp() {
      const btn   = document.getElementById('actifyxai-ia-send-btn');
      const input = document.getElementById('actifyxai-ia-input');
      if (!btn || !input) return;
      btn.addEventListener('click', e => {
        e.stopPropagation();
        const q = input.value.trim();
        if (!q) return;
        input.value = '';
        sendFollowUp(q);
      });
      input.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          const q = input.value.trim();
          if (!q) return;
          input.value = '';
          sendFollowUp(q);
        }
      });
    }
    wireFollowUp();

    // ── Initial fetch ───────────────────────────────────────────
    fetch('http://localhost:8000/api/quick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text:        text.slice(0, 600),
        action:      action || 'explain',
        context_url: window.location.href,
        intent:      currentIntent
      })
    })
      .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(d.detail || r.status)))
      .then(data => {
        convoHistory.push({ role: 'assistant', content: data.result });
        renderResult(data.result, data.model_used);
      })
      .catch(err => {
        const convo = document.getElementById('actifyxai-ia-convo');
        const loader = document.getElementById('actifyxai-ia-loading');
        if (convo && iaPanelEl) {
          if (loader) loader.remove();
          const isOffline = err instanceof TypeError && err.message.includes('fetch');
          const msg = isOffline ? '⚠️ Cannot reach backend (connection refused)'
            : (typeof err === 'string' ? err : '⚠️ Request failed');
          
          const errBubble = document.createElement('div');
          errBubble.className = 'actifyxai-ia-error-bubble';
          errBubble.innerHTML = 
            `<p class="actifyxai-ia-error">${escHtml(msg)}</p>` +
            `<p class="actifyxai-ia-hint">Start backend: <code>cd backend &amp;&amp; uvicorn main:app --reload</code></p>`;
          convo.appendChild(errBubble);
        }
      });
  }

  function positionIAPanel() {
    if (!iaPanelEl) return;
    requestAnimationFrame(() => {
      const pw  = iaPanelEl.offsetWidth  || 360;
      const ph  = iaPanelEl.offsetHeight || 200;
      const vw  = window.innerWidth;
      const vh  = window.innerHeight;

      let left, top;

      if (selectorEl) {
        // Beside selector: right preferred, then left
        const sr = selectorEl.getBoundingClientRect();
        left = sr.right + 10;
        top  = sr.top;
        if (left + pw > vw - 8) left = sr.left - pw - 10;
        if (left < 8) left = Math.max(8, vw - pw - 8);
      } else if (popupEl && popupEl.style.display !== 'none') {
        const pr = popupEl.getBoundingClientRect();
        left = pr.left;
        top = pr.bottom + 8;
        if (top + ph > vh - 8) {
          top = pr.top - ph - 8;
        }
        if (left + pw > vw - 8) left = vw - pw - 8;
        if (left < 8) left = 8;
      } else {
        // Standalone (DIRECT_ACTION): anchor near cursor / center-right
        left = Math.min(lastMouseX + 12, vw - pw - 8);
        top  = Math.min(lastMouseY - ph / 2, vh - ph - 8);
        if (left < 8) left = 8;
      }

      if (top + ph > vh - 8) top = vh - ph - 8;
      if (top < 8) top = 8;

      iaPanelEl.style.left = `${Math.round(left)}px`;
      iaPanelEl.style.top  = `${Math.round(top)}px`;
    });
  }

  // Advanced combined prompt: Now replaced by the natural prompt engine
  function buildCombinedPrompt(originalText, iaResult, action) {
    // We completely drop the robotic 'You are an expert...' template and the IA result duplication.
    // Instead, we just pass the exact natural question they would have typed to continue the flow.
    return buildContextualInjectionPrompt(action, originalText);
  }

  function escapeHtml(str) {
    return (str || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
      .replace(/\n/g, '<br>');
  }

  // ================================================================
  // DESTROY
  // ================================================================

  function destroySelector() {
    if (selectorEl) { selectorEl.remove(); selectorEl = null; }
    // NOTE: does NOT remove iaPanelEl — IA panel manages its own lifecycle
  }

  function destroyAll() {
    isClickingBtn = false;
    uiActive = false;
    currentText = '';
    if (popupEl)    { popupEl.style.display = 'none'; }
    if (selectorEl) { selectorEl.remove(); selectorEl = null; }
    if (iaPanelEl)  { iaPanelEl.remove(); iaPanelEl = null; }
  }

} // end guard