/* ==========================================================================
   00_util.js — أدوات عامة: DOM، التخزين، النص الغني مع الرياضيات، النوافذ، التنزيل
   ========================================================================== */
'use strict';
window.T27 = window.T27 || {};
(function () {
  const U = (T27.U = {});

  U.$ = (sel, root) => (root || document).querySelector(sel);
  U.$$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  /** إنشاء عنصر: el('div', {class:'x', html:'...', on:{click:fn}}, child1, 'text', ...) */
  U.el = function (tag, attrs, ...kids) {
    const n = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v === undefined || v === null || v === false) continue;
        if (k === 'class') n.className = v;
        else if (k === 'html') n.innerHTML = v;
        else if (k === 'text') n.textContent = v;
        else if (k === 'on') for (const [ev, fn] of Object.entries(v)) n.addEventListener(ev, fn);
        else if (k === 'style' && typeof v === 'object') Object.assign(n.style, v);
        else if (k === 'dataset') Object.assign(n.dataset, v);
        else if (v === true) n.setAttribute(k, '');
        else n.setAttribute(k, v);
      }
    }
    for (const c of kids.flat()) {
      if (c === null || c === undefined || c === false) continue;
      n.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return n;
  };

  U.esc = (s) =>
    String(s === undefined || s === null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

  /* ---------------- التخزين المحلي (آمن: لا يتعطل في الوضع الخاص) */
  const PFX = 't27.';
  U.store = {
    get(k, def) {
      try {
        const v = localStorage.getItem(PFX + k);
        return v === null ? def : JSON.parse(v);
      } catch (e) {
        return def;
      }
    },
    set(k, v) {
      try {
        localStorage.setItem(PFX + k, JSON.stringify(v));
        return true;
      } catch (e) {
        return false;
      }
    },
    del(k) {
      try {
        localStorage.removeItem(PFX + k);
      } catch (e) { /* تجاهل */ }
    },
  };

  /* ---------------- الرياضيات والنص الغني */
  const mathCache = new Map();
  U.math = function (tex) {
    if (mathCache.has(tex)) return mathCache.get(tex);
    let out;
    try {
      out = window.katex
        ? katex.renderToString(tex, { throwOnError: false, output: 'html', strict: 'ignore', trust: false })
        : U.esc(tex);
    } catch (e) {
      out = U.esc(tex);
    }
    mathCache.set(tex, out);
    return out;
  };

  /** يقسم النص على علامات $ غير المسبوقة بشرطة مائلة (بدون lookbehind لدعم Safari القديم) */
  function splitMath(s) {
    const parts = [];
    let buf = '';
    for (let i = 0; i < s.length; i++) {
      const ch = s[i];
      if (ch === '\\' && s[i + 1] === '$') {
        buf += '$';
        i++;
        continue;
      }
      if (ch === '$') {
        parts.push(buf);
        buf = '';
        continue;
      }
      buf += ch;
    }
    parts.push(buf);
    return parts;
  }

  function fmtText(t) {
    let h = U.esc(t);
    h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    h = h.replace(/\n/g, '<br>');
    return h;
  }

  /** نص عربي مع رياضيات $…$ و **غامق** وأسطر جديدة ← HTML */
  U.rich = function (src) {
    const s = String(src === undefined || src === null ? '' : src).replace(/\s+$/, '');
    const parts = splitMath(s);
    let html = '';
    parts.forEach((p, i) => {
      if (i % 2 === 1) html += '<span class="m" dir="ltr">' + U.math(p) + '</span>';
      else html += fmtText(p);
    });
    return html;
  };

  /** نص مختصر بلا وسوم (للقوائم والبحث) */
  U.plain = function (src) {
    return String(src || '').replace(/\$([^$]*)\$/g, ' $1 ').replace(/\\[a-zA-Z]+/g, ' ').replace(/[{}]/g, '').replace(/\s+/g, ' ').trim();
  };

  U.table = function (t) {
    const tb = U.el('table', { class: 'dt' });
    if (t.caption) tb.append(U.el('caption', { html: U.rich(t.caption) }));
    if (t.headers) {
      const tr = U.el('tr');
      t.headers.forEach((h) => tr.append(U.el('th', { html: U.rich(h) })));
      tb.append(U.el('thead', null, tr));
    }
    const body = U.el('tbody');
    (t.rows || []).forEach((r) => {
      const tr = U.el('tr');
      r.forEach((c, j) => tr.append(U.el(j === 0 && t.row_headers ? 'th' : 'td', { html: U.rich(c) })));
      body.append(tr);
    });
    tb.append(body);
    return tb;
  };

  /* ---------------- أرقام وأزمنة */
  U.parseNum = function (s) {
    if (s === null || s === undefined) return NaN;
    let t = String(s).trim().replace(/−/g, '-').replace(/\s+/g, '').replace(/,/g, '.');
    if (!t) return NaN;
    const fr = t.match(/^(-?)(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)$/);
    if (fr) {
      const d = parseFloat(fr[3]);
      return d === 0 ? NaN : (fr[1] === '-' ? -1 : 1) * (parseFloat(fr[2]) / d);
    }
    if (!/^-?(\d+\.?\d*|\.\d+)$/.test(t)) return NaN;
    return parseFloat(t);
  };
  U.fmtTime = function (sec) {
    sec = Math.max(0, Math.round(sec));
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
  };
  U.fmtDate = function (ts) {
    try {
      return new Date(ts).toLocaleString('ar-QA-u-nu-latn', { dateStyle: 'medium', timeStyle: 'short' });
    } catch (e) {
      return new Date(ts).toISOString().slice(0, 16).replace('T', ' ');
    }
  };
  U.pct = (a, b) => (b ? Math.round((1000 * a) / b) / 10 : 0);
  U.uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  U.shuffle = function (arr, rnd) {
    const a = arr.slice();
    const r = rnd || Math.random;
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(r() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  };
  U.sample = (arr, n, rnd) => U.shuffle(arr, rnd).slice(0, n);

  /* ---------------- تجزئة بسيطة لرمز المعلم (ليست أماناً حقيقياً، بل منع الدخول العرضي) */
  U.hash = function (str) {
    let h = 2166136261 >>> 0;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619) >>> 0;
    }
    return h.toString(16);
  };

  /* ---------------- التنزيل والقراءة */
  U.download = function (filename, text, mime) {
    const blob = new Blob([text], { type: mime || 'application/json;charset=utf-8' });
    const a = U.el('a', { href: URL.createObjectURL(blob), download: filename });
    document.body.append(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(a.href);
      a.remove();
    }, 1500);
  };
  U.readFiles = function (files) {
    return Promise.all(
      Array.from(files).map(
        (f) =>
          new Promise((res) => {
            const r = new FileReader();
            r.onload = () => res({ name: f.name, text: String(r.result) });
            r.onerror = () => res({ name: f.name, text: '' });
            r.readAsText(f, 'utf-8');
          })
      )
    );
  };
  U.csv = function (rows) {
    return '﻿' + rows.map((r) => r.map((c) => {
      const s = String(c === undefined || c === null ? '' : c);
      return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    }).join(',')).join('\n');
  };

  /* ---------------- النوافذ والرسائل */
  U.modal = function (opts) {
    const root = document.getElementById('modal-root');
    const back = U.el('div', { class: 'modal-back', role: 'dialog', 'aria-modal': 'true' });
    const box = U.el('div', { class: 'modal' });
    if (opts.title) box.append(U.el('h3', { html: U.rich(opts.title) }));
    if (opts.body instanceof Node) box.append(opts.body);
    else if (opts.body) box.append(U.el('div', { html: opts.body }));
    const acts = U.el('div', { class: 'acts' });
    const close = () => back.remove();
    (opts.actions || [{ label: 'حسناً' }]).forEach((a) => {
      acts.append(
        U.el('button', {
          class: 'btn ' + (a.kind || ''),
          type: 'button',
          text: a.label,
          on: {
            click: async () => {
              if (a.onClick) {
                const keep = await a.onClick(box);
                if (keep === false) return;
              }
              close();
            },
          },
        })
      );
    });
    box.append(acts);
    back.append(box);
    if (opts.dismiss !== false) back.addEventListener('click', (e) => { if (e.target === back) close(); });
    root.append(back);
    const first = box.querySelector('input,textarea,select,button');
    if (first) setTimeout(() => first.focus(), 30);
    return { close, box };
  };
  U.confirm = (title, body, okLabel) =>
    new Promise((res) => {
      U.modal({
        title,
        body,
        dismiss: false,
        actions: [
          { label: 'إلغاء', kind: 'ghost', onClick: () => res(false) },
          { label: okLabel || 'تأكيد', kind: 'maroon', onClick: () => res(true) },
        ],
      });
    });
  let toastTimer = null;
  U.toast = function (msg) {
    let t = document.querySelector('.toast');
    if (!t) {
      t = U.el('div', { class: 'toast', role: 'status' });
      document.body.append(t);
    }
    t.textContent = msg;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.remove(), 2600);
  };
  U.base64ToBytes = function (b64) {
    const bin = atob(b64);
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  };
})();
