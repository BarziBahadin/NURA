(function () {
  'use strict';

  var _s = document.currentScript;
  var API_BASE = (_s && _s.getAttribute('data-api')) || 'http://localhost:8080/v1';

  // ── Inject styles ──────────────────────────────────────────────────────────
  var style = document.createElement('style');
  style.textContent = [
    '#nura-widget-root * { box-sizing: border-box; margin: 0; padding: 0; }',
    '#nura-widget-root { font-family: \'Segoe UI\', \'Noto Sans Arabic\', Tahoma, Arial, sans-serif; }',

    '#chat-toggle {',
    '  position: fixed; bottom: 28px; left: 28px;',
    '  width: 60px; height: 60px; border-radius: 50%;',
    '  background: linear-gradient(135deg, #ea580c, #f97316);',
    '  border: none; cursor: pointer;',
    '  box-shadow: 0 4px 18px rgba(234,88,12,0.45);',
    '  display: flex; align-items: center; justify-content: center;',
    '  transition: transform 0.2s, box-shadow 0.2s; z-index: 2147483640;',
    '}',
    '#chat-toggle:hover { transform: scale(1.08); box-shadow: 0 6px 24px rgba(234,88,12,0.55); }',

    '#nura-badge {',
    '  position: absolute; top: -4px; right: -4px;',
    '  background: #ef476f; color: #fff; border-radius: 50%;',
    '  width: 20px; height: 20px; font-size: 11px; font-weight: 700;',
    '  display: none; align-items: center; justify-content: center;',
    '}',

    '#chat-window {',
    '  position: fixed; top: 50%; left: 50%;',
    '  width: 420px; max-height: 680px;',
    '  background: #fff; border-radius: 18px;',
    '  box-shadow: 0 8px 40px rgba(0,0,0,0.18);',
    '  display: flex; flex-direction: column; overflow: hidden;',
    '  z-index: 2147483639;',
    '  transform: translate(-50%, -50%) scale(0.85);',
    '  opacity: 0; pointer-events: none;',
    '  transition: transform 0.25s cubic-bezier(.34,1.56,.64,1), opacity 0.2s;',
    '}',
    '#chat-window.nura-open { transform: translate(-50%, -50%) scale(1); opacity: 1; pointer-events: all; }',

    '.nura-chat-header {',
    '  background: linear-gradient(135deg, #ea580c, #f97316);',
    '  padding: 14px 18px; display: flex; align-items: center; gap: 10px; flex-shrink: 0;',
    '}',
    '.nura-avatar {',
    '  width: 40px; height: 40px; border-radius: 50%;',
    '  background: rgba(255,255,255,0.25);',
    '  display: flex; align-items: center; justify-content: center;',
    '  color: #fff; font-weight: 700; font-size: 13px; flex-shrink: 0; letter-spacing: -0.5px;',
    '}',
    '.nura-header-info { flex: 1; }',
    '.nura-header-info h3 { color: #fff; font-size: 15px; font-weight: 700; }',
    '.nura-header-info span { color: rgba(255,255,255,0.8); font-size: 12px; }',
    '.nura-online-dot {',
    '  width: 8px; height: 8px; background: #06d6a0; border-radius: 50%;',
    '  display: inline-block; margin: 0 3px; animation: nuraPulse 2s infinite;',
    '}',
    '@keyframes nuraPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }',

    '#nura-lang-toggle {',
    '  display: flex; align-items: center;',
    '  background: rgba(255,255,255,0.15); border-radius: 20px; overflow: hidden;',
    '  border: 1.5px solid rgba(255,255,255,0.35); flex-shrink: 0;',
    '}',
    '.nura-lang-btn {',
    '  background: none; border: none; color: rgba(255,255,255,0.7);',
    '  font-size: 11px; font-weight: 700; padding: 4px 9px; cursor: pointer;',
    '  transition: background 0.15s, color 0.15s; font-family: inherit; letter-spacing: 0.3px;',
    '}',
    '.nura-lang-btn.active { background: rgba(255,255,255,0.9); color: #ea580c; border-radius: 18px; }',
    '.nura-lang-btn:hover:not(.active) { color: #fff; }',

    '#nura-close-btn {',
    '  background: none; border: none; color: rgba(255,255,255,0.8);',
    '  cursor: pointer; font-size: 20px; line-height: 1; padding: 4px;',
    '}',
    '#nura-close-btn:hover { color: #fff; }',

    '#nura-messages {',
    '  flex: 1; overflow-y: auto; padding: 16px;',
    '  display: flex; flex-direction: column; gap: 10px; scroll-behavior: smooth;',
    '}',
    '#nura-messages::-webkit-scrollbar { width: 4px; }',
    '#nura-messages::-webkit-scrollbar-thumb { background: #ccc; border-radius: 4px; }',

    '.nura-msg { display: flex; flex-direction: column; max-width: 82%; animation: nuraFadeUp 0.2s ease; }',
    '@keyframes nuraFadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }',
    '.nura-msg.user  { align-self: flex-start; }',
    '.nura-msg.bot   { align-self: flex-end; }',
    '.nura-msg.agent { align-self: flex-end; }',

    '.nura-bubble {',
    '  padding: 9px 13px; border-radius: 16px; font-size: 13.5px;',
    '  line-height: 1.6; word-break: break-word; white-space: pre-wrap; unicode-bidi: plaintext;',
    '}',
    '.nura-msg.user  .nura-bubble { background: #f0f2f5; color: #1a1a2e; border-bottom-right-radius: 4px; }',
    '.nura-msg.bot   .nura-bubble { background: linear-gradient(135deg, #ea580c, #f97316); color: #fff; border-bottom-left-radius: 4px; }',
    '.nura-msg.agent .nura-bubble { background: linear-gradient(135deg, #1a7a4a, #06d6a0); color: #fff; border-bottom-left-radius: 4px; }',

    '.nura-msg.bot .nura-followup-bubble {',
    '  margin-top: 5px; padding: 8px 13px; border-radius: 16px; border-bottom-left-radius: 4px;',
    '  font-size: 13px; background: rgba(234,88,12,0.08); color: #ea580c;',
    '  border: 1.5px solid rgba(249,115,22,0.35); animation: nuraFadeUp 0.2s ease;',
    '}',
    '.nura-followup-btns { margin-top: 7px; display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-start; }',
    '.nura-followup-btn {',
    '  background: #fff; border: 1.5px solid #f97316; color: #ea580c;',
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

    '.nura-source-tag {',
    '  font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 20px;',
    '  text-transform: uppercase; letter-spacing: 0.5px;',
    '}',
    '.nura-source-tag.local  { background: #d4f7e8; color: #1a7a4a; }',
    '.nura-source-tag.openai { background: #e8d4f7; color: #6b1a99; }',
    '.nura-source-tag.low    { background: #ffecd4; color: #b45309; }',
    '.nura-source-doc-chip {',
    '  display: inline-flex; align-items: center; gap: 3px;',
    '  font-size: 9.5px; color: #888; margin-top: 2px;',
    '  background: #f5f5f5; border: 1px solid #e5e5e5;',
    '  border-radius: 8px; padding: 1px 7px;',
    '  max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;',
    '}',

    '#nura-typing {',
    '  display: none; align-self: flex-end;',
    '  padding: 10px 14px;',
    '  background: linear-gradient(135deg, #ea580c, #f97316);',
    '  border-radius: 18px; border-bottom-left-radius: 4px;',
    '  animation: nuraFadeUp 0.2s ease; margin: 0 16px 0;',
    '}',
    '#nura-typing span {',
    '  display: inline-block; width: 7px; height: 7px; border-radius: 50%;',
    '  background: rgba(255,255,255,0.8); margin: 0 2px; animation: nuraBounce 1.2s infinite;',
    '}',
    '#nura-typing span:nth-child(2) { animation-delay: 0.2s; }',
    '#nura-typing span:nth-child(3) { animation-delay: 0.4s; }',
    '@keyframes nuraBounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }',

    '#nura-tree-panel {',
    '  border-top: 1px solid #f0f2f5; padding: 10px 14px;',
    '  flex-shrink: 0; background: #fafafa; max-height: 200px; overflow-y: auto;',
    '}',
    '#nura-tree-panel::-webkit-scrollbar { width: 3px; }',
    '#nura-tree-panel::-webkit-scrollbar-thumb { background: #ddd; border-radius: 3px; }',

    '.nura-tree-nav-bar { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; flex-wrap: wrap; }',
    '.nura-tree-crumb { font-size: 10px; color: #aaa; font-weight: 600; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }',
    '.nura-tree-nav-btn {',
    '  background: #fff7ed; border: 1.5px solid #f97316; color: #ea580c;',
    '  border-radius: 20px; padding: 3px 10px; font-size: 11px; cursor: pointer;',
    '  font-family: inherit; transition: background 0.15s, color 0.15s; flex-shrink: 0; white-space: nowrap;',
    '}',
    '.nura-tree-nav-btn:hover { background: #f97316; color: #fff; }',
    '.nura-tree-nav-btn.home { background: none; border-color: #ddd; color: #999; }',
    '.nura-tree-nav-btn.home:hover { background: #f0f2f5; color: #555; border-color: #bbb; }',

    '.nura-tree-level-q { font-size: 11.5px; color: #555; font-weight: 600; margin-bottom: 7px; }',
    '.nura-agent-bypass-btn {',
    '  margin-top: 12px; width: 100%; padding: 9px 14px;',
    '  background: none; border: 1.5px dashed #f97316; border-radius: 10px;',
    '  color: #ea580c; font-size: 12.5px; font-weight: 600; cursor: pointer;',
    '  transition: background 0.15s, color 0.15s;',
    '}',
    '.nura-agent-bypass-btn:hover { background: #fff7ed; }',
    '.nura-tree-options { display: flex; gap: 6px; flex-wrap: wrap; }',
    '.nura-tree-opt {',
    '  background: #fff; border: 1.5px solid #e0e0e0; color: #333;',
    '  border-radius: 20px; padding: 5px 13px; font-size: 12.5px; cursor: pointer;',
    '  font-family: inherit; transition: background 0.15s, border-color 0.15s, color 0.15s; white-space: nowrap;',
    '}',
    '.nura-tree-opt:hover { background: #fff7ed; border-color: #f97316; color: #ea580c; }',
    '.nura-tree-opt.has-children::after { content: \' ›\'; font-size: 13px; opacity: 0.6; }',

    '.nura-chat-footer {',
    '  border-top: 1px solid #f0f2f5; padding: 10px 14px;',
    '  display: flex; gap: 8px; align-items: flex-end; flex-shrink: 0; background: #fff;',
    '}',
    '#nura-msg-input {',
    '  flex: 1; border: 1.5px solid #e0e0e0; border-radius: 22px;',
    '  padding: 9px 16px; font-size: 14px; font-family: inherit;',
    '  outline: none; resize: none; max-height: 100px; line-height: 1.4;',
    '  transition: border-color 0.2s;',
    '}',
    '#nura-msg-input:focus { border-color: #f97316; }',
    '#nura-msg-input::placeholder { color: #bbb; }',

    '#nura-send-btn {',
    '  width: 40px; height: 40px; border-radius: 50%;',
    '  background: linear-gradient(135deg, #ea580c, #f97316);',
    '  border: none; cursor: pointer;',
    '  display: flex; align-items: center; justify-content: center; flex-shrink: 0;',
    '  transition: transform 0.15s, opacity 0.15s;',
    '}',
    '#nura-send-btn:hover { transform: scale(1.08); }',
    '#nura-send-btn:disabled { opacity: 0.5; cursor: default; transform: none; }',
    '#nura-send-btn svg { width: 18px; height: 18px; fill: #fff; }',

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
    '  background: #fff3cd; border: 1px solid #ffc107; border-radius: 10px;',
    '  padding: 9px 13px; font-size: 12.5px; color: #856404; text-align: center;',
    '  animation: nuraFadeUp 0.2s ease;',
    '}',
    '.nura-error-bubble {',
    '  background: #fff0f0; color: #c0392b; border: 1px solid #f5c6cb;',
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
    '.nura-star-btn:hover, .nura-star-btn.lit { color: #f97316; }',
    '.nura-star-btn:hover { transform: scale(1.15); }',

    '@media (max-width: 460px) {',
    '  #chat-window { width: calc(100vw - 24px); max-height: 90vh; }',
    '}',
  ].join('\n');
  document.head.appendChild(style);

  // ── Inject HTML ────────────────────────────────────────────────────────────
  var root = document.createElement('div');
  root.id = 'nura-widget-root';
  root.innerHTML = [
    '<button id="chat-toggle" aria-label="فتح المحادثة">',
    '  <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="white" viewBox="0 0 24 24">',
    '    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>',
    '  </svg>',
    '  <div id="nura-badge">1</div>',
    '</button>',
    '<div id="chat-window" role="dialog" aria-label="نافذة دعم العملاء">',
    '  <div class="nura-chat-header">',
    '    <div class="nura-avatar">RC</div>',
    '    <div class="nura-header-info">',
    '      <h3 id="nura-header-title">NURA</h3>',
    '      <span id="nura-header-status">متصل الآن <span class="nura-online-dot"></span></span>',
    '    </div>',
    '    <div id="nura-lang-toggle" role="group" aria-label="Language">',
    '      <button class="nura-lang-btn active" data-lang="ar">عربي</button>',
    '      <button class="nura-lang-btn" data-lang="ku">Kurdî</button>',
    '    </div>',
    '    <button id="nura-close-btn" aria-label="إغلاق">✕</button>',
    '  </div>',
    '  <div id="nura-messages"></div>',
    '  <div id="nura-typing"><span></span><span></span><span></span></div>',
    '  <div id="nura-tree-panel"></div>',
    '  <div class="nura-chat-footer">',
    '    <button id="nura-send-btn" aria-label="إرسال" disabled>',
    '      <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>',
    '    </button>',
    '    <textarea id="nura-msg-input" rows="1" placeholder="اكتب رسالتك هنا…" maxlength="500"></textarea>',
    '  </div>',
    '</div>',
  ].join('\n');
  document.body.appendChild(root);

  // ── UI strings per language ────────────────────────────────────────────────
  var UI = {
    ar: {
      dir: 'rtl', htmlLang: 'ar',
      headerTitle: 'NURA', headerStatus: 'متصل الآن',
      placeholder: 'اكتب رسالتك هنا…',
      sendAriaLabel: 'إرسال', closeAriaLabel: 'إغلاق',
      welcome: 'أهلاً وسهلاً، شكراً لتواصلك مع Rcell Telecom!\nاختر موضوعاً من القائمة أدناه أو اكتب سؤالك مباشرةً.',
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
      talkToAgent: '🎧 التحدث مع موظف مباشرةً',
    },
    ku: {
      dir: 'ltr', htmlLang: 'ku',
      headerTitle: 'NURA', headerStatus: 'Niha ve ye',
      placeholder: 'Peyama xwe binivîse…',
      sendAriaLabel: 'Bişîne', closeAriaLabel: 'Bigire',
      welcome: 'Xêr hatî bo xizmetguzariya xerîdarên Rcell Telecom!\nMijareke ji lîsteyê hilbijêre an pirseke xwe binivîse.',
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
      talkToAgent: '🎧 Rasterast bi karmend re biaxive',
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

  // ── Topic tree ─────────────────────────────────────────────────────────────
  var TOPIC_TREE = {
    id: 'root',
    label: { ar: 'كيف يمكنني مساعدتك؟', ku: 'Çawa dikarim alîkariya te bikim?' },
    children: [
      { id: 'apps', label: { ar: '📱 التطبيقات', ku: '📱 Aplikasyon' }, children: [
        { id: 'selfcare', label: { ar: 'تطبيق Self-Care', ku: 'Apî Self-Care' }, children: [
          { id: 'sc_dl',     label: { ar: 'تحميل التطبيق',           ku: 'Daxistina aplikasyonê'   }, article: 0  },
          { id: 'sc_login',  label: { ar: 'مشكلة في تسجيل الدخول',   ku: 'Pirsgirêka têketinê'    }, article: 13 },
          { id: 'sc_access', label: { ar: 'لا أستطيع الوصول للموقع', ku: 'Nikarin gihîjin malperê' }, article: 1  },
        ]},
        { id: 'hakki', label: { ar: 'تطبيق حكي', ku: 'Apî Hakki' }, children: [
          { id: 'hk_dl',  label: { ar: 'تحميل التطبيق',                ku: 'Daxistina aplikasyonê'   }, article: 5  },
          { id: 'hk_sos', label: { ar: 'الاستخدام المجاني في الطوارئ', ku: 'Bikaranîna belaş a acil' }, article: 28 },
        ]},
        { id: 'ana', label: { ar: 'منصة آنا (Ana)', ku: 'Platforma Ana' }, article: 20 },
      ]},
      { id: 'internet', label: { ar: '🌐 الإنترنت والاتصال', ku: '🌐 Înternetê û Pêwendî' }, children: [
        { id: 'slow',   label: { ar: 'الإنترنت بطيء', ku: 'Înternetê hêdî ye' }, article: 6  },
        { id: 'noconn', label: { ar: 'لا يوجد اتصال', ku: 'Pêwendî tune'       }, article: 3  },
        { id: 'apn',    label: { ar: 'إعدادات APN',   ku: 'Mîhengên APN'       }, article: 21 },
        { id: 'fiveg',  label: { ar: '5G — قريباً',   ku: '5G — nêzîk e'       }, article: 25 },
        { id: 'hdcall', label: { ar: 'HD Call (VoLTE)', ku: 'HD Call (VoLTE)' }, children: [
          { id: 'hd_what', label: { ar: 'ما هو HD Call؟',  ku: 'HD Call çi ye?'              }, article: 7  },
          { id: 'hd_why',  label: { ar: 'مميزاته',          ku: 'Taybetmendiyên wê'           }, article: 8  },
          { id: 'hd_sup',  label: { ar: 'هل هاتفي يدعمه؟', ku: 'Têlefona min piştgirî dide?' }, article: 9  },
          { id: 'hd_act',  label: { ar: 'كيف أفعّله؟',      ku: 'Çawa çalak bikim?'           }, article: 10 },
          { id: 'hd_use',  label: { ar: 'كيف أستخدمه؟',    ku: 'Çawa bikar bînim?'           }, article: 11 },
          { id: 'hd_fix',  label: { ar: 'مشكلة في HD Call', ku: 'Pirsgirêka HD Call'          }, article: 12 },
        ]},
      ]},
      { id: 'account', label: { ar: '🔐 الحساب والأمان', ku: '🔐 Hesab û Ewlekarî' }, children: [
        { id: 'password', label: { ar: 'كلمة المرور', ku: 'Şîfre' }, children: [
          { id: 'pw_change',  label: { ar: 'تغيير كلمة المرور', ku: 'Guherandina şîfreyê'        }, article: 14 },
          { id: 'pw_recover', label: { ar: 'نسيت كلمة المرور',  ku: 'Şîfreya min ji bîra min çû' }, article: 19 },
        ]},
        { id: 'pin',        label: { ar: 'الرمز السري PIN',        ku: 'Koda PIN'            }, article: 2  },
        { id: 'login_prob', label: { ar: 'مشكلة في تسجيل الدخول', ku: 'Pirsgirêka têketinê'  }, article: 13 },
        { id: 'puk',        label: { ar: 'SIM مقفلة / رمز PUK',   ku: 'SIM kilêrkirî / PUK'  }, article: 23 },
      ]},
      { id: 'packages', label: { ar: '📦 الباقات والخدمات', ku: '📦 Pakêt û Xizmetguzarî' }, children: [
        { id: 'pkg_prices', label: { ar: 'أسعار الباقات',       ku: 'Bihayên pakêtan'     }, article: 16 },
        { id: 'sim',        label: { ar: 'شريحة SIM',           ku: 'Karta SIM'           }, article: 18 },
        { id: 'esim',       label: { ar: 'eSIM الرقمية',        ku: 'eSIM Dijîtal'        }, article: 24 },
        { id: 'points',     label: { ar: 'إرسال النقاط',        ku: 'Şandina xalan'       }, article: 4  },
        { id: 'fastdata',   label: { ar: 'الرصيد ينتهي بسرعة', ku: 'Balans zû diqede'    }, article: 22 },
        { id: 'scratchcard',label: { ar: 'بطاقة شحن محكوكة',    ku: 'Karta şarjê xerabûye'}, article: 29 },
      ]},
      { id: 'info', label: { ar: 'ℹ️ معلومات عامة', ku: 'ℹ️ Agahiyên Giştî' }, children: [
        { id: 'hours',    label: { ar: 'ساعات العمل',          ku: 'Demjimêrên xebatê'                }, article: 17 },
        { id: 'coverage', label: { ar: 'تغطية الشركة ومراكزها', ku: 'Nixumandin û navendên pargîdaniyê'}, article: 26 },
        { id: 'business', label: { ar: 'إنترنت الأعمال FTTx',  ku: 'Înterneta karsaziyê FTTx'         }, article: 27 },
      ]},
    ],
  };

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
  var typingDebounceTimer  = null;

  // ── DOM refs ───────────────────────────────────────────────────────────────
  var toggle      = root.querySelector('#chat-toggle');
  var win         = root.querySelector('#chat-window');
  var closeBtn    = root.querySelector('#nura-close-btn');
  var msgInput    = root.querySelector('#nura-msg-input');
  var sendBtn     = root.querySelector('#nura-send-btn');
  var messagesEl  = root.querySelector('#nura-messages');
  var typingEl    = root.querySelector('#nura-typing');
  var badge       = root.querySelector('#nura-badge');
  var treePanel   = root.querySelector('#nura-tree-panel');
  var headerTitle = root.querySelector('#nura-header-title');
  var headerStatus= root.querySelector('#nura-header-status');
  var langBtns    = root.querySelectorAll('.nura-lang-btn');

  // ── Tree helpers ───────────────────────────────────────────────────────────
  function treeLabel(node) { return node.label[currentLang] || node.label.ar; }
  function currentTreeNode() { return treeStack.length > 0 ? treeStack[treeStack.length - 1] : TOPIC_TREE; }

  async function directToAgent() {
    if (isEscalated || isSessionClosed) return;
    try {
      var handoffRes = await fetch(API_BASE + '/handoff/direct', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      backBtn.textContent = t.treeBack;
      backBtn.addEventListener('click', function () {
        track('tree_back', treeLabel(treeStack[treeStack.length - 1]), '');
        treeStack.pop();
        renderTree();
      });
      navBar.appendChild(backBtn);

      if (treeStack.length > 1) {
        var homeBtn = document.createElement('button');
        homeBtn.className = 'nura-tree-nav-btn home';
        homeBtn.textContent = t.treeHome;
        homeBtn.addEventListener('click', function () {
          track('tree_home', '', '');
          treeStack = [];
          renderTree();
        });
        navBar.appendChild(homeBtn);
      }

      var crumb = document.createElement('span');
      crumb.className = 'nura-tree-crumb';
      crumb.textContent = treeStack.map(function (n) { return treeLabel(n); }).join(' › ');
      navBar.appendChild(crumb);
      treePanel.appendChild(navBar);
    }

    var q = document.createElement('div');
    q.className = 'nura-tree-level-q';
    q.textContent = treeLabel(node);
    treePanel.appendChild(q);

    var optsDiv = document.createElement('div');
    optsDiv.className = 'nura-tree-options';

    (node.children || []).forEach(function (child) {
      var btn = document.createElement('button');
      btn.className = 'nura-tree-opt' + (child.children ? ' has-children' : '');
      btn.textContent = treeLabel(child);
      btn.addEventListener('click', function () {
        track('tree_click', treeLabel(child), child.id, { topic_id: child.id, article_id: child.article != null ? child.article : null });
        if (child.article !== undefined) {
          handleLeaf(child);
        } else if (child.children) {
          treeStack.push(child);
          renderTree();
        }
      });
      optsDiv.appendChild(btn);
    });

    treePanel.appendChild(optsDiv);

    if (treeStack.length === 0 && !isEscalated) {
      var agentBtn = document.createElement('button');
      agentBtn.className = 'nura-agent-bypass-btn';
      agentBtn.textContent = UI[currentLang].talkToAgent;
      agentBtn.addEventListener('click', function () {
        track('direct_to_agent', 'bypass_btn', '');
        directToAgent();
      });
      treePanel.appendChild(agentBtn);
    }
  }

  function handleLeaf(node) {
    var dict    = currentLang === 'ku' ? ARTICLES_KU : ARTICLES;
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
    win.setAttribute('dir', t.dir);
    msgInput.setAttribute('dir', t.dir);
    msgInput.placeholder = t.placeholder;
    headerTitle.textContent = t.headerTitle;
    headerStatus.innerHTML = t.headerStatus + ' <span class="nura-online-dot"></span>';
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
    isOpen = true;
    win.classList.add('nura-open');
    badge.style.display = 'none';
    setTimeout(function () { msgInput.focus(); }, 250);
    if (isEscalated && !isSessionClosed) startAgentStream();
  }
  function closeChat() {
    isOpen = false;
    win.classList.remove('nura-open');
    stopAgentStream();
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

  // ── Input ──────────────────────────────────────────────────────────────────
  msgInput.addEventListener('input', function () {
    msgInput.style.height = 'auto';
    msgInput.style.height = Math.min(msgInput.scrollHeight, 100) + 'px';
    sendBtn.disabled = msgInput.value.trim() === '';
    if (isEscalated && !isSessionClosed && sessionId && sessionToken) {
      clearTimeout(typingDebounceTimer);
      typingDebounceTimer = setTimeout(function () {
        fetch(API_BASE + '/session/' + encodeURIComponent(sessionId) +
          '/typing?sender=customer&session_token=' + encodeURIComponent(sessionToken),
          { method: 'POST' }).catch(function () {});
      }, 500);
    }
  });
  msgInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  sendBtn.addEventListener('click', sendMessage);

  // ── Render helpers ─────────────────────────────────────────────────────────
  function fmtTime() {
    return new Date().toLocaleTimeString('ar', { hour: '2-digit', minute: '2-digit' });
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
    div.innerHTML = '<div class="nura-bubble">' + escHtml(text) + '</div>' +
      '<div class="nura-meta"><span>' + fmtTime() + '</span></div>';
    messagesEl.appendChild(div);
    scrollBottom();
  }

  function appendBotMsg(text, confidence, source, sourceDoc) {
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
        '<span>' + fmtTime() + '</span>' +
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

    messagesEl.appendChild(div);
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
        messagesEl.appendChild(fDiv);
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
    if (escalationBannerEl) escalationBannerEl.textContent = t.agentConnectedBanner;
  }

  function showEscalationBanner() {
    escalationBannerEl = document.createElement('div');
    escalationBannerEl.className = 'nura-escalation-banner';
    escalationBannerEl.textContent = UI[currentLang].escalatingBanner;
    messagesEl.appendChild(escalationBannerEl);
    scrollBottom();
  }

  // ── Agent message polling ──────────────────────────────────────────────────
  function startAgentStream() {
    if (agentEventSource || !sessionId || !sessionToken) return;
    var streamUrl = API_BASE + '/session/' + encodeURIComponent(sessionId) +
      '/stream?session_token=' + encodeURIComponent(sessionToken);
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
        headers: { 'Content-Type': 'application/json' },
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
  applyLang('ar');
  setTimeout(function () { if (!isOpen) badge.style.display = 'flex'; }, 2000);

})();
