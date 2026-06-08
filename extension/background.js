// ================================================================
// ActifyXAI — background.js  v7.2
// • TTL-based prompt relay (survives SPA redirects)
// • INJECT_INTO_PAGE: runs injection in MAIN world via executeScript
//   → This is the definitive fix for Claude / Gemini / DeepSeek
// ================================================================

'use strict';

const promptStore = {};
const TTL_MS = 30000;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {

  if (message.type === 'OPEN_TAB') {
    chrome.tabs.create({ url: message.url });
    return;
  }

  // Content script stores a prompt BEFORE opening a new tab
  if (message.type === 'STORE_PROMPT') {
    promptStore[message.llm] = { prompt: message.prompt, ts: Date.now() };
    sendResponse({ ok: true });
    return;
  }

  // Inject script reads the pending prompt (multi-read within TTL)
  if (message.type === 'GET_PROMPT') {
    const entry = promptStore[message.llm];
    if (entry && (Date.now() - entry.ts) < TTL_MS) {
      sendResponse({ prompt: entry.prompt });
    } else {
      if (entry) delete promptStore[message.llm];
      sendResponse({ prompt: null });
    }
    return true;
  }

  // Inject script clears the prompt after successful injection
  if (message.type === 'CLEAR_PROMPT') {
    delete promptStore[message.llm];
    return;
  }

  // ── MAIN-WORLD INJECTION ─────────────────────────────────────
  // Inject script found the editor → background runs injection in
  // MAIN world so paste / execCommand work with the page's own JS
  if (message.type === 'INJECT_INTO_PAGE') {
    const tabId = sender.tab && sender.tab.id;
    if (!tabId) return;

    chrome.scripting.executeScript({
      target: { tabId },
      world: 'MAIN',
      func: mainWorldInject,
      args: [message.text, message.llm]
    }).catch(err =>
      console.error('[ActifyXAI] executeScript error:', err.message)
    );

    sendResponse({ ok: true });
    return true;
  }
});

// ================================================================
// mainWorldInject — runs in PAGE context (MAIN world)
// Has full access to the page's JS, DataTransfer, execCommand, etc.
// MUST be a pure function (no references to outer scope)
// ================================================================

function mainWorldInject(text, llm) {
  function findEditor(llm) {
    // Gemini shadow DOM (rich-textarea)
    if (llm === 'gemini') {
      const host = document.querySelector('rich-textarea');
      if (host && host.shadowRoot) {
        const inner = host.shadowRoot.querySelector('[contenteditable="true"]');
        if (inner) return inner;
      }
      // Walk all shadow roots
      for (const el of document.querySelectorAll('*')) {
        if (el.shadowRoot) {
          const found = el.shadowRoot.querySelector('[contenteditable="true"]');
          if (found) return found;
        }
      }
    }

    // DeepSeek
    if (llm === 'deepseek') {
      return (
        document.querySelector('textarea#chat-input') ||
        document.querySelector('textarea[placeholder]') ||
        document.querySelector('div[contenteditable="true"]') ||
        document.querySelector('textarea')
      );
    }

    // Claude / ChatGPT / Perplexity / generic
    return (
      document.querySelector('#prompt-textarea') ||
      document.querySelector('.ProseMirror[contenteditable="true"]') ||
      document.querySelector('div[contenteditable="true"][spellcheck]') ||
      document.querySelector('div[contenteditable="true"][data-placeholder]') ||
      document.querySelector('div[contenteditable="true"]') ||
      document.querySelector('textarea')
    );
  }

  const editor = findEditor(llm);
  if (!editor) return false;

  editor.focus();

  if (editor.tagName === 'TEXTAREA') {
    // React-aware value setter
    const nativeSetter = Object.getOwnPropertyDescriptor(
      HTMLTextAreaElement.prototype, 'value'
    ).set;
    nativeSetter.call(editor, text);
    editor.dispatchEvent(new Event('input', { bubbles: true }));
    editor.dispatchEvent(new Event('change', { bubbles: true }));
    editor.setSelectionRange(text.length, text.length);
    return true;
  }

  if (editor.getAttribute('contenteditable') === 'true') {
    // Step 1: clear
    editor.innerHTML = '';
    editor.focus();

    // Step 2: paste event (most reliable — page's own handler processes it)
    let pasteWorked = false;
    try {
      const dt = new DataTransfer();
      dt.setData('text/plain', text);
      editor.dispatchEvent(new ClipboardEvent('paste', {
        bubbles: true, cancelable: true, clipboardData: dt
      }));
      pasteWorked = editor.textContent.trim().length > 0;
    } catch (e) { }

    // Step 3: execCommand (works in MAIN world even without user gesture)
    if (!pasteWorked) {
      editor.focus();
      document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      const inserted = document.execCommand('insertText', false, text);
      if (!inserted) {
        // Step 4: direct textContent + InputEvent
        editor.textContent = text;
        editor.dispatchEvent(new InputEvent('input', {
          bubbles: true, cancelable: true,
          inputType: 'insertText', data: text
        }));
      }
    }

    // Move cursor to end
    try {
      const range = document.createRange();
      const sel = window.getSelection();
      range.selectNodeContents(editor);
      range.collapse(false);
      sel.removeAllRanges();
      sel.addRange(range);
      editor.scrollTop = editor.scrollHeight;
    } catch (e) { }

    return true;
  }

  return false;
}