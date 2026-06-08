// ================================================================
// ActifyXAI — chatgpt_inject.js  v7.2
// Pattern: isolated-world polls DOM → background injects in MAIN world
// ================================================================
'use strict';

(function () {
  const params = new URLSearchParams(window.location.search);
  const rawParam = params.get('actify_prompt');

  if (rawParam) {
    try {
      window.history.replaceState({}, document.title,
        window.location.origin + window.location.pathname);
    } catch (e) { }
    pollAndInject(decodeURIComponent(rawParam), null);
    return;
  }

  try {
    chrome.runtime.sendMessage({ type: 'GET_PROMPT', llm: 'chatgpt' }, (res) => {
      if (chrome.runtime.lastError) return;
      if (res && res.prompt) pollAndInject(res.prompt, 'chatgpt');
    });
  } catch (e) { }
})();

function editorReady() {
  return !!(
    document.querySelector('#prompt-textarea') ||
    document.querySelector('.ProseMirror[contenteditable="true"]') ||
    document.querySelector('[contenteditable="true"][data-lexical-editor]') ||
    document.querySelector('div[contenteditable="true"]') ||
    document.querySelector('textarea')
  );
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
        { type: 'INJECT_INTO_PAGE', text, llm: 'chatgpt' },
        () => {
          if (chrome.runtime.lastError) return;
          if (llmKey) {
            try { chrome.runtime.sendMessage({ type: 'CLEAR_PROMPT', llm: llmKey }); } catch (e) { }
          }
        }
      );
    } else if (elapsed >= MAX) {
      clearInterval(timer);
    }
  }, TICK);
}