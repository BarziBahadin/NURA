(function () {
  'use strict';

  var _s = document.currentScript;
  function initNuraWidget() {
  if (window.__NURA_WIDGET_LOADED__) return;
  window.__NURA_WIDGET_LOADED__ = true;

  var API_BASE = (_s && _s.getAttribute('data-api')) || '/v1';
  var initialLang = (_s && _s.getAttribute('data-lang')) || 'ar';
  var widgetPosition = (_s && _s.getAttribute('data-position')) || 'bottom-left';
  var primaryColor = (_s && _s.getAttribute('data-primary')) || '#f97316';
  var accentColor = (_s && _s.getAttribute('data-accent')) || '#22c55e';
  var brandTitle = (_s && _s.getAttribute('data-title')) || 'NURA';
  var autoOpen = (_s && _s.getAttribute('data-auto-open')) === 'true';

  if (initialLang !== 'ar' && initialLang !== 'ku' && initialLang !== 'en') initialLang = 'ar';
  if (widgetPosition !== 'bottom-right') widgetPosition = 'bottom-left';

  // ── Inject styles ──────────────────────────────────────────────────────────
  var style = document.createElement('style');
  style.textContent = [
    ':host { all: initial; color-scheme: light; }',
    '#nura-widget-root * { box-sizing: border-box; margin: 0; padding: 0; }',
    '#nura-widget-root {',
    '  --nura-primary: #f97316;',
    '  --nura-accent: #22c55e;',
    '  --nura-viewport-height: 100vh;',
    '  font-family: \'Segoe UI\', \'Noto Sans Arabic\', Tahoma, Arial, sans-serif;',
    '}',

    '#chat-toggle {',
    '  position: fixed; bottom: calc(28px + env(safe-area-inset-bottom, 0px)); left: 28px;',
    '  width: 60px; height: 60px; border-radius: 50%;',
    '  background: #111827;',
    '  border: none; cursor: pointer;',
    '  box-shadow: 0 14px 34px rgba(17,24,39,0.24);',
    '  display: flex; align-items: center; justify-content: center;',
    '  transition: transform 0.2s, box-shadow 0.2s, opacity 0.22s; z-index: 2147483640;',
    '  -webkit-tap-highlight-color: transparent;',
    '}',
    '#nura-widget-root.nura-pos-bottom-right #chat-toggle { left: auto; right: 28px; }',
    '#chat-toggle:hover { transform: translateY(-1px); box-shadow: 0 18px 42px rgba(17,24,39,0.28); }',

    '#nura-badge {',
    '  position: absolute; top: -4px; right: -4px;',
    '  background: #22c55e; color: #fff; border-radius: 50%;',
    '  width: 20px; height: 20px; font-size: 11px; font-weight: 700;',
    '  display: none; align-items: center; justify-content: center;',
    '}',

    '#chat-window {',
    '  position: fixed; top: 50%; left: 50%;',
    '  width: 430px; max-height: 700px;',
    '  background: #fff; border-radius: 12px; border: 1px solid rgba(17,24,39,0.12);',
    '  box-shadow: 0 24px 64px rgba(15,23,42,0.20);',
    '  display: flex; flex-direction: column; overflow: hidden;',
    '  overscroll-behavior: contain;',
    '  z-index: 2147483639;',
    '  transform: translate(-50%, -50%) scale(0.85);',
    '  opacity: 0; pointer-events: none;',
    '  transition: transform 0.25s cubic-bezier(.34,1.56,.64,1), opacity 0.2s;',
    '}',
    '#chat-window.nura-open { transform: translate(-50%, -50%) scale(1); opacity: 1; pointer-events: all; }',

    '.nura-chat-header {',
    '  background: #111827;',
    '  padding: 14px 16px; display: flex; align-items: center; gap: 10px; flex-shrink: 0;',
    '  direction: ltr; position: relative; overflow: hidden;',
    '}',
    '.nura-avatar {',
    '  width: 40px; height: 40px; border-radius: 10px;',
    '  background: #fff; border: 1px solid rgba(255,255,255,0.35);',
    '  display: flex; align-items: center; justify-content: center;',
    '  color: var(--nura-primary); font-weight: 900; font-size: 13px; flex-shrink: 0; letter-spacing: -0.5px;',
    '}',
    '.nura-header-info { flex: 1; min-width: 0; text-align: right; }',
    '#chat-window[dir="ltr"] .nura-header-info { text-align: left; }',
    '.nura-header-info h3 { color: #fff; font-size: 15px; font-weight: 900; line-height: 1.2; }',
    '.nura-header-info span { color: rgba(229,231,235,0.88); font-size: 12px; display: inline-flex; align-items: center; gap: 5px; }',
    '.nura-online-dot {',
    '  width: 7px; height: 7px; background: #22c55e; border-radius: 50%;',
    '  display: inline-block; margin: 0; animation: nuraPulse 2s infinite;',
    '}',
    '@keyframes nuraPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }',

    '#nura-lang-toggle {',
    '  display: flex; align-items: center;',
    '  background: rgba(255,255,255,0.16); border-radius: 999px; overflow: hidden;',
    '  border: 1px solid rgba(255,255,255,0.34); flex-shrink: 0; padding: 2px;',
    '}',
    '.nura-lang-btn {',
    '  background: none; border: none; color: rgba(255,255,255,0.7);',
    '  font-size: 11px; font-weight: 800; padding: 4px 9px; cursor: pointer; border-radius: 999px;',
    '  transition: background 0.15s, color 0.15s; font-family: inherit; letter-spacing: 0.3px;',
    '}',
    '.nura-lang-btn.active { background: rgba(255,255,255,0.95); color: #ea580c; }',
    '.nura-lang-btn:hover:not(.active) { color: #fff; }',

    '#nura-close-btn {',
    '  width: 34px; height: 34px; border-radius: 50%; background: rgba(255,255,255,0.12); border: none; color: rgba(255,255,255,0.92);',
    '  cursor: pointer; font-size: 18px; line-height: 1; padding: 0; display: flex; align-items: center; justify-content: center;',
    '}',
    '#nura-close-btn:hover { color: #fff; background: rgba(255,255,255,0.2); }',

    '#nura-messages {',
    '  flex: 1; overflow-y: auto; padding: 16px 18px 12px; background: #fbfbfc;',
    '  display: flex; flex-direction: column; gap: 10px; scroll-behavior: smooth;',
    '  overscroll-behavior: contain; -webkit-overflow-scrolling: touch;',
    '}',
    '#nura-messages::-webkit-scrollbar { width: 4px; }',
    '#nura-messages::-webkit-scrollbar-thumb { background: #ccc; border-radius: 4px; }',

    '.nura-msg { display: flex; flex-direction: column; max-width: 86%; animation: nuraFadeUp 0.2s ease; }',
    '@keyframes nuraFadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }',
    '.nura-msg.user  { align-self: flex-start; }',
    '.nura-msg.bot   { align-self: flex-end; }',
    '.nura-msg.agent { align-self: flex-end; }',

    '.nura-bubble {',
    '  padding: 10px 14px; border-radius: 10px; font-size: 13.5px;',
    '  line-height: 1.65; word-break: break-word; white-space: pre-wrap; unicode-bidi: plaintext; text-align: start;',
    '}',
    '.nura-msg.user  .nura-bubble { background: #111827; color: #fff; border-bottom-right-radius: 4px; box-shadow: 0 5px 14px rgba(15,23,42,0.14); }',
    '.nura-msg.bot   .nura-bubble { background: #fff; color: #1f2937; border: 1px solid #e5e7eb; border-bottom-left-radius: 4px; box-shadow: 0 4px 14px rgba(15,23,42,0.04); }',
    '.nura-msg.agent .nura-bubble { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; border-bottom-left-radius: 4px; }',

    '.nura-msg.bot .nura-followup-bubble {',
    '  margin-top: 5px; padding: 8px 13px; border-radius: 16px; border-bottom-left-radius: 4px;',
    '  font-size: 13px; background: #fff7ed; color: #c2410c;',
    '  border: 1px solid #fed7aa; animation: nuraFadeUp 0.2s ease;',
    '}',
    '.nura-followup-btns { margin-top: 7px; display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-start; }',
    '.nura-followup-btn {',
    '  background: #fff; border: 1.5px solid #f97316; color: #c2410c;',
    '  border-radius: 20px; padding: 4px 11px; font-size: 12px; cursor: pointer;',
    '  font-family: inherit; transition: background 0.15s, color 0.15s;',
    '}',
    '.nura-followup-btn:hover { background: #f97316; color: #fff; }',
    '.nura-followup-btn.no { border-color: #ccc; color: #888; }',
    '.nura-followup-btn.no:hover { background: #f0f2f5; color: #555; }',

    '.nura-meta {',
    '  font-size: 10px; color: #aaa; margin-top: 3px; padding: 0 4px;',
    '  display: flex; align-items: center; gap: 6px;',
    '}',
    '.nura-msg.user  .nura-meta { align-self: flex-start; }',
    '.nura-msg.bot   .nura-meta { align-self: flex-end; flex-direction: row-reverse; }',
    '.nura-msg.agent .nura-meta { align-self: flex-end; flex-direction: row-reverse; }',
    '.nura-msg-time { opacity: 0; transition: opacity 0.18s; }',
    '.nura-msg:hover .nura-msg-time, .nura-bot-row:hover .nura-msg-time { opacity: 1; }',

    '.nura-read-tick { font-size: 10px; color: #ccc; margin-top: 2px; align-self: flex-start; padding: 0 4px; transition: color 0.2s; }',
    '.nura-read-tick.read { color: var(--nura-primary); }',

    '.nura-bot-row { display: flex; align-items: flex-end; gap: 7px; align-self: flex-end; max-width: 86%; }',
    '.nura-bot-row .nura-msg { max-width: 100%; }',
    '.nura-bot-avatar-sm {',
    '  width: 26px; height: 26px; border-radius: 50%;',
    '  background: #111827;',
    '  color: #fff; font-size: 9px; font-weight: 900;',
    '  display: flex; align-items: center; justify-content: center;',
    '  flex-shrink: 0; letter-spacing: -0.3px; margin-bottom: 16px;',
    '}',
    '.nura-bot-content { display: flex; flex-direction: column; min-width: 0; }',

    '.nura-source-tag {',
    '  font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 20px;',
    '  text-transform: uppercase; letter-spacing: 0.5px;',
    '}',
    '.nura-source-tag.local  { background: #dcfce7; color: #15803d; }',
    '.nura-source-tag.openai { background: #e8d4f7; color: #6b1a99; }',
    '.nura-source-tag.low    { background: #ffecd4; color: #b45309; }',
    '.nura-source-doc-chip {',
    '  display: inline-flex; align-items: center; gap: 3px;',
    '  font-size: 9.5px; color: #888; margin-top: 2px;',
    '  background: #f8fafc; border: 1px solid #e2e8f0;',
    '  border-radius: 8px; padding: 1px 7px;',
    '  max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;',
    '}',

    '#nura-typing {',
    '  display: none; align-self: flex-end;',
    '  padding: 10px 14px;',
    '  background: #fff; border: 1px solid #eef0f3;',
    '  border-radius: 18px; border-bottom-left-radius: 4px;',
    '  animation: nuraFadeUp 0.2s ease; margin: 0 16px 0;',
    '}',
    '#nura-typing span {',
    '  display: inline-block; width: 7px; height: 7px; border-radius: 50%;',
    '  background: #fb7c28; margin: 0 2px; animation: nuraBounce 1.2s infinite;',
    '}',
    '#nura-typing span:nth-child(2) { animation-delay: 0.2s; }',
    '#nura-typing span:nth-child(3) { animation-delay: 0.4s; }',
    '@keyframes nuraBounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }',

    '#nura-tree-panel {',
    '  border-top: 1px solid #edf2f7; padding: 12px 14px 14px;',
    '  flex-shrink: 0; background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%); max-height: 230px; overflow-y: auto;',
    '  overscroll-behavior: contain; -webkit-overflow-scrolling: touch;',
    '  transition: max-height 0.18s ease, padding 0.18s ease, border-color 0.18s ease, opacity 0.14s ease;',
    '}',
    '#nura-tree-panel::-webkit-scrollbar { width: 3px; }',
    '#nura-tree-panel::-webkit-scrollbar-thumb { background: #ddd; border-radius: 3px; }',

    '.nura-tree-nav-bar { display: flex; align-items: center; gap: 9px; margin-bottom: 8px; min-height: 34px; }',
    '.nura-tree-title { flex: 1; min-width: 0; color: #111827; font-size: 13px; font-weight: 900; line-height: 1.25; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: start; }',
    '.nura-tree-nav-btn {',
    '  width: 32px; height: 32px; background: #fff; border: 1px solid #e5e7eb; color: #111827;',
    '  border-radius: 50%; padding: 0; font-size: 20px; line-height: 1; cursor: pointer;',
    '  font-family: inherit; transition: background 0.15s, color 0.15s, border-color 0.15s, transform 0.15s; flex-shrink: 0;',
    '  display: inline-flex; align-items: center; justify-content: center;',
    '}',
    '.nura-tree-nav-btn:hover { background: #fff7ed; color: var(--nura-primary); border-color: #fed7aa; transform: translateY(-1px); }',
    '.nura-tree-nav-btn.home { font-size: 16px; color: #64748b; background: #f8fafc; }',
    '.nura-tree-nav-btn.home:hover { background: #f1f5f9; color: #111827; border-color: #cbd5e1; }',

    '.nura-tree-level-q { font-size: 12px; color: #111827; font-weight: 900; margin-bottom: 10px; text-align: right; }',
    '.nura-tree-level-q.sub { color: #64748b; font-size: 11.5px; font-weight: 800; margin-top: -2px; }',
    '#chat-window[dir="ltr"] .nura-tree-level-q { text-align: left; }',
    '.nura-agent-bypass-btn {',
    '  margin-top: 12px; width: 100%; padding: 11px 14px;',
    '  background: #111827; border: 1px solid #1f2937; border-radius: 14px;',
    '  color: #fff; font-size: 13px; font-weight: 900; cursor: pointer;',
    '  transition: background 0.15s, color 0.15s, border-color 0.15s, transform 0.15s;',
    '}',
    '.nura-agent-bypass-btn:hover { background: #0f172a; border-color: #f97316; transform: translateY(-1px); }',
    '.nura-suggestion-card {',
    '  background: #fff; border: 1px solid #e5e7eb; border-radius: 14px; padding: 12px;',
    '  box-shadow: 0 6px 18px rgba(15,23,42,0.05);',
    '}',
    '.nura-suggestion-card h4 { font-size: 13px; color: #111827; font-weight: 900; margin-bottom: 5px; text-align: start; }',
    '.nura-suggestion-card p { font-size: 12px; color: #64748b; line-height: 1.55; margin-bottom: 10px; text-align: start; }',
    '.nura-suggestion-input {',
    '  width: 100%; min-height: 86px; border: 1px solid #e5e7eb; border-radius: 12px;',
    '  resize: vertical; padding: 10px 12px; font-size: 13px; font-family: inherit; line-height: 1.5;',
    '  color: #111827; outline: none; background: #fff;',
    '}',
    '.nura-suggestion-input:focus { border-color: var(--nura-primary); box-shadow: 0 0 0 3px rgba(249,115,22,0.12); }',
    '.nura-suggestion-actions { display: flex; gap: 8px; margin-top: 10px; align-items: center; }',
    '.nura-suggestion-submit {',
    '  flex: 1; border: none; border-radius: 12px; padding: 9px 12px;',
    '  background: #111827; color: #fff; font-size: 12.5px; font-weight: 900; cursor: pointer; font-family: inherit;',
    '}',
    '.nura-suggestion-submit:disabled { opacity: 0.45; cursor: default; }',
    '.nura-suggestion-cancel {',
    '  border: 1px solid #e5e7eb; border-radius: 12px; padding: 9px 12px;',
    '  background: #fff; color: #64748b; font-size: 12.5px; font-weight: 800; cursor: pointer; font-family: inherit;',
    '}',
    '.nura-suggestion-error { margin-top: 8px; color: #be123c; font-size: 11.5px; text-align: start; }',
    '.nura-tree-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }',
    '.nura-tree-opt {',
    '  background: #fff; border: 1px solid #e2e8f0; color: #1f2937;',
    '  border-radius: 8px; padding: 9px 12px; min-height: 38px; font-size: 12.5px; cursor: pointer;',
    '  font-family: inherit; transition: background 0.15s, border-color 0.15s, color 0.15s, box-shadow 0.15s; white-space: normal;',
    '  display: inline-flex; align-items: center; justify-content: center; gap: 5px; text-align: center; line-height: 1.35;',
    '}',
    '.nura-tree-opt:hover { background: #fff7ed; border-color: #fb923c; color: #ea580c; box-shadow: 0 5px 14px rgba(234,88,12,0.08); }',
    '.nura-tree-opt.has-children::after { content: \' ›\'; font-size: 13px; opacity: 0.6; }',

    '.nura-chat-footer {',
    '  border-top: 1px solid #f0f2f5; padding: 12px 14px;',
    '  display: flex; gap: 9px; align-items: flex-end; flex-shrink: 0; background: #fff; direction: rtl;',
    '}',
    '#chat-window[dir="ltr"] .nura-chat-footer { direction: ltr; }',
    '#nura-msg-input {',
    '  flex: 1; border: 1px solid #e5e7eb; border-radius: 999px; background: #fff;',
    '  padding: 11px 16px; font-size: 14px; font-family: inherit;',
    '  outline: none; resize: none; max-height: 100px; line-height: 1.4;',
    '  transition: border-color 0.2s, box-shadow 0.2s; text-align: right;',
    '}',
    '#nura-msg-input:focus { border-color: var(--nura-primary); box-shadow: 0 0 0 3px rgba(249,115,22,0.14); }',
    '#chat-window[dir="ltr"] #nura-msg-input { text-align: left; }',
    '#nura-msg-input::placeholder { color: #bbb; }',

    '#nura-send-btn {',
    '  width: 42px; height: 42px; border-radius: 50%;',
    '  background: #111827;',
    '  border: none; cursor: pointer;',
    '  display: flex; align-items: center; justify-content: center; flex-shrink: 0;',
    '  transition: transform 0.15s, opacity 0.15s;',
    '}',
    '#nura-send-btn:hover { transform: scale(1.08); }',
    '#nura-send-btn:disabled { opacity: 0.38; cursor: default; transform: none; filter: grayscale(0.2); }',
    '#nura-send-btn svg { width: 18px; height: 18px; fill: #fff; }',

    '#nura-attach-btn {',
    '  width: 38px; height: 38px; border-radius: 50%;',
    '  background: #f0f2f5; border: none; cursor: pointer;',
    '  display: flex; align-items: center; justify-content: center; flex-shrink: 0;',
    '  font-size: 17px; transition: background 0.15s, color 0.15s, opacity 0.15s; color: #888;',
    '}',
    '#nura-attach-btn:hover { background: #e0e4ea; color: #111827; }',
    '#nura-attach-btn:disabled { opacity: 0.5; cursor: default; }',
    '.nura-chat-img {',
    '  max-width: 230px; max-height: 180px; border-radius: 14px;',
    '  border: 1px solid rgba(255,255,255,0.4); object-fit: cover; cursor: pointer;',
    '  box-shadow: 0 5px 16px rgba(15,23,42,0.12);',
    '}',

    '.nura-feedback-btns { display: flex; gap: 4px; margin-top: 4px; justify-content: flex-end; }',
    '.nura-fb-btn {',
    '  background: none; border: 1.5px solid #ddd; border-radius: 50%;',
    '  width: 22px; height: 22px; font-size: 12px; cursor: pointer;',
    '  display: flex; align-items: center; justify-content: center;',
    '  transition: all 0.15s; color: #bbb; line-height: 1; padding: 0;',
    '}',
    '.nura-fb-btn.good:hover  { border-color: #06d6a0; color: #06d6a0; }',
    '.nura-fb-btn.bad:hover   { border-color: #ef476f; color: #ef476f; }',
    '.nura-fb-btn.sel-good    { border-color: #06d6a0; color: #06d6a0; background: rgba(6,214,160,0.1); }',
    '.nura-fb-btn.sel-bad     { border-color: #ef476f; color: #ef476f; background: rgba(239,71,111,0.1); }',
    '.nura-fb-btn:disabled    { opacity: 0.45; cursor: default; }',

    '.nura-escalation-banner {',
    '  background: linear-gradient(135deg, #fff8ed, #fffbf2); border: 1px solid #fcd34d; border-radius: 14px;',
    '  padding: 12px 16px; font-size: 13px; color: #92400e;',
    '  display: flex; align-items: center; gap: 10px;',
    '  animation: nuraFadeUp 0.2s ease; box-shadow: 0 4px 12px rgba(252,211,77,0.15);',
    '}',
    '.nura-esc-spinner {',
    '  width: 18px; height: 18px; border: 2.5px solid #fde68a; border-top-color: #f59e0b;',
    '  border-radius: 50%; animation: nuraSpin 0.8s linear infinite; flex-shrink: 0;',
    '}',
    '@keyframes nuraSpin { to { transform: rotate(360deg); } }',
    '.nura-error-bubble {',
    '  background: #fff1f2; color: #be123c; border: 1px solid #fecdd3;',
    '  padding: 8px 14px; border-radius: 12px; font-size: 13px; align-self: flex-end;',
    '}',
    '.nura-rating-prompt {',
    '  background: #f9f9f9; border: 1px solid #e0e0e0; border-radius: 12px;',
    '  padding: 10px 14px; text-align: center; font-size: 13px; color: #555;',
    '  animation: nuraFadeUp 0.2s ease;',
    '}',
    '.nura-rating-stars { display: flex; justify-content: center; gap: 4px; margin-top: 7px; }',
    '.nura-star-btn {',
    '  background: none; border: none; font-size: 24px; cursor: pointer;',
    '  color: #ddd; transition: color 0.15s, transform 0.1s; line-height: 1; padding: 0 2px;',
    '}',
    '.nura-star-btn:hover, .nura-star-btn.lit { color: var(--nura-primary); }',
    '.nura-star-btn:hover { transform: scale(1.15); }',

    '@media (prefers-reduced-motion: reduce) {',
    '  #nura-widget-root *, #nura-widget-root *::before, #nura-widget-root *::after { animation-duration: 0.001ms !important; animation-iteration-count: 1 !important; transition-duration: 0.001ms !important; scroll-behavior: auto !important; }',
    '}',
    '@media (max-width: 600px) {',
    '  #chat-toggle { width: 56px; height: 56px; bottom: calc(20px + env(safe-area-inset-bottom, 0px)); left: 20px; }',
    '  #nura-widget-root.nura-pos-bottom-right #chat-toggle { left: auto; right: 20px; }',
    '  #chat-window {',
    '    top: 0; left: 0; right: 0; bottom: 0;',
    '    width: 100vw; height: 100%; height: 100dvh; max-height: none; border-radius: 0; border: none;',
    '    transform: translateY(105%); opacity: 1;',
    '  }',
    '  #chat-window.nura-open { transform: translateY(0); }',
    '  #chat-window.nura-keyboard-active { height: var(--nura-viewport-height); }',
    '  .nura-chat-header { padding-top: calc(16px + env(safe-area-inset-top, 0px)); border-radius: 0; }',
    '  .nura-chat-footer { padding-bottom: calc(14px + env(safe-area-inset-bottom, 0px)); }',
    '  #nura-msg-input { font-size: 16px; }',
    '  .nura-msg { max-width: 92%; }',
    '  .nura-tree-options { grid-template-columns: 1fr; }',
    '  #nura-tree-panel { max-height: 260px; }',
    '  #chat-window.nura-mobile-input-active #nura-tree-panel {',
    '    max-height: 0; padding-top: 0; padding-bottom: 0; border-top-color: transparent; opacity: 0; overflow: hidden;',
    '  }',
    '  #nura-close-btn { width: 44px; height: 44px; font-size: 20px; }',
    '  .nura-tree-nav-btn { width: 44px; height: 44px; }',
    '  .nura-tree-opt { min-height: 48px; font-size: 14px; padding: 12px 14px; }',
    '  .nura-followup-btn { min-height: 40px; padding: 8px 14px; font-size: 13px; }',
    '  .nura-bubble { font-size: 15px; }',
    '}',
    '@media (prefers-reduced-motion: reduce) {',
    '  #nura-widget-root *, #nura-widget-root *::before, #nura-widget-root *::after {',
    '    animation-duration: 0.001ms !important; animation-iteration-count: 1 !important;',
    '    scroll-behavior: auto !important; transition-duration: 0.001ms !important;',
    '  }',
    '}',
  ].join('\n');

  var host = document.createElement('div');
  host.id = 'nura-widget-host';
  var shadowRoot = host.attachShadow ? host.attachShadow({ mode: 'open' }) : null;
  if (shadowRoot) {
    shadowRoot.appendChild(style);
  } else {
    document.head.appendChild(style);
  }

  // ── Inject HTML ────────────────────────────────────────────────────────────
  var root = document.createElement('div');
  root.id = 'nura-widget-root';
  root.className = widgetPosition === 'bottom-right' ? 'nura-pos-bottom-right' : 'nura-pos-bottom-left';
  root.style.setProperty('--nura-primary', primaryColor);
  root.style.setProperty('--nura-accent', accentColor);
  root.innerHTML = [
    '<button id="chat-toggle" aria-expanded="false" aria-controls="chat-window">',
    '  <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="white" viewBox="0 0 24 24">',
    '    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>',
    '  </svg>',
    '  <div id="nura-badge">1</div>',
    '</button>',
    '<div id="chat-window" role="dialog" aria-modal="false" aria-hidden="true" aria-label="نافذة دعم العملاء">',
    '  <div class="nura-chat-header">',
    '    <button id="nura-close-btn" aria-label="إغلاق">✕</button>',
    '    <div id="nura-lang-toggle" role="group" aria-label="Language">',
    '      <button class="nura-lang-btn active" data-lang="ar">عربي</button>',
    '      <button class="nura-lang-btn" data-lang="ku">Kurdî</button>',
    '      <button class="nura-lang-btn" data-lang="en">EN</button>',
    '    </div>',
    '    <div class="nura-header-info">',
    '      <h3 id="nura-header-title">NURA</h3>',
    '      <span id="nura-header-status"><span class="nura-online-dot"></span> متصل الآن</span>',
    '    </div>',
    '    <div class="nura-avatar">NU</div>',
    '  </div>',
    '  <div id="nura-messages" aria-live="polite" aria-relevant="additions text"></div>',
    '  <div id="nura-typing"><span></span><span></span><span></span></div>',
    '  <div id="nura-tree-panel"></div>',
    '  <div class="nura-chat-footer">',
    '    <button id="nura-send-btn" aria-label="إرسال" disabled>',
    '      <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>',
    '    </button>',
    '    <textarea id="nura-msg-input" rows="1" placeholder="اكتب رسالتك هنا…" maxlength="500"></textarea>',
    '    <button id="nura-attach-btn" type="button" title="إرفاق صورة أو ملف">📎</button>',
    '    <input type="file" id="nura-file-input" accept="image/*,.pdf" style="display:none">',
    '  </div>',
    '</div>',
  ].join('\n');
  if (shadowRoot) {
    shadowRoot.appendChild(root);
    document.body.appendChild(host);
  } else {
    document.body.appendChild(root);
  }

  // ── UI strings per language ────────────────────────────────────────────────
  var UI = {
    ar: {
      dir: 'rtl', htmlLang: 'ar',
      headerTitle: 'NURA', headerStatus: 'متصل الآن',
      placeholder: 'اكتب رسالتك هنا…',
      sendAriaLabel: 'إرسال', closeAriaLabel: 'إغلاق',
      welcome: 'أهلاً بك في دعم Rcell الرقمي.\nاختر خدمة من القائمة أو اكتب سؤالك مباشرة.',
      followUpMarker: 'هل يمكنني مساعدتك بشيء آخر؟',
      yesBtn: 'نعم، لدي سؤال آخر', noBtn: 'لا، شكراً',
      yesReply: 'بالتأكيد! اختر موضوعاً أو اكتب سؤالك.',
      noReply: 'العفو! يسعدنا دائماً خدمتك.\nإذا احتجت أي مساعدة مستقبلاً، نحن هنا لك!',
      noUserText: 'لا، شكراً', errorPrefix: 'تعذر الاتصال بالخادم',
      escalatingBanner: '⏳ جاري التواصل مع موظف بشري…',
      agentConnectedBanner: '✅ موظف بشري متصل الآن', agentLabel: 'موظف',
      sessionClosed: '🔒 تم إغلاق هذه الجلسة. شكراً لتواصلك معنا.',
      ratePrompt: 'كيف تقيّم تجربتك مع خدمة العملاء؟',
      rateThanks: 'شكراً على تقييمك! نسعى دائماً للتحسين.',
      treeRoot: 'كيف يمكنني مساعدتك؟', treeBack: '← رجوع', treeHome: '🏠 الرئيسية',
      talkToAgent: '🎧 التحدث مع موظف',
      suggestionTitle: 'الشكاوى والاقتراحات',
      suggestionIntro: 'هذا القسم مخصص للملاحظات العامة، التوصيات، الشكاوى، أو الاقتراحات. اكتب رسالتك هنا وسنرسلها مباشرة إلى قسم الاقتراحات في نظام المتابعة.',
      suggestionPlaceholder: 'اكتب الشكوى أو الاقتراح هنا…',
      suggestionSubmit: 'إرسال إلى قسم الاقتراحات',
      suggestionCancel: 'إلغاء',
      suggestionMin: 'يرجى كتابة 5 أحرف على الأقل.',
      suggestionSending: 'جارٍ الإرسال…',
      suggestionThanks: 'شكراً لك. تم إرسال ملاحظتك إلى فريقنا وسيتم مراجعتها ضمن قسم الاقتراحات.',
      suggestionCase: 'رقم المتابعة',
      attachFirstMessage: '⚠️ اكتب رسالة أولاً قبل إرفاق ملف.',
    },
    ku: {
      dir: 'ltr', htmlLang: 'ku',
      headerTitle: 'NURA', headerStatus: 'Niha ve ye',
      placeholder: 'Peyama xwe binivîse…',
      sendAriaLabel: 'Bişîne', closeAriaLabel: 'Bigire',
      welcome: 'Xêr hatî bo piştgiriya dijîtal a Rcell.\nXizmetekê hilbijêre an pirsa xwe rasterast binivîse.',
      followUpMarker: 'Dikarim di tiştekî din de jî alîkariya te bikim?',
      yesBtn: 'Erê, pirseke min heye', noBtn: 'Na, spas',
      yesReply: 'Bêguman! Mijarekê hilbijêre an pirsê binivîse.',
      noReply: 'Xêr be! Her tim kêfa me tê ku alîkariya te bikin.\nEger pêdiviya te bi alîkariyê hebe, em li vir in!',
      noUserText: 'Na, spas', errorPrefix: 'Nexşeya serverê nehat',
      escalatingBanner: '⏳ Wekîlek mirovî têkilî te dide…',
      agentConnectedBanner: '✅ Wekîlek mirovî niha ve ye', agentLabel: 'Wekîl',
      sessionClosed: '🔒 Ev rûniştgeha hate girtin. Spas ji bo têkiliya we.',
      ratePrompt: 'Hûn xizmetguzariya xerîdar çawa dinirxînin?',
      rateThanks: 'Spas ji bo nirxandina te! Em her tim hewl didin baştir bibin.',
      treeRoot: 'Çawa dikarim alîkariya te bikim?', treeBack: '← Vegerîn', treeHome: '🏠 Serxane',
      talkToAgent: '🎧 Bi karmend re biaxive',
      suggestionTitle: 'Gilî û pêşniyar',
      suggestionIntro: 'Ev beş ji bo têbînî, pêşniyar, gilî, an ramanên giştî ye. Peyama xwe binivîse û em ê wê rasterast bişînin beşa pêşniyaran di pergala me de.',
      suggestionPlaceholder: 'Gilî an pêşniyara xwe li vir binivîse…',
      suggestionSubmit: 'Bişîne beşa pêşniyaran',
      suggestionCancel: 'Betal bike',
      suggestionMin: 'Ji kerema xwe herî kêm 5 tîpan binivîse.',
      suggestionSending: 'Tê şandin…',
      suggestionThanks: 'Spas. Peyama te hate şandin û dê ji aliyê tîma me ve were nirxandin.',
      suggestionCase: 'Hejmara şopandinê',
      attachFirstMessage: '⚠️ Ji kerema xwe berî pêvekirina pelê peyamek binivîse.',
    },
    en: {
      dir: 'ltr', htmlLang: 'en',
      headerTitle: 'NURA', headerStatus: 'Online now',
      placeholder: 'Type your message here...',
      sendAriaLabel: 'Send', closeAriaLabel: 'Close',
      welcome: 'Welcome to Rcell digital support.\nChoose a service from the menu or type your question directly.',
      followUpMarker: 'Can I help you with anything else?',
      yesBtn: 'Yes, I have another question', noBtn: 'No, thank you',
      yesReply: 'Of course. Choose a topic or type your question.',
      noReply: 'You are welcome. We are always happy to help.\nIf you need support later, we are here for you.',
      noUserText: 'No, thank you', errorPrefix: 'Could not connect to the server',
      escalatingBanner: '⏳ Connecting you with a human agent...',
      agentConnectedBanner: '✅ A human agent is online now', agentLabel: 'Agent',
      sessionClosed: '🔒 This session has been closed. Thank you for contacting us.',
      ratePrompt: 'How would you rate your customer support experience?',
      rateThanks: 'Thank you for your rating. We are always working to improve.',
      treeRoot: 'How can I help you?', treeBack: '← Back', treeHome: '🏠 Home',
      talkToAgent: '🎧 Talk to an agent',
      suggestionTitle: 'Complaints and Suggestions',
      suggestionIntro: 'This section is for general feedback, recommendations, complaints, or suggestions. Write your message here and we will send it directly to the suggestions section in our follow-up system.',
      suggestionPlaceholder: 'Write your complaint or suggestion here...',
      suggestionSubmit: 'Send to Suggestions',
      suggestionCancel: 'Cancel',
      suggestionMin: 'Please write at least 5 characters.',
      suggestionSending: 'Sending...',
      suggestionThanks: 'Thank you. Your feedback has been sent to our team and will be reviewed in the suggestions section.',
      suggestionCase: 'Tracking number',
      attachFirstMessage: '⚠️ Please send a message before attaching a file.',
    },
  };

  // ── Articles (Arabic) ──────────────────────────────────────────────────────
  var ARTICLES = {
    0: 'لتحميل تطبيق الرعاية الذاتية Self-Care:\n\nاندرويد:\n• Google Play: https://play.google.com/store/apps/details?id=com.rcell.selfcareApp\n• Apkpure: https://apkpure.com/ar/rcell-selfcare/com.rcell.selfcareApp\n\niOS:\n• https://apps.apple.com/us/app/rselfcare/id6473144133\n\nأو زيارة: https://rcell.me/vas/selfcare',
    1: 'في حال واجهتم مشكلة في الوصول لموقع الرعاية الذاتية:\n• تأكد من تحديث المتصفح لآخر إصدار.\n• أو تفريغ سجل المتصفح: الإعدادات > مسح سجل التصفح.',
    2: 'لتفعيل الرمز السري PIN من تطبيق الرعاية الذاتية:\nالإعدادات > تفعيل الرمز السري PIN > اختر رمزاً خاصاً بك > أدخل كلمة المرور > اضغط "تفعيل الرمز السري PIN"',
    3: 'خطوات التحقق من الاتصال:\n١. تحقق من تمكين بيانات الجوال.\n٢. تأكد من صحة إعدادات APN.\n٣. تأكد من ضبط وضع الشبكة (4G أو 3G) بشكل صحيح.\n٤. تأكد من وجود باقة إنترنت نشطة.\n٥. تحقق من عدم الوصول إلى حد البيانات.\n\nإعدادات APN:\n• اندرويد: الإعدادات > الاتصالات > شبكات الهاتف المحمول > أسماء نقاط الوصول\n• iOS: الإعدادات > الخلوي > شبكة الجوال > APN',
    4: 'لإرسال النقاط من تطبيق الرعاية الذاتية:\naضغط "إرسال" ← أدخل رقم المستقبل ← أدخل كمية النقاط ← اضغط "إرسال"',
    5: 'لتحميل تطبيق حكي:\n\nاندرويد:\n• Google Play: https://play.google.com/store/apps/details?id=com.rcell.app\n• Apkpure: https://apkpure.com/ar/hakki/com.rcell.app\n\niOS:\n• https://apps.apple.com/us/app/hakki/id6449400694\n\nأو زيارة: https://rcell.me/vas/hakki',
    6: 'لحل مشكلة بطء الإنترنت، اتبع الخطوات بالترتيب:\n\n١. أغلق جميع التطبيقات في الخلفية.\n٢. أوقف تشغيل VPN.\n٣. أوقف تشغيل نقطة الاتصال.\n٤. تأكد من استخدام شريحة Rcell وتعطيل الشرائح الأخرى.\n٥. شغّل وضع الطائرة ثم أوقفه.\n٦. أعد تشغيل الجهاز.\n٧. حدّث نظام التشغيل.\n٨. أجرِ اختبار السرعة على fast.com وتحقق من التحسن.\n٩. إن استمرت المشكلة، غيّر موقعك وحاول مجدداً.\n١٠. إن لم يتحسن الأمر، يرجى رفع تذكرة شكوى.',
    7: 'HD Call (VoLTE) هي تقنية المكالمات الصوتية بتقنية LTE.\nتتيح إجراء مكالمات عبر شبكة 4G-LTE بدلاً من شبكات 2G أو 3G القديمة.',
    8: 'مميزات HD Call (VoLTE):\n• جودة صوت أعلى: أوضح وأنقى.\n• اتصال أسرع: توصيل المكالمات بشكل أسرع.\n• البيانات + الصوت معاً: تصفح الإنترنت أثناء المكالمة دون التبديل إلى 3G.',
    9: 'للتحقق من دعم هاتفك لـ HD Call:\n• في إعدادات الهاتف: ابحث عن "VoLTE" أو "4G Calling" في إعدادات الشبكة.\n• مواصفات الجهاز: تحقق في دليل هاتفك أو عبر الإنترنت.\n• أو تواصل مع شركة الاتصالات مباشرةً.',
    10: 'لتفعيل HD Call (VoLTE):\n\nاندرويد:\n١. الإعدادات > الاتصالات > شبكات الهاتف المحمول\n٢. فعّل "مكالمات VoLTE" أو "مكالمات 4G"\n\nآيفون:\n١. الإعدادات > خلوي > خيارات البيانات الخلوية\n٢. اختر "تمكين LTE" > "الصوت والبيانات"',
    11: 'بعد تشغيل HD Call، ما عليك سوى الاتصال كالمعتاد.\nسيستخدم هاتفك تقنية LTE تلقائياً إذا كانت الشبكة ومنطقتك تدعمها.',
    12: 'استكشاف أخطاء HD Call (VoLTE):\n\n١. أعد تشغيل هاتفك.\n٢. تحقق من توفر 4G/LTE في منطقتك.\n٣. ابحث عن أي انقطاع معلن من شركة الاتصالات.\n٤. شغّل وضع الطائرة ثم أوقفه.\n٥. أعد ضبط إعدادات الشبكة:\n   • اندرويد: الإعدادات > النظام > إعادة ضبط > إعادة ضبط إعدادات الشبكة\n   • آيفون: الإعدادات > عام > إعادة تعيين > إعادة ضبط إعدادات الشبكة\n٦. تحقق من إعدادات APN.\n٧. جرّب شريحة SIM في جهاز آخر.',
    13: 'إذا كنت تواجه مشكلة في تسجيل الدخول إلى تطبيق الرعاية الذاتية:\n\n• حدّث التطبيق والمتصفح لآخر إصدار.\n• عطّل VPN إن كنت تستخدمه.\n• جرّب إصدار الويب: https://my.rcell.me/\n\nإذا استمرت المشكلة، تواصل مع فريق الدعم.',
    14: 'لتغيير كلمة المرور عبر التطبيق:\n\n١. افتح الواجهة الرئيسية للتطبيق.\n٢. اضغط على زر الخيارات من أعلى الشاشة.\n٣. اختر "تغيير كلمة المرور".\n٤. أدخل كلمة مرور جديدة (أرقام وحروف).\n٥. اضغط "تأكيد".\n\nلا تحتاج للتواصل مع الدعم الفني لتغيير كلمة المرور.',
    16: 'تفاصيل الباقات والأسعار:\n\n• الشمس:    1 GB  يومياً     = 4,500 ل.س   (3 نقاط)\n• بلوتو:    3 GB  أسبوعياً   = 10,500 ل.س  (7 نقاط)\n• الأرض:    9 GB  شهرياً     = 25,000 ل.س  (16 نقطة)\n• القمر:    5 GB  شهرياً     = 20,000 ل.س  (11 نقطة)\n• المريخ:   20 GB شهرياً     = 55,000 ل.س  (36 نقطة)\n• الكواكب:  40 GB شهرياً     = 100,000 ل.س (66 نقطة)\n\nالنقطة الواحدة = 1,500 ليرة سورية',
    17: 'ساعات العمل:\n• السبت: 8:00 ص – 4:00 م\n• الأحد – الخميس: 8:00 ص – 10:00 م\n• الجمعة: عطلة رسمية',
    18: 'شرائح SIM متوفرة الآن.\nيمكنك شراؤها من مراكزنا ونقاط البيع المعتمدة في مدينتك بسعر 75,000 ليرة سورية.',
    19: 'لاستعادة كلمة المرور:\nالإعدادات > تعديل الملف الشخصي > اضغط "الاستعادة هنا"',
    20: 'منصة آنا (Ana) — حساب واحد لجميع تطبيقات Rcell\n\nمنصة آنا هي نظام تسجيل دخول موحد يتيح الدخول إلى جميع تطبيقات Rcell بحساب واحد.\n\nالتطبيقات المدعومة:\n• تطبيق Self-Care (رائد)\n• تطبيق حكي\n• تطبيقات Rcell القادمة\n\nرابط المنصة: ana.rcell.me\nمتاح على: الويب وAndroid',
    21: 'إعدادات APN الصحيحة لشبكة Rcell:\n\nاحذف جميع إعدادات APN الحالية ثم أضف إعداداً جديداً:\n• الاسم: internet\n• APN: internet\n• نوع الشبكة: LTE\n• النوع: default\n\nخطوات على اندرويد:\nالإعدادات ← الاتصالات ← شبكات الهاتف المحمول ← أسماء نقاط الوصول ← أضف جديد\n\nخطوات على iOS:\nالإعدادات ← الخلوي ← شبكة الجوال ← APN\n\nبعد الإضافة، أعد تشغيل الجهاز أو شغّل وضع الطائرة 30 ثانية ثم أوقفه.',
    22: 'إذا كان رصيد الإنترنت ينتهي بسرعة:\n\n١. عطّل التحديثات التلقائية للتطبيقات.\n٢. تحقق من استهلاك كل تطبيق: الإعدادات ← الاتصالات ← استخدام البيانات.\n٣. أوقف تحديثات الخلفية.\n٤. إذا استمرت المشكلة، تواصل مع فريق الدعم لفحص الحساب.',
    23: 'إذا كانت بطاقة SIM مقفلة وتطلب رمز PUK:\n\n⚠️ تحذير: إدخال PUK خاطئ 10 مرات يعطّل الشريحة نهائياً — لا تخمّن.\n\nللحصول على رمز PUK:\n• تواصل مع فريق دعم Rcell مباشرةً.\n• أو زر أقرب مركز خدمة Rcell مع هوية شخصية.',
    24: 'شريحة eSIM الرقمية من Rcell\n\neSIM هي شريحة SIM رقمية مدمجة في الجهاز تغنيك عن الشريحة الفيزيائية.\n\nللاستفسار عن توفر eSIM أو تفعيلها:\nزر أقرب مركز خدمة Rcell أو تواصل مع فريق الدعم.',
    25: 'شبكة الجيل الخامس 5G — قريباً من Rcell\n\nRcell في المراحل النهائية لإطلاق شبكة 5G في سوريا.\nسيتم الإعلان عن موعد الإطلاق الرسمي قريباً.',
    26: 'أرقام وحقائق شركة Rcell:\n\n• أبراج التغطية: أكثر من 1,000 برج\n• المناطق المغطاة: أكثر من 40 منطقة في سوريا\n• عدد المشتركين: أكثر من 1.1 مليون مشترك\n• مراكز خدمة العملاء: أكثر من 11 مركز\n• نقاط البيع المعتمدة: أكثر من 2,000 نقطة\n\nللعثور على أقرب مركز: www.rcell.me',
    27: 'خدمة إنترنت الأعمال من Rcell\n\nFTTx — الألياف الضوئية للأعمال وحزم شرائح 4G متعددة للشركات.\n\nللاستفسار: www.rcell.me',
    28: 'استخدام تطبيق حكي مجاناً في حالات الطوارئ\n\nتطبيق حكي يتيح التواصل مجاناً حتى بعد انتهاء رصيدك!\n\nللاستفادة:\n١. حمّل تطبيق حكي.\n٢. سجّل الدخول باستخدام حساب آنا.\n٣. استخدم التطبيق للتواصل بشكل مجاني.',
    29: 'إذا كانت بطاقة الشحن محكوكة أو تالفة:\n\nتواصل مع فريق دعم Rcell وأرسل صورة واضحة للبطاقة من الوجهين.\nسيراجع الفريق التقني البطاقة ويرسل الرمز إن أمكن.',
  };

  // ── Articles (Kurdish) ─────────────────────────────────────────────────────
  var ARTICLES_KU = {
    0: 'Ji bo daxistina sepana Self-Care:\n\nAndroid:\n• Google Play: https://play.google.com/store/apps/details?id=com.rcell.selfcareApp\n\niOS:\n• https://apps.apple.com/us/app/rselfcare/id6473144133\n\nAn jî: https://rcell.me/vas/selfcare',
    1: 'Ger di gihîştina malpera Self-Care de pirsgirêkek we hebe:\n• Piştrast bin ku geroka we li ser guhertoya herî dawî ye.\n• An jî dîroka gerokê paqij bikin.',
    2: 'Ji sepana Self-Care: Mîheng > Çalakirina koda PIN > Kodek taybet hilbijêrin > Şîfreya xwe têkevin > "Çalakirina koda PIN" bikirtînin.',
    3: 'Gavên kontrolkirina têkiliyê:\n1. Piştrast bin ku daneya mobîl çalak e.\n2. Mîhengên APN rast bin.\n3. Rewşa tora mobîl rast be (4G, 3G).\n4. Pakêtek înternetê ya çalak heye.\n5. Sînorê daneyê nehatiye temamkirin.',
    4: '"Şandin" bikirtînin ← hejmara wergir binivîsin ← hejmara xalan binivîsin ← "Bişîne" bikirtînin',
    5: 'Ji bo daxistina sepana Hakki:\n\nAndroid:\n• Google Play: https://play.google.com/store/apps/details?id=com.rcell.app\n\niOS:\n• https://apps.apple.com/us/app/hakki/id6449400694\n\nAn jî: https://rcell.me/vas/hakki',
    6: 'Ji bo çareserkirina hêdîbûna înternetê:\n1. Hemî sepanên li paşplanê bigirin.\n2. VPN bigirin.\n3. Hotspot bigirin.\n4. SIM-karta Rcell bikar bînin.\n5. Moda balafirê vekin û bigirin.\n6. Amûrê ji nû ve bidin destpêkirin.\n7. Testek leza înternetê bi rêya fast.com bikin.',
    7: 'HD Call (VoLTE) dihêle hûn bangên xwe bi rêya tora 4G-LTE bikin.',
    8: 'Taybetmendiyên HD Call:\n• Kalîteya dengê baştir.\n• Sazkirina bilez a bangê.\n• Daneyên û deng di heman demê de.',
    9: 'Di mîhengên têlefonê de li "VoLTE" an "4G Calling" bigerin.',
    10: 'Ji bo çalakirina HD Call (VoLTE):\n\nAndroid: Mîheng > Têkilî > Torên mobîl > Veguherînin bangên VoLTE\n\niPhone: Mîheng > Têkilî > Vebijêrkên daneya mobîl > LTE > Deng û Dane',
    11: 'Piştî çalakirinê, tenê bangên xwe bikin. Têlefona we dê bixweber LTE bikar bîne.',
    12: 'Çareserkirina pirsgirêkên HD Call:\n1. Têlefona xwe ji nû ve bidin destpêkirin.\n2. Piştrast bin ku 4G/LTE li devera we heye.\n3. Moda balafirê biguherînin.\n4. Mîhengên torê resetbikin.',
    13: 'Ger di ketina Self-Care de pirsgirêkê dikişînin:\n• Sepan û gerokê nûjen bikin.\n• VPN bigirin.\n• Guhertoya Webê biceribînin: https://my.rcell.me/',
    14: 'Ji bo guhertina şîfreyê:\n1. Rûyê sereke vekin.\n2. Bişkojka vebijêrkan bikirtînin.\n3. "Guhertina şîfreyê" hilbijêrin.\n4. Şîfreyek nû binivîsin.\n5. "Pejirandin" bikirtînin.',
    16: 'Agahiyên pakêt û bihayê:\n• Roj: 1 GB rojane = 4,500 L.S (3 xal)\n• Pluto: 3 GB heftane = 10,500 L.S (7 xal)\n• Erd: 9 GB mehane = 25,000 L.S (16 xal)\n• Heyv: 5 GB mehane = 20,000 L.S (11 xal)\n• Merîx: 20 GB mehane = 55,000 L.S (36 xal)\n• Gerstêrk: 40 GB mehane = 100,000 L.S (66 xal)',
    17: 'Demjimêrên kar:\n• Şemî: 8:00 – 16:00\n• Yekşem – Pêncşem: 8:00 – 22:00\n• În: Betlane',
    18: 'SIM kart niha peyda dibin bi 75,000 Lîreyên Sûriyê.',
    19: 'Mîheng > Guhertina profîlê > "Vegera li vir" bikirtînin',
    20: 'Platforma Ana — Hesabek ji bo hemî sepanên Rcell.\nLînk: ana.rcell.me',
    21: 'Mîhengên APN yên rast:\n• Nav: internet\n• APN: internet\n• Cureya torê: LTE\n• Cure: default\n\nAndroid: Mîheng ← Têkilî ← Torên mobîl ← APN\niOS: Mîheng ← Têkilî ← APN',
    22: 'Ger balansê înternetê zû biqede:\n1. Nûjenkirinên otomatîk bigirin.\n2. Bikaranîna her sepanê kontrol bikin.\n3. Nûjenkirinên paşplanê bigirin.',
    23: 'Ger SIM kilît bûye û PUK dixwaze:\n⚠️ Texmîn nekin — 10 xeta şaş SIM-ê diqetîne.\nBi tîmê piştgiriya Rcell re têkilî daynin.',
    24: 'eSIM ya dîjîtal ji Rcell peyda dibe.\nBi tîmê piştgiriyê re têkilî daynin.',
    25: 'Tora 5G — Zû tê ji Rcell.\nDîroka destpêkirinê dê di demek nêzîk de were ragihandin.',
    26: 'Hejmar û rastiyên Rcell:\n• Zêdetirî 1,000 birc\n• Zêdetirî 40 dever li Sûriyê\n• Zêdetirî 1.1 mîlyon abone\n• Zêdetirî 11 navend\n\nwww.rcell.me',
    27: 'Înterneta karsaziyê ji Rcell (FTTx û 4G).\nBi tîmê firotanê re têkilî daynin: www.rcell.me',
    28: 'Sepana Hakki dihêle hûn belaş têkilî daynin tewra piştî ku balansê we qediya.',
    29: 'Ger karta şarjê hatibe xerabkirin:\nBi tîmê piştgiriyê re têkilî daynin û wêneyek zelal a kartê bişînin.',
  };

  // ── Articles (English) ─────────────────────────────────────────────────────
  var ARTICLES_EN = {
    0: 'To download the Self-Care app:\n\nAndroid:\n• Google Play: https://play.google.com/store/apps/details?id=com.rcell.selfcareApp\n• Apkpure: https://apkpure.com/ar/rcell-selfcare/com.rcell.selfcareApp\n\niOS:\n• https://apps.apple.com/us/app/rselfcare/id6473144133\n\nOr visit: https://rcell.me/vas/selfcare',
    1: 'If you cannot access the Self-Care website:\n• Make sure your browser is updated to the latest version.\n• Or clear your browser history/cache from browser settings.',
    2: 'To activate the PIN code from the Self-Care app:\nSettings > Activate PIN code > Choose your private PIN > Enter your password > Tap "Activate PIN code".',
    3: 'Connection checklist:\n1. Make sure Mobile Data is enabled.\n2. Check that the APN settings are correct.\n3. Make sure the network mode is set correctly, such as 4G or 3G.\n4. Make sure you have an active internet package.\n5. Check that you have not reached your data limit.\n\nAPN settings:\n• Android: Settings > Connections > Mobile Networks > Access Point Names\n• iOS: Settings > Cellular > Cellular Data Network > APN',
    4: 'To send points from the Self-Care app:\nTap "Send" > Enter the recipient number > Enter the number of points > Tap "Send".',
    5: 'To download the Hakki app:\n\nAndroid:\n• Google Play: https://play.google.com/store/apps/details?id=com.rcell.app\n• Apkpure: https://apkpure.com/ar/hakki/com.rcell.app\n\niOS:\n• https://apps.apple.com/us/app/hakki/id6449400694\n\nOr visit: https://rcell.me/vas/hakki',
    6: 'To fix slow internet, follow these steps in order:\n\n1. Close all background apps.\n2. Turn off VPN.\n3. Turn off hotspot.\n4. Make sure you are using the Rcell SIM and disable other SIM cards.\n5. Turn Airplane Mode on, then off.\n6. Restart your device.\n7. Update the operating system.\n8. Run a speed test on fast.com and check if it improves.\n9. If the issue continues, change your location and try again.\n10. If it still does not improve, please submit a complaint ticket.',
    7: 'HD Call, also known as VoLTE, is voice calling over LTE. It lets calls run over the 4G-LTE network instead of older 2G or 3G networks.',
    8: 'HD Call (VoLTE) benefits:\n• Better voice quality: clearer and cleaner audio.\n• Faster call setup: calls connect more quickly.\n• Data + voice together: use the internet during a call without switching to 3G.',
    9: 'To check whether your phone supports HD Call:\n• In phone settings, search for "VoLTE" or "4G Calling" under network settings.\n• Check your device specifications or phone manual.\n• Or contact the telecom provider directly.',
    10: 'To activate HD Call (VoLTE):\n\nAndroid:\n1. Settings > Connections > Mobile Networks\n2. Enable "VoLTE calls" or "4G Calling"\n\niPhone:\n1. Settings > Cellular > Cellular Data Options\n2. Choose "Enable LTE" > "Voice & Data".',
    11: 'After enabling HD Call, make calls as usual. Your phone will automatically use LTE if the network and your area support it.',
    12: 'HD Call (VoLTE) troubleshooting:\n\n1. Restart your phone.\n2. Check that 4G/LTE is available in your area.\n3. Check for any announced network outage.\n4. Turn Airplane Mode on, then off.\n5. Reset network settings:\n   • Android: Settings > System > Reset > Reset network settings\n   • iPhone: Settings > General > Reset > Reset Network Settings\n6. Check APN settings.\n7. Try the SIM card in another device.',
    13: 'If you are having trouble logging in to the Self-Care app:\n\n• Update the app and browser to the latest version.\n• Turn off VPN if you are using one.\n• Try the web version: https://my.rcell.me/\n\nIf the issue continues, contact support.',
    14: 'To change your password in the app:\n\n1. Open the app home screen.\n2. Tap the options button at the top.\n3. Choose "Change password".\n4. Enter a new password with letters and numbers.\n5. Tap "Confirm".\n\nYou do not need to contact technical support to change your password.',
    16: 'Package details and prices:\n\n• Sun: 1 GB daily = 4,500 SYP (3 points)\n• Pluto: 3 GB weekly = 10,500 SYP (7 points)\n• Earth: 9 GB monthly = 25,000 SYP (16 points)\n• Moon: 5 GB monthly = 20,000 SYP (11 points)\n• Mars: 20 GB monthly = 55,000 SYP (36 points)\n• Planets: 40 GB monthly = 100,000 SYP (66 points)\n\n1 point = 1,500 Syrian pounds',
    17: 'Working hours:\n• Saturday: 8:00 AM - 4:00 PM\n• Sunday - Thursday: 8:00 AM - 10:00 PM\n• Friday: Official holiday',
    18: 'SIM cards are currently available.\nYou can buy them from our centers and authorized points of sale in your city for 75,000 Syrian pounds.',
    19: 'To recover your password:\nSettings > Edit profile > Tap "Recover here".',
    20: 'Ana Platform — one account for all Rcell apps\n\nAna is a single sign-on platform that lets you access all Rcell apps with one account.\n\nSupported apps:\n• Self-Care app (Raid)\n• Hakki app\n• Future Rcell apps\n\nPlatform link: ana.rcell.me\nAvailable on: Web and Android',
    21: 'Correct APN settings for Rcell:\n\nDelete all current APN settings, then add a new one:\n• Name: internet\n• APN: internet\n• Network type: LTE\n• Type: default\n\nAndroid steps:\nSettings > Connections > Mobile Networks > Access Point Names > Add new\n\niOS steps:\nSettings > Cellular > Cellular Data Network > APN\n\nAfter adding it, restart the device or turn Airplane Mode on for 30 seconds, then turn it off.',
    22: 'If your internet balance finishes quickly:\n\n1. Disable automatic app updates.\n2. Check usage by app: Settings > Connections > Data Usage.\n3. Turn off background refresh/background data.\n4. If the issue continues, contact support to check the account.',
    23: 'If your SIM card is locked and asks for a PUK code:\n\n⚠️ Warning: entering the wrong PUK 10 times permanently disables the SIM. Do not guess.\n\nTo get the PUK code:\n• Contact Rcell support directly.\n• Or visit the nearest Rcell service center with your ID.',
    24: 'Rcell digital eSIM\n\neSIM is a digital SIM built into the device and does not require a physical SIM card.\n\nTo ask about availability or activation:\nVisit the nearest Rcell service center or contact support.',
    25: '5G network — coming soon from Rcell\n\nRcell is in the final stages of launching 5G in Syria.\nThe official launch date will be announced soon.',
    26: 'Rcell numbers and facts:\n\n• Coverage towers: more than 1,000 towers\n• Covered areas: more than 40 areas in Syria\n• Subscribers: more than 1.1 million subscribers\n• Customer service centers: more than 11 centers\n• Authorized points of sale: more than 2,000 points\n\nTo find the nearest center: www.rcell.me',
    27: 'Rcell business internet\n\nFTTx fiber for businesses and multi-SIM 4G packages for companies.\n\nFor inquiries: www.rcell.me',
    28: 'Using the Hakki app for free in emergencies\n\nThe Hakki app lets you communicate for free even after your balance runs out.\n\nTo use it:\n1. Download the Hakki app.\n2. Sign in with your Ana account.\n3. Use the app to communicate for free.',
    29: 'If your recharge card is scratched or damaged:\n\nContact Rcell support and send a clear photo of both sides of the card.\nThe technical team will review the card and send the code if possible.',
  };

  // ── Topic tree ─────────────────────────────────────────────────────────────
  var TOPIC_LABELS_KU = {
    root: 'Çawa dikarim alîkariya te bikim?',
    apps: '📱 Aplikasyon',
    selfcare: 'Apî Self-Care',
    sc_dl: 'Daxistina aplikasyonê',
    sc_login: 'Pirsgirêka têketinê',
    sc_access: 'Nikarin gihîjin malperê',
    hakki: 'Apî Hakki',
    hk_dl: 'Daxistina aplikasyonê',
    hk_sos: 'Bikaranîna belaş a acil',
    ana: 'Platforma Ana',
    internet: '🌐 Înternetê û Pêwendî',
    slow: 'Înternetê hêdî ye',
    noconn: 'Pêwendî tune',
    apn: 'Mîhengên APN',
    fiveg: '5G - nêzîk e',
    hdcall: 'HD Call (VoLTE)',
    hd_what: 'HD Call çi ye?',
    hd_why: 'Taybetmendiyên wê',
    hd_sup: 'Têlefona min piştgirî dide?',
    hd_act: 'Çawa çalak bikim?',
    hd_use: 'Çawa bikar bînim?',
    hd_fix: 'Pirsgirêka HD Call',
    account: '🔐 Hesab û Ewlekarî',
    password: 'Şîfre',
    pw_change: 'Guherandina şîfreyê',
    pw_recover: 'Şîfreya min ji bîra min çû',
    pin: 'Koda PIN',
    login_prob: 'Pirsgirêka têketinê',
    puk: 'SIM kilêrkirî / PUK',
    packages: '📦 Pakêt û Xizmetguzarî',
    pkg_prices: 'Bihayên pakêtan',
    sim: 'Karta SIM',
    esim: 'eSIM Dijîtal',
    points: 'Şandina xalan',
    fastdata: 'Balans zû diqede',
    scratchcard: 'Karta şarjê xerabûye',
    info: 'ℹ️ Agahiyên Giştî',
    hours: 'Demjimêrên xebatê',
    coverage: 'Nixumandin û navendên pargîdaniyê',
    business: 'Înterneta karsaziyê FTTx',
    other: '🔗 Yên Din',
    other_complaint: 'Pêşkêşkirina gilî an pêşniyar',
    other_agent: '🎧 Rasterast bi karmend re biaxive',
  };
  var TOPIC_LABELS_EN = {
    root: 'How can I help you?',
    apps: '📱 Apps',
    selfcare: 'Self-Care App',
    sc_dl: 'Download the app',
    sc_login: 'Login problem',
    sc_access: 'Cannot access the website',
    hakki: 'Hakki App',
    hk_dl: 'Download the app',
    hk_sos: 'Free emergency use',
    ana: 'Ana Platform',
    internet: '🌐 Internet and Connectivity',
    slow: 'Slow internet',
    noconn: 'No connection',
    apn: 'APN settings',
    fiveg: '5G - Coming soon',
    hdcall: 'HD Call (VoLTE)',
    hd_what: 'What is HD Call?',
    hd_why: 'Benefits',
    hd_sup: 'Does my phone support it?',
    hd_act: 'How do I activate it?',
    hd_use: 'How do I use it?',
    hd_fix: 'HD Call issue',
    account: '🔐 Account and Security',
    password: 'Password',
    pw_change: 'Change password',
    pw_recover: 'Forgot password',
    pin: 'PIN code',
    login_prob: 'Login problem',
    puk: 'Locked SIM / PUK code',
    packages: '📦 Packages and Services',
    pkg_prices: 'Package prices',
    sim: 'SIM card',
    esim: 'Digital eSIM',
    points: 'Send points',
    fastdata: 'Balance ends quickly',
    scratchcard: 'Scratched recharge card',
    info: 'ℹ️ General Information',
    hours: 'Working hours',
    coverage: 'Company coverage and centers',
    business: 'FTTx business internet',
    other: '🔗 Other',
    other_complaint: 'Submit a complaint or suggestion',
    other_agent: '🎧 Talk directly to an agent',
  };
  var TOPIC_TREE = { id: 'root', label: { ar: 'كيف يمكنني مساعدتك؟', ku: TOPIC_LABELS_KU.root, en: TOPIC_LABELS_EN.root }, children: [] };

  // ── State ──────────────────────────────────────────────────────────────────
  var currentLang        = 'ar';
  var sessionId          = null;
  var sessionToken       = null;
  var customerId         = 'widget-' + Math.random().toString(36).substr(2, 8);
  var isOpen             = false;
  var welcomed           = false;
  var isEscalated        = false;
  var isSessionClosed      = false;
  var escalationBannerEl   = null;
  var treeStack            = [];
  var agentEventSource     = null;
  var agentStreamStarting  = false;
  var typingDebounceTimer  = null;

  // ── DOM refs ───────────────────────────────────────────────────────────────
  var toggle       = root.querySelector('#chat-toggle');
  var win          = root.querySelector('#chat-window');
  var closeBtn     = root.querySelector('#nura-close-btn');
  var msgInput     = root.querySelector('#nura-msg-input');
  var sendBtn      = root.querySelector('#nura-send-btn');
  var attachBtn    = root.querySelector('#nura-attach-btn');
  var fileInput    = root.querySelector('#nura-file-input');
  var messagesEl   = root.querySelector('#nura-messages');
  var typingEl     = root.querySelector('#nura-typing');
  var badge        = root.querySelector('#nura-badge');
  var treePanel    = root.querySelector('#nura-tree-panel');
  var headerTitle  = root.querySelector('#nura-header-title');
  var headerStatus = root.querySelector('#nura-header-status');
  var langBtns     = root.querySelectorAll('.nura-lang-btn');
  var lastUserTickEl = null;
  var lastFocusedEl  = null;
  var pageScrollY = 0;
  var pageScrollLocked = false;
  var previousBodyStyles = {};
  var previousDocumentElementStyles = {};

  function updateViewportHeight() {
    var h = (window.visualViewport && window.visualViewport.height) || window.innerHeight || 720;
    root.style.setProperty('--nura-viewport-height', h + 'px');
    if (!isMobileViewport()) setTreeCollapsedForInput(false);
    setPageScrollLocked(isOpen);
    updateKeyboardSafeMode();
    if (isOpen) scrollBottom();
  }

  function isMobileViewport() {
    return window.matchMedia ? window.matchMedia('(max-width: 600px)').matches : window.innerWidth <= 600;
  }

  function setTreeCollapsedForInput(collapsed) {
    var shouldCollapse = collapsed && isMobileViewport();
    win.classList.toggle('nura-mobile-input-active', shouldCollapse);
    treePanel.setAttribute('aria-hidden', shouldCollapse ? 'true' : 'false');
    if ('inert' in treePanel) treePanel.inert = shouldCollapse;
    updateKeyboardSafeMode();
  }

  function updateKeyboardSafeMode() {
    var active = shadowRoot ? shadowRoot.activeElement : document.activeElement;
    var keyboardLikelyOpen = window.visualViewport
      ? window.visualViewport.height < window.innerHeight - 80
      : false;
    var shouldUseKeyboardHeight = isOpen && isMobileViewport() && active === msgInput && keyboardLikelyOpen;
    win.classList.toggle('nura-keyboard-active', shouldUseKeyboardHeight);
  }

  function setPageScrollLocked(locked) {
    var shouldLock = locked && isMobileViewport();
    if (shouldLock && !pageScrollLocked) {
      pageScrollY = window.scrollY || window.pageYOffset || 0;
      previousBodyStyles = {
        position: document.body.style.position,
        top: document.body.style.top,
        left: document.body.style.left,
        right: document.body.style.right,
        width: document.body.style.width,
        overflow: document.body.style.overflow,
        overscrollBehavior: document.body.style.overscrollBehavior,
      };
      previousDocumentElementStyles = {
        overflow: document.documentElement.style.overflow,
        overscrollBehavior: document.documentElement.style.overscrollBehavior,
      };
      document.documentElement.style.overflow = 'hidden';
      document.documentElement.style.overscrollBehavior = 'none';
      document.body.style.position = 'fixed';
      document.body.style.top = '-' + pageScrollY + 'px';
      document.body.style.left = '0';
      document.body.style.right = '0';
      document.body.style.width = '100%';
      document.body.style.overflow = 'hidden';
      document.body.style.overscrollBehavior = 'none';
      pageScrollLocked = true;
    } else if (!shouldLock && pageScrollLocked) {
      document.documentElement.style.overflow = previousDocumentElementStyles.overflow || '';
      document.documentElement.style.overscrollBehavior = previousDocumentElementStyles.overscrollBehavior || '';
      document.body.style.position = previousBodyStyles.position || '';
      document.body.style.top = previousBodyStyles.top || '';
      document.body.style.left = previousBodyStyles.left || '';
      document.body.style.right = previousBodyStyles.right || '';
      document.body.style.width = previousBodyStyles.width || '';
      document.body.style.overflow = previousBodyStyles.overflow || '';
      document.body.style.overscrollBehavior = previousBodyStyles.overscrollBehavior || '';
      window.scrollTo(0, pageScrollY);
      pageScrollLocked = false;
    }
  }

  updateViewportHeight();
  window.addEventListener('resize', updateViewportHeight, { passive: true });
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', updateViewportHeight, { passive: true });
    window.visualViewport.addEventListener('scroll', updateViewportHeight, { passive: true });
  }

  function focusableElements() {
    return Array.prototype.slice.call(root.querySelectorAll(
      'button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])'
    )).filter(function (el) {
      return !el.disabled && el.offsetParent !== null;
    });
  }

  function trapFocus(e) {
    if (!isOpen || e.key !== 'Tab') return;
    var items = focusableElements();
    if (!items.length) return;
    var first = items[0];
    var last = items[items.length - 1];
    var active = shadowRoot ? shadowRoot.activeElement : document.activeElement;
    if (e.shiftKey && active === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && active === last) {
      e.preventDefault();
      first.focus();
    }
  }

  // ── Tree helpers ───────────────────────────────────────────────────────────
  function treeLabel(node) {
    if (typeof node.label === 'string') return node.label;
    return node.label[currentLang] || node.label.ar;
  }
  function currentTreeNode() { return treeStack.length > 0 ? treeStack[treeStack.length - 1] : TOPIC_TREE; }
  function cleanTreeTitle(label) {
    return (label || '').replace(/^[^A-Za-z\u00C0-\u024F\u0600-\u06FF]+/, '').trim() || label;
  }
  function chooseServiceText() {
    if (currentLang === 'ar') return 'اختر الخدمة التي تحتاجها';
    if (currentLang === 'en') return 'Choose the service you need';
    return 'Xizmeta ku pêdiviya te pê heye hilbijêre';
  }

  function mergeSharedTopicLabels(sharedNode, localNode) {
    if (!sharedNode) return localNode;
    var merged = Object.assign({}, sharedNode);
    if (typeof sharedNode.label === 'string') {
      merged.label = {
        ar: sharedNode.label,
        ku: TOPIC_LABELS_KU[sharedNode.id] || (localNode && localNode.label && localNode.label.ku) || sharedNode.label,
        en: TOPIC_LABELS_EN[sharedNode.id] || (localNode && localNode.label && localNode.label.en) || sharedNode.label,
      };
    }
    var localChildrenById = {};
    ((localNode && localNode.children) || []).forEach(function (child) { localChildrenById[child.id] = child; });
    if (sharedNode.children) {
      merged.children = sharedNode.children.map(function (child) {
        return mergeSharedTopicLabels(child, localChildrenById[child.id]);
      });
    }
    return merged;
  }

  async function loadSharedTopicTree() {
    try {
      var res = await fetch(API_BASE + '/topic-tree');
      if (!res.ok) return;
      var shared = await res.json();
      TOPIC_TREE = mergeSharedTopicLabels(shared, TOPIC_TREE);
      treeStack = [];
      renderTree();
    } catch (e) {
      console.warn('topic tree load failed:', e);
    }
  }

  async function directToAgent() {
    if (isEscalated || isSessionClosed) return;
    try {
      var handoffHeaders = { 'Content-Type': 'application/json' };
      if (sessionToken) handoffHeaders['X-Session-Token'] = sessionToken;
      var handoffRes = await fetch(API_BASE + '/handoff/direct', {
        method: 'POST',
        headers: handoffHeaders,
        body: JSON.stringify({ session_id: sessionId, customer_id: customerId, channel: 'web', reason: 'direct_request' }),
      });
      if (!handoffRes.ok) throw new Error('Handoff failed: ' + handoffRes.status);
      var data = await handoffRes.json();
      sessionId = data.session_id;
      sessionToken = data.session_token || sessionToken;
      isEscalated = true;
      showEscalationBanner();
      startAgentStream();
    } catch (e) {
      console.warn('directToAgent failed:', e);
    }
  }

  function renderTree() {
    var t    = UI[currentLang];
    var node = currentTreeNode();
    treePanel.innerHTML = '';

    if (treeStack.length > 0) {
      var navBar = document.createElement('div');
      navBar.className = 'nura-tree-nav-bar';

      var backBtn = document.createElement('button');
      backBtn.className = 'nura-tree-nav-btn';
      backBtn.type = 'button';
      backBtn.title = t.treeBack;
      backBtn.setAttribute('aria-label', t.treeBack);
      backBtn.textContent = currentLang === 'ar' ? '›' : '‹';
      backBtn.addEventListener('click', function () {
        track('tree_back', treeLabel(treeStack[treeStack.length - 1]), '');
        treeStack.pop();
        renderTree();
      });
      navBar.appendChild(backBtn);

      var title = document.createElement('div');
      title.className = 'nura-tree-title';
      title.textContent = cleanTreeTitle(treeLabel(node));
      navBar.appendChild(title);

      if (treeStack.length > 1) {
        var homeBtn = document.createElement('button');
        homeBtn.className = 'nura-tree-nav-btn home';
        homeBtn.type = 'button';
        homeBtn.title = t.treeHome;
        homeBtn.setAttribute('aria-label', t.treeHome);
        homeBtn.textContent = '⌂';
        homeBtn.addEventListener('click', function () {
          track('tree_home', '', '');
          treeStack = [];
          renderTree();
        });
        navBar.appendChild(homeBtn);
      }

      treePanel.appendChild(navBar);
    }

    var q = document.createElement('div');
    q.className = 'nura-tree-level-q' + (treeStack.length > 0 ? ' sub' : '');
    q.textContent = treeStack.length > 0 ? chooseServiceText() : treeLabel(node);
    treePanel.appendChild(q);

    var optsDiv = document.createElement('div');
    optsDiv.className = 'nura-tree-options';

    (node.children || []).forEach(function (child) {
      var btn = document.createElement('button');
      btn.className = 'nura-tree-opt' + (child.children ? ' has-children' : '');
      btn.textContent = treeLabel(child);
      btn.addEventListener('click', function () {
        track('tree_click', treeLabel(child), child.id, { topic_id: child.id, article_id: child.article != null ? child.article : null });
        if (child.action === 'complaint') {
          track('suggestion_open', treeLabel(child), child.id);
          renderSuggestionForm(child);
        } else if (child.action === 'agent') {
          track('direct_to_agent', 'tree_option', child.id);
          directToAgent();
        } else if (child.article !== undefined) {
          handleLeaf(child);
        } else if (child.children) {
          treeStack.push(child);
          renderTree();
        }
      });
      optsDiv.appendChild(btn);
    });

    treePanel.appendChild(optsDiv);

  }

  function renderSuggestionForm(node) {
    var t = UI[currentLang];
    treePanel.innerHTML = '';

    var navBar = document.createElement('div');
    navBar.className = 'nura-tree-nav-bar';

    var backBtn = document.createElement('button');
    backBtn.className = 'nura-tree-nav-btn';
    backBtn.type = 'button';
    backBtn.title = t.treeBack;
    backBtn.setAttribute('aria-label', t.treeBack);
    backBtn.textContent = currentLang === 'ar' ? '›' : '‹';
    backBtn.addEventListener('click', function () {
      track('tree_back', treeLabel(node), '');
      renderTree();
    });
    navBar.appendChild(backBtn);

    var title = document.createElement('div');
    title.className = 'nura-tree-title';
    title.textContent = t.suggestionTitle;
    navBar.appendChild(title);
    treePanel.appendChild(navBar);

    var card = document.createElement('div');
    card.className = 'nura-suggestion-card';

    var heading = document.createElement('h4');
    heading.textContent = t.suggestionTitle;
    card.appendChild(heading);

    var intro = document.createElement('p');
    intro.textContent = t.suggestionIntro;
    card.appendChild(intro);

    var textarea = document.createElement('textarea');
    textarea.className = 'nura-suggestion-input';
    textarea.placeholder = t.suggestionPlaceholder;
    textarea.maxLength = 5000;
    textarea.setAttribute('dir', t.dir);
    card.appendChild(textarea);

    var actions = document.createElement('div');
    actions.className = 'nura-suggestion-actions';

    var submit = document.createElement('button');
    submit.className = 'nura-suggestion-submit';
    submit.type = 'button';
    submit.textContent = t.suggestionSubmit;
    submit.disabled = true;

    var cancel = document.createElement('button');
    cancel.className = 'nura-suggestion-cancel';
    cancel.type = 'button';
    cancel.textContent = t.suggestionCancel;
    cancel.addEventListener('click', renderTree);

    var error = document.createElement('div');
    error.className = 'nura-suggestion-error';
    error.style.display = 'none';

    textarea.addEventListener('input', function () {
      submit.disabled = textarea.value.trim().length < 5;
      error.style.display = 'none';
    });

    submit.addEventListener('click', async function () {
      var message = textarea.value.trim();
      if (message.length < 5) {
        error.textContent = t.suggestionMin;
        error.style.display = 'block';
        return;
      }

      submit.disabled = true;
      cancel.disabled = true;
      submit.textContent = t.suggestionSending || (currentLang === 'ar' ? 'جارٍ الإرسال…' : 'Tê şandin…');
      try {
        var headers = { 'Content-Type': 'application/json' };
        if (sessionToken) headers['X-Session-Token'] = sessionToken;
        var res = await fetch(API_BASE + '/suggestions', {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({
            session_id: sessionId,
            customer_id: customerId,
            channel: 'web',
            kind: 'suggestion',
            message: message,
          }),
        });
        var data = await res.json().catch(function () { return {}; });
        if (!res.ok) throw new Error(data.detail || ('Error ' + res.status));
        track('suggestion_submit', treeLabel(node), node.id, { message_length: String(message.length) });
        appendUserMsg(message);
        appendBotMsg(t.suggestionThanks + (data.case_number ? '\n' + t.suggestionCase + ': ' + data.case_number : ''), null, null);
        treeStack = [];
        renderTree();
      } catch (e) {
        error.textContent = e.message || UI[currentLang].errorPrefix;
        error.style.display = 'block';
        submit.disabled = false;
        cancel.disabled = false;
        submit.textContent = t.suggestionSubmit;
      }
    });

    actions.appendChild(submit);
    actions.appendChild(cancel);
    card.appendChild(actions);
    card.appendChild(error);
    treePanel.appendChild(card);
    setTimeout(function () { textarea.focus(); }, 50);
  }

  function handleLeaf(node) {
    var dict    = currentLang === 'en' ? ARTICLES_EN : (currentLang === 'ku' ? ARTICLES_KU : ARTICLES);
    var content = dict[node.article];
    if (content === undefined) return;
    appendUserMsg(treeLabel(node));
    showTyping();
    setTimeout(function () {
      hideTyping();
      appendBotMsg(content, 0.97, 'rules');
      treeStack = [];
      renderTree();
    }, 450);
  }

  // ── Language ───────────────────────────────────────────────────────────────
  function applyLang(lang) {
    currentLang = lang;
    var t = UI[lang];
    root.setAttribute('lang', t.htmlLang);
    root.setAttribute('dir', t.dir);
    win.setAttribute('dir', t.dir);
    msgInput.setAttribute('dir', t.dir);
    msgInput.placeholder = t.placeholder;
    headerTitle.textContent = brandTitle || t.headerTitle;
    headerStatus.innerHTML = '<span class="nura-online-dot"></span> ' + t.headerStatus;
    langBtns.forEach(function (b) { b.classList.toggle('active', b.dataset.lang === lang); });
    sendBtn.setAttribute('aria-label', t.sendAriaLabel);
    closeBtn.setAttribute('aria-label', t.closeAriaLabel);
    treeStack = [];
    renderTree();
    if (welcomed) {
      messagesEl.innerHTML = '';
      appendBotMsg(t.welcome, null, null);
    }
  }

  langBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (btn.dataset.lang === currentLang) return;
      track('lang_switch', btn.dataset.lang, '');
      applyLang(btn.dataset.lang);
    });
  });

  // ── Open / close ───────────────────────────────────────────────────────────
  function openChat() {
    lastFocusedEl = document.activeElement;
    isOpen = true;
    win.classList.add('nura-open');
    win.setAttribute('aria-hidden', 'false');
    toggle.setAttribute('aria-expanded', 'true');
    toggle.style.opacity = '0';
    toggle.style.transform = 'scale(0.5)';
    toggle.style.pointerEvents = 'none';
    badge.style.display = 'none';
    updateViewportHeight();
    setTimeout(function () {
      if (!isMobileViewport()) msgInput.focus();
      scrollBottom();
    }, 250);
    if (isEscalated && !isSessionClosed) startAgentStream();
  }
  function closeChat() {
    isOpen = false;
    setPageScrollLocked(false);
    setTreeCollapsedForInput(false);
    win.classList.remove('nura-open');
    win.setAttribute('aria-hidden', 'true');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.style.opacity = '1';
    toggle.style.transform = '';
    toggle.style.pointerEvents = '';
    stopAgentStream();
    if (lastFocusedEl && typeof lastFocusedEl.focus === 'function') {
      setTimeout(function () { lastFocusedEl.focus(); }, 0);
    }
  }

  toggle.addEventListener('click', function () {
    track(isOpen ? 'chat_close' : 'chat_open', 'toggle_btn', '');
    if (isOpen) { closeChat(); } else { openChat(); }
    if (!welcomed && isOpen) {
      welcomed = true;
      badge.style.display = 'none';
      setTimeout(function () { appendBotMsg(UI[currentLang].welcome, null, null); }, 300);
    }
  });
  closeBtn.addEventListener('click', function () { track('chat_close', 'close_btn', ''); closeChat(); });
  win.addEventListener('keydown', trapFocus);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && isOpen) {
      track('chat_close', 'escape_key', '');
      closeChat();
    }
  });

  // ── Input ──────────────────────────────────────────────────────────────────
  msgInput.addEventListener('input', function () {
    msgInput.style.height = 'auto';
    msgInput.style.height = Math.min(msgInput.scrollHeight, 100) + 'px';
    sendBtn.disabled = msgInput.value.trim() === '';
    if (!isSessionClosed && sessionId && sessionToken) {
      clearTimeout(typingDebounceTimer);
      typingDebounceTimer = setTimeout(function () {
        fetch(API_BASE + '/session/' + encodeURIComponent(sessionId) + '/typing',
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Session-Token': sessionToken },
            body: JSON.stringify({ sender: 'customer', text: msgInput.value.trim() })
          }).catch(function () {});
      }, 500);
    }
  });
  msgInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  msgInput.addEventListener('focus', function () {
    setTreeCollapsedForInput(true);
    setTimeout(function () { updateViewportHeight(); scrollBottom(); }, 150);
  });
  msgInput.addEventListener('blur', function () {
    setTimeout(function () { setTreeCollapsedForInput(false); updateViewportHeight(); }, 120);
  });
  sendBtn.addEventListener('click', sendMessage);

  // ── Attachment upload ──────────────────────────────────────────────────────
  attachBtn.addEventListener('click', function () {
    if (attachBtn.disabled) return;
    fileInput.click();
  });

  fileInput.addEventListener('change', async function () {
    var file = fileInput.files[0];
    if (!file) return;
    fileInput.value = '';

    if (!sessionId || !sessionToken) {
      var firstMsgErr = document.createElement('div');
      firstMsgErr.className = 'nura-error-bubble';
      firstMsgErr.textContent = UI[currentLang].attachFirstMessage;
      messagesEl.appendChild(firstMsgErr);
      scrollBottom();
      return;
    }

    attachBtn.disabled = true;

    var form = new FormData();
    form.append('file', file);
    form.append('session_id', sessionId);

    try {
      var uploadRes = await fetch(
        API_BASE + '/upload',
        { method: 'POST', headers: { 'X-Session-Token': sessionToken }, body: form }
      );
      if (!uploadRes.ok) {
        var uploadErr = await uploadRes.json().catch(function () { return {}; });
        throw new Error(uploadErr.detail || ('Upload error ' + uploadRes.status));
      }

      var uploadData = await uploadRes.json();
      var url = uploadData.url;
      var msgType = file.type.indexOf('image/') === 0 ? 'image' : 'file';
      appendAttachmentPreview(file, url, msgType);

      var messageRes = await fetch(API_BASE + '/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': sessionToken || '' },
        body: JSON.stringify({
          session_id: sessionId,
          channel: 'web',
          customer_id: customerId,
          message: msgType === 'image'
            ? (currentLang === 'en' ? '[Image]' : '[صورة]')
            : (currentLang === 'en' ? '[File: ' + file.name + ']' : '[ملف: ' + file.name + ']'),
          attachment_url: url,
          message_type: msgType,
        }),
      });
      if (messageRes.ok) {
        var messageData = await messageRes.json().catch(function () { return {}; });
        sessionId = messageData.session_id || sessionId;
        sessionToken = messageData.session_token || sessionToken;
      }
    } catch (e) {
      var errDiv = document.createElement('div');
      errDiv.className = 'nura-error-bubble';
      errDiv.textContent = '⚠️ ' + (e.message || UI[currentLang].errorPrefix);
      messagesEl.appendChild(errDiv);
      scrollBottom();
    } finally {
      attachBtn.disabled = false;
    }
  });

  // ── Render helpers ─────────────────────────────────────────────────────────
  function fmtTime() {
    var locale = currentLang === 'en' ? 'en' : (currentLang === 'ku' ? 'ku' : 'ar');
    return new Date().toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
  }

  function escHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function scrollBottom() { messagesEl.scrollTop = messagesEl.scrollHeight; }
  function showTyping()   { typingEl.style.display = 'flex'; scrollBottom(); }
  function hideTyping()   { typingEl.style.display = 'none'; }

  function sourceTag(src) {
    if (src === 'rules' || src === 'local_model') return 'local';
    if (src === 'openai') return 'openai';
    return 'low';
  }
  function sourceLabel(src) {
    if (src === 'rules')       return 'Rules';
    if (src === 'local_model') return 'ML';
    if (src === 'openai')      return 'AI';
    return null;
  }

  function appendUserMsg(text) {
    var div = document.createElement('div');
    div.className = 'nura-msg user';
    var tick = document.createElement('span');
    tick.className = 'nura-read-tick';
    tick.textContent = '✓';
    div.innerHTML = '<div class="nura-bubble">' + escHtml(text) + '</div>' +
      '<div class="nura-meta"><span class="nura-msg-time">' + fmtTime() + '</span></div>';
    div.appendChild(tick);
    lastUserTickEl = tick;
    messagesEl.appendChild(div);
    scrollBottom();
  }

  function appendAttachmentPreview(file, url, msgType) {
    var div = document.createElement('div');
    div.className = 'nura-msg user';

    if (msgType === 'image') {
      var img = document.createElement('img');
      img.src = url;
      img.alt = file.name || 'attachment';
      img.className = 'nura-chat-img';
      img.addEventListener('click', function () { window.open(url, '_blank'); });
      div.appendChild(img);
    } else {
      var bubble = document.createElement('div');
      bubble.className = 'nura-bubble';
      var link = document.createElement('a');
      link.href = url;
      link.target = '_blank';
      link.rel = 'noreferrer';
      link.style.color = 'inherit';
      link.style.textDecoration = 'underline';
      link.textContent = '📄 ' + (file.name || 'attachment.pdf');
      bubble.appendChild(link);
      div.appendChild(bubble);
    }

    var meta = document.createElement('div');
    meta.className = 'nura-meta';
    var time = document.createElement('span');
    time.textContent = fmtTime();
    meta.appendChild(time);
    div.appendChild(meta);
    messagesEl.appendChild(div);
    scrollBottom();
  }

  function appendBotMsg(text, confidence, source, sourceDoc) {
    if (lastUserTickEl) {
      lastUserTickEl.textContent = '✓✓';
      lastUserTickEl.classList.add('read');
      lastUserTickEl = null;
    }

    var t    = UI[currentLang];
    var div  = document.createElement('div');
    div.className = 'nura-msg bot';

    var pct   = confidence != null ? Math.round(confidence * 100) + '%' : '';
    var tag   = sourceTag(source);
    var label = sourceLabel(source);

    var hasFollowUp = text.indexOf(t.followUpMarker) !== -1;
    var mainText = hasFollowUp
      ? text.substring(0, text.lastIndexOf(t.followUpMarker)).trimEnd()
      : text;

    div.innerHTML =
      '<div class="nura-bubble">' + escHtml(mainText) + '</div>' +
      (sourceDoc ? '<span class="nura-source-doc-chip" title="' + escHtml(sourceDoc) + '">📄 ' + escHtml(sourceDoc) + '</span>' : '') +
      '<div class="nura-meta">' +
        (pct   ? '<span>' + pct + '</span>' : '') +
        (label ? '<span class="nura-source-tag ' + tag + '">' + label + '</span>' : '') +
        '<span class="nura-msg-time">' + fmtTime() + '</span>' +
      '</div>';

    if (source) {
      var fbDiv   = document.createElement('div');
      fbDiv.className = 'nura-feedback-btns';
      var btnGood = document.createElement('button');
      btnGood.className = 'nura-fb-btn good'; btnGood.textContent = '✓';
      var btnBad  = document.createElement('button');
      btnBad.className  = 'nura-fb-btn bad';  btnBad.textContent  = '✗';
      btnGood.addEventListener('click', function () { track('feedback_good', source || '', ''); onFeedback(true,  btnGood, btnBad); });
      btnBad.addEventListener('click',  function () { track('feedback_bad',  source || '', ''); onFeedback(false, btnGood, btnBad); });
      fbDiv.appendChild(btnGood);
      fbDiv.appendChild(btnBad);
      div.appendChild(fbDiv);
    }

    var row     = document.createElement('div');
    row.className = 'nura-bot-row';
    var avatar  = document.createElement('div');
    avatar.className = 'nura-bot-avatar-sm';
    avatar.textContent = 'NU';
    var content = document.createElement('div');
    content.className = 'nura-bot-content';
    content.appendChild(div);
    row.appendChild(avatar);
    row.appendChild(content);
    messagesEl.appendChild(row);
    scrollBottom();

    if (hasFollowUp) {
      setTimeout(function () {
        var fDiv = document.createElement('div');
        fDiv.className = 'nura-msg bot';
        fDiv.innerHTML =
          '<div class="nura-followup-bubble">' +
            escHtml(t.followUpMarker) +
            '<div class="nura-followup-btns">' +
              '<button class="nura-followup-btn yes-btn">' + escHtml(t.yesBtn) + '</button>' +
              '<button class="nura-followup-btn no no-btn">' + escHtml(t.noBtn) + '</button>' +
            '</div>' +
          '</div>';
        fDiv.querySelector('.yes-btn').addEventListener('click', function () {
          track('followup_yes', '', '');
          fDiv.querySelector('.nura-followup-btns').remove();
          appendBotMsg(t.yesReply, null, null);
          msgInput.focus();
        });
        fDiv.querySelector('.no-btn').addEventListener('click', function () {
          track('followup_no', '', '');
          fDiv.querySelector('.nura-followup-btns').remove();
          appendUserMsg(t.noUserText);
          showTyping();
          setTimeout(function () { hideTyping(); appendBotMsg(t.noReply, null, null); }, 800);
        });
        var fRow    = document.createElement('div');
        fRow.className = 'nura-bot-row';
        var fAvatar = document.createElement('div');
        fAvatar.className = 'nura-bot-avatar-sm';
        fAvatar.textContent = 'NU';
        var fContent = document.createElement('div');
        fContent.className = 'nura-bot-content';
        fContent.appendChild(fDiv);
        fRow.appendChild(fAvatar);
        fRow.appendChild(fContent);
        messagesEl.appendChild(fRow);
        scrollBottom();
      }, 600);
    }
  }

  function appendAgentMsg(text, agentName) {
    var t   = UI[currentLang];
    var div = document.createElement('div');
    div.className = 'nura-msg agent';
    div.innerHTML =
      '<div class="nura-bubble">' + escHtml(text) + '</div>' +
      '<div class="nura-meta"><span>' + escHtml(agentName || t.agentLabel) + '</span><span>' + fmtTime() + '</span></div>';
    messagesEl.appendChild(div);
    scrollBottom();
    if (escalationBannerEl) escalationBannerEl.innerHTML = '<span>' + escHtml(t.agentConnectedBanner) + '</span>';
  }

  function showEscalationBanner() {
    escalationBannerEl = document.createElement('div');
    escalationBannerEl.className = 'nura-escalation-banner';
    escalationBannerEl.innerHTML = '<div class="nura-esc-spinner"></div><span>' + escHtml(UI[currentLang].escalatingBanner) + '</span>';
    messagesEl.appendChild(escalationBannerEl);
    scrollBottom();
  }

  // ── Agent message polling ──────────────────────────────────────────────────
  async function startAgentStream() {
    if (agentEventSource || agentStreamStarting || !sessionId || !sessionToken) return;
    agentStreamStarting = true;
    try {
      var tokenRes = await fetch(API_BASE + '/session/' + encodeURIComponent(sessionId) + '/stream-token', {
        method: 'POST',
        headers: { 'X-Session-Token': sessionToken },
      });
      if (!tokenRes.ok) throw new Error('Stream token failed: ' + tokenRes.status);
      var tokenData = await tokenRes.json();
      var streamUrl = API_BASE + '/session/' + encodeURIComponent(sessionId) +
        '/stream?stream_token=' + encodeURIComponent(tokenData.stream_token);
      agentEventSource = new EventSource(streamUrl);
      agentEventSource.onmessage = function (e) {
        try { handleStreamEvent(JSON.parse(e.data)); } catch (_) {}
      };
      agentEventSource.onerror = function () {
        agentEventSource.close();
        agentEventSource = null;
        if (!isSessionClosed && isEscalated) {
          setTimeout(startAgentStream, 5000);
        }
      };
    } catch (e) {
      if (!isSessionClosed && isEscalated) {
        setTimeout(startAgentStream, 5000);
      }
    } finally {
      agentStreamStarting = false;
    }
  }

  function stopAgentStream() {
    if (agentEventSource) {
      agentEventSource.close();
      agentEventSource = null;
    }
  }

  var agentTypingTimer = null;

  function handleStreamEvent(event) {
    if (event.type === 'turn') {
      var t = event.turn;
      if (t.role === 'agent' && t.source === 'human') {
        appendAgentMsg(t.message);
      }
    } else if (event.type === 'typing' && event.sender === 'agent') {
      showTyping();
      clearTimeout(agentTypingTimer);
      agentTypingTimer = setTimeout(hideTyping, 3000);
    } else if (event.type === 'status' && event.status === 'RESOLVED' && !isSessionClosed) {
      isSessionClosed = true;
      stopAgentStream();
      var notice = document.createElement('div');
      notice.className = 'nura-escalation-banner';
      notice.textContent = UI[currentLang].sessionClosed;
      messagesEl.appendChild(notice);
      showRatingPrompt();
      scrollBottom();
      msgInput.disabled = true;
      sendBtn.disabled  = true;
    }
  }

  function showRatingPrompt() {
    var t = UI[currentLang];
    var ratingDiv = document.createElement('div');
    ratingDiv.className = 'nura-rating-prompt';
    var p = document.createElement('p');
    p.textContent = t.ratePrompt;
    var starsRow = document.createElement('div');
    starsRow.className = 'nura-rating-stars';
    [1, 2, 3, 4, 5].forEach(function (score) {
      var btn = document.createElement('button');
      btn.className = 'nura-star-btn';
      btn.textContent = '★';
      btn.addEventListener('mouseenter', function () {
        starsRow.querySelectorAll('.nura-star-btn').forEach(function (b, i) { b.classList.toggle('lit', i < score); });
      });
      btn.addEventListener('mouseleave', function () {
        starsRow.querySelectorAll('.nura-star-btn').forEach(function (b) { b.classList.remove('lit'); });
      });
      btn.addEventListener('click', function () {
        starsRow.querySelectorAll('.nura-star-btn').forEach(function (b, i) { b.classList.toggle('lit', i < score); b.disabled = true; });
        fetch(API_BASE + '/session/' + encodeURIComponent(sessionId) + '/rating', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Session-Token': sessionToken || '' },
          body: JSON.stringify({ score: score }),
        }).catch(function () {});
        setTimeout(function () { ratingDiv.innerHTML = '<p>' + escHtml(t.rateThanks) + '</p>'; }, 300);
      });
      starsRow.appendChild(btn);
    });
    ratingDiv.appendChild(p);
    ratingDiv.appendChild(starsRow);
    messagesEl.appendChild(ratingDiv);
  }

  // ── Send ───────────────────────────────────────────────────────────────────
  async function sendMessage() {
    var text = msgInput.value.trim();
    if (!text || sendBtn.disabled) return;

    track('send_message', text.substring(0, 100), '');
    msgInput.value = '';
    msgInput.style.height = 'auto';
    sendBtn.disabled = true;

    appendUserMsg(text);
    showTyping();

    try {
      var res = await fetch(API_BASE + '/message', {
        method: 'POST',
        headers: sessionToken
          ? { 'Content-Type': 'application/json', 'X-Session-Token': sessionToken }
          : { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, channel: 'web', customer_id: customerId, message: text }),
      });

      if (!res.ok) {
        var err = await res.json().catch(function () { return {}; });
        throw new Error(err.detail || 'Error ' + res.status);
      }

      var data = await res.json();
      sessionId = data.session_id;
      sessionToken = data.session_token || sessionToken;
      hideTyping();
      if (data.response) appendBotMsg(data.response, data.confidence, data.source, data.source_doc);

      if (data.escalated && !isEscalated) {
        isEscalated = true;
        showEscalationBanner();
        startAgentStream();
      }
    } catch (e) {
      hideTyping();
      var errDiv = document.createElement('div');
      errDiv.className = 'nura-error-bubble';
      errDiv.textContent = '⚠️ ' + (e.message || UI[currentLang].errorPrefix);
      messagesEl.appendChild(errDiv);
      scrollBottom();
    }
  }

  // ── Analytics ──────────────────────────────────────────────────────────────
  function track(eventType, label, meta, extra) {
    fetch(API_BASE + '/analytics/click', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.assign({
        session_id: sessionId, customer_id: customerId,
        event_type: eventType, label: label || '', meta: meta || '',
      }, extra || {})),
    }).catch(function () {});
  }

  // ── Feedback ───────────────────────────────────────────────────────────────
  async function onFeedback(isGood, btnGood, btnBad) {
    btnGood.disabled = true;
    btnBad.disabled  = true;
    if (isGood) { btnGood.classList.add('sel-good'); return; }
    btnBad.classList.add('sel-bad');
    if (!sessionId || isEscalated) return;
    try {
      await fetch(API_BASE + '/handoff/' + sessionId, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': sessionToken || '' },
        body: JSON.stringify({ reason: 'bad_feedback' }),
      });
      isEscalated = true;
      showEscalationBanner();
      startAgentStream();
    } catch (e) { console.warn('Handoff failed:', e); }
  }

  // ── Init ───────────────────────────────────────────────────────────────────
  applyLang(initialLang);
  loadSharedTopicTree();
  if (autoOpen) {
    openChat();
    if (!welcomed) {
      welcomed = true;
      setTimeout(function () { appendBotMsg(UI[currentLang].welcome, null, null); }, 300);
    }
  } else {
    setTimeout(function () { if (!isOpen) badge.style.display = 'flex'; }, 2000);
  }

  }

  if (document.body) {
    initNuraWidget();
  } else {
    document.addEventListener('DOMContentLoaded', initNuraWidget, { once: true });
  }
})();
