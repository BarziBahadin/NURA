(function () {
  'use strict';

  var script = document.currentScript;

  function bootLoader() {
    if (window.__NURA_WIDGET_LOADER_LOADED__ || window.__NURA_WIDGET_LOADED__) return;
    window.__NURA_WIDGET_LOADER_LOADED__ = true;

    var position = (script && script.getAttribute('data-position')) || 'bottom-left';
    var primary = (script && script.getAttribute('data-primary')) || '#f97316';
    var title = (script && script.getAttribute('data-title')) || 'NURA';
    var fullSrc = (script && script.getAttribute('data-widget-src')) || deriveWidgetSrc(script && script.src);

    var host = document.createElement('div');
    host.id = 'nura-widget-loader';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.setAttribute('aria-label', 'Open chat');
    btn.textContent = title;
    btn.style.cssText = [
      'position:fixed',
      'bottom:calc(28px + env(safe-area-inset-bottom,0px))',
      position === 'bottom-right' ? 'right:28px' : 'left:28px',
      'width:60px',
      'height:60px',
      'border-radius:50%',
      'border:0',
      'background:linear-gradient(135deg,#111827,' + primary + ')',
      'color:#fff',
      'font:900 12px/1.1 system-ui,-apple-system,Segoe UI,sans-serif',
      'cursor:pointer',
      'z-index:2147483640',
      'box-shadow:0 14px 34px rgba(17,24,39,.28),0 4px 18px rgba(249,115,22,.36)',
      '-webkit-tap-highlight-color:transparent',
    ].join(';');

    btn.addEventListener('click', function () {
      btn.disabled = true;
      btn.style.opacity = '0.72';
      loadFullWidget(fullSrc, host);
    });

    host.appendChild(btn);
    document.body.appendChild(host);
  }

  function deriveWidgetSrc(src) {
    if (!src) return '/widget.js';
    return src.replace(/widget-loader\.js(?:\?.*)?$/, 'widget.js');
  }

  function copyDataAttributes(target) {
    if (!script) return;
    Array.prototype.slice.call(script.attributes).forEach(function (attr) {
      if (attr.name.indexOf('data-') === 0 && attr.name !== 'data-widget-src') {
        target.setAttribute(attr.name, attr.value);
      }
    });
  }

  function loadFullWidget(src, host) {
    var full = document.createElement('script');
    full.src = src;
    full.async = true;
    copyDataAttributes(full);
    full.setAttribute('data-auto-open', 'true');
    full.onload = function () {
      if (host && host.parentNode) host.parentNode.removeChild(host);
    };
    full.onerror = function () {
      if (host) {
        var btn = host.querySelector('button');
        if (btn) {
          btn.disabled = false;
          btn.style.opacity = '1';
        }
      }
    };
    document.body.appendChild(full);
  }

  if (document.body) {
    bootLoader();
  } else {
    document.addEventListener('DOMContentLoaded', bootLoader, { once: true });
  }
})();
