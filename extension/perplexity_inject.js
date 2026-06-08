// ================================================================
// ActifyXAI — perplexity_inject.js  v7.2
// Pattern: isolated-world polls DOM → background injects in MAIN world
// ================================================================
'use strict';

(function () {
  const params = new URLSearchParams(window.location.search);
  const rawParam = params.get('actify_prompt') || params.get('q');

  if (rawParam) {
    try {
      window.history.replaceState({}, document.title,
        window.location.origin + window.location.pathname);
    } catch (e) { }
    pollAndInject(decodeURIComponent(rawParam), null);
    return;
  }

  try {
    chrome.runtime.sendMessage({ type: 'GET_PROMPT', llm: 'perplexity' }, (res) => {
      if (chrome.runtime.lastError) return;
      if (res && res.prompt) pollAndInject(res.prompt, 'perplexity');
    });
  } catch (e) { }
})();

function editorReady() {
  return !!(
    document.querySelector('textarea[placeholder]') ||
    document.querySelector('textarea') ||
    document.querySelector('[contenteditable="true"]')
  );
}

function showFallbackNotification() {
  const div = document.createElement('div');
  div.textContent = 'ActifyXAI: Direct injection unavailable currently. Query copied to clipboard.';
  div.style.cssText = 'position:fixed; top:20px; right:20px; background:rgba(248,113,113,0.9); color:white; padding:12px 20px; border-radius:8px; z-index:999999; font-family:sans-serif; font-size:14px; box-shadow:0 4px 12px rgba(0,0,0,0.15); pointer-events:none; transition:opacity 0.3s;';
  document.body.appendChild(div);
  setTimeout(() => { div.style.opacity = '0'; setTimeout(() => div.remove(), 300); }, 4000);
}

function pollAndInject(text, llmKey) {
  let elapsed = 0;
  const MAX = 25000;
  const TICK = 400;

  const timer = setInterval(() => {
    elapsed += TICK;
    if (editorReady()) {
      clearInterval(timer);
      chrome.runtime.sendMessage(
        { type: 'INJECT_INTO_PAGE', text, llm: 'perplexity' },
        (res) => {
          if (chrome.runtime.lastError || (res && res.error)) {
            showFallbackNotification();
            return;
          }
          if (llmKey) {
            try { chrome.runtime.sendMessage({ type: 'CLEAR_PROMPT', llm: llmKey }); } catch (e) { }
          }
        }
      );
    } else if (elapsed >= MAX) {
      clearInterval(timer);
      showFallbackNotification();
    }
  }, TICK);
}