/* ==========================================================================
   20_widgets.js — عناصر التفاعل: حاسبة TIMSS، لوحة الأرقام، السحب والإفلات، الرسم على الشبكة
   ========================================================================== */
'use strict';
(function () {
  const U = T27.U;
  const el = U.el;

  /* ======================================================================
     حاسبة TIMSS (الصف الثامن): العمليات الأربع، √، الإشارة السالبة،
     وتنفّذ عملية واحدة في كل مرة (بلا أسبقية للعمليات): 2 + 3 × 4 = 20
     ====================================================================== */
  const Calc = (T27.Calc = {});
  let cRoot = null;
  let st = null;
  const reset = () => (st = { cur: '0', acc: null, op: null, fresh: true, err: false });
  reset();

  function fmt(n) {
    if (!isFinite(n)) return 'Error';
    if (n !== 0 && (Math.abs(n) >= 1e10 || Math.abs(n) < 1e-8)) return n.toExponential(5);
    return String(parseFloat(n.toPrecision(10)));
  }
  const curVal = () => parseFloat(st.cur);
  function apply(a, op, b) {
    if (op === '+') return a + b;
    if (op === '−') return a - b;
    if (op === '×') return a * b;
    if (op === '÷') return b === 0 ? NaN : a / b;
    return b;
  }
  function error() {
    st.cur = 'Error';
    st.err = true;
    st.op = null;
    st.acc = null;
    st.fresh = true;
    render();
  }
  Calc.press = function (k) {
    if (st.err && k !== 'C') return render();
    if ('0123456789'.includes(k)) {
      if (st.fresh) {
        st.cur = k;
        st.fresh = false;
      } else if (st.cur.replace(/[-.]/g, '').length < 12) {
        if (st.cur === '0') st.cur = k;
        else if (st.cur === '-0') st.cur = '-' + k;
        else st.cur += k;
      }
    } else if (k === '.') {
      if (st.fresh) {
        st.cur = '0.';
        st.fresh = false;
      } else if (!st.cur.includes('.')) st.cur += '.';
    } else if (k === '±') {
      if (st.fresh && st.op) {
        st.cur = '-0';
        st.fresh = false;
      } else st.cur = st.cur.startsWith('-') ? st.cur.slice(1) : '-' + st.cur;
    } else if ('+−×÷'.includes(k)) {
      if (st.op && !st.fresh) {
        const r = apply(st.acc, st.op, curVal());
        if (!isFinite(r)) return error();
        st.cur = fmt(r);
        st.acc = r;
      } else st.acc = curVal();
      st.op = k;
      st.fresh = true;
    } else if (k === '=') {
      if (st.op) {
        const r = apply(st.acc, st.op, curVal());
        if (!isFinite(r)) return error();
        st.cur = fmt(r);
        st.acc = null;
        st.op = null;
        st.fresh = true;
      }
    } else if (k === '√') {
      const v = curVal();
      if (v < 0 || !isFinite(v)) return error();
      st.cur = fmt(Math.sqrt(v));
      st.fresh = true;
    } else if (k === 'C') reset();
    else if (k === '⌫') {
      if (!st.fresh) {
        st.cur = st.cur.length > 1 ? st.cur.slice(0, -1) : '0';
        if (st.cur === '-' || st.cur === '') st.cur = '0';
      }
    }
    render();
  };
  Calc.display = () => st.cur;
  function render() {
    if (!cRoot) return;
    cRoot.querySelector('.disp span').textContent = st.cur;
    cRoot.querySelector('.disp small').textContent = st.op ? fmt(st.acc) + ' ' + st.op : '';
  }
  function build() {
    const keys = [
      ['7', '8', '9', '÷'],
      ['4', '5', '6', '×'],
      ['1', '2', '3', '−'],
      ['0', '.', '±', '+'],
      ['√', 'C', '⌫', '='],
    ];
    const grid = el('div', { class: 'keys' });
    keys.flat().forEach((k) => {
      const cls = '+−×÷√'.includes(k) ? 'op' : k === '=' ? 'eq' : k === 'C' ? 'clr' : '';
      grid.append(el('button', { type: 'button', class: cls, 'aria-label': k === '±' ? 'تغيير الإشارة' : k, text: k, on: { click: () => Calc.press(k) } }));
    });
    const bar = el('div', { class: 'bar' }, el('span', { text: 'الحاسبة ⇕' }), el('button', { type: 'button', 'aria-label': 'إغلاق الحاسبة', text: '×', on: { click: () => Calc.hide() } }));
    cRoot = el('div', { class: 'calc', role: 'dialog', 'aria-label': 'الحاسبة', tabindex: '-1' }, bar, el('div', { class: 'disp' }, el('small'), el('span', { text: '0' })), grid);
    // سحب النافذة
    let drag = null;
    bar.addEventListener('pointerdown', (e) => {
      if (e.target.tagName === 'BUTTON') return;
      const r = cRoot.getBoundingClientRect();
      drag = { dx: e.clientX - r.left, dy: e.clientY - r.top };
      bar.setPointerCapture(e.pointerId);
    });
    bar.addEventListener('pointermove', (e) => {
      if (!drag) return;
      cRoot.style.left = Math.max(0, Math.min(window.innerWidth - 270, e.clientX - drag.dx)) + 'px';
      cRoot.style.top = Math.max(0, Math.min(window.innerHeight - 120, e.clientY - drag.dy)) + 'px';
    });
    bar.addEventListener('pointerup', () => (drag = null));
    cRoot.addEventListener('keydown', (e) => {
      const map = { '*': '×', x: '×', '/': '÷', '-': '−', '+': '+', Enter: '=', '=': '=', Backspace: '⌫', Escape: 'C', '.': '.', ',': '.' };
      const k = /^[0-9]$/.test(e.key) ? e.key : map[e.key];
      if (k) {
        e.preventDefault();
        Calc.press(k);
      }
    });
    document.getElementById('calc-root').append(cRoot);
    render();
  }
  Calc.show = function () {
    if (!cRoot) build();
    cRoot.classList.remove('hidden');
    cRoot.focus();
  };
  Calc.hide = () => cRoot && cRoot.classList.add('hidden');
  Calc.toggle = () => (cRoot && !cRoot.classList.contains('hidden') ? Calc.hide() : Calc.show());
  Calc.reset = () => {
    reset();
    render();
  };

  /* ======================================================================
     لوحة الأرقام (تحاكي لوحة eTIMSS) — تعمل على آخر خانة رقمية نشطة
     ====================================================================== */
  T27.NumPad = function (inputs, opts) {
    opts = opts || {};
    let active = inputs[0];
    const coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
    inputs.forEach((inp) => {
      inp.setAttribute('inputmode', coarse ? 'none' : 'decimal');
      inp.addEventListener('focus', () => (active = inp));
      inp.addEventListener('input', () => {
        const clean = inp.value.replace(/[^0-9.\-−\/,]/g, '').slice(0, 14);
        if (clean !== inp.value) inp.value = clean;
        opts.onChange && opts.onChange();
      });
    });
    const keys = ['7', '8', '9', '⌫', '4', '5', '6', '−', '1', '2', '3', opts.allowFraction ? '/' : '.', '0', opts.allowFraction ? '.' : null, 'مسح'].filter(Boolean);
    const pad = el('div', { class: 'numpad', role: 'group', 'aria-label': 'لوحة الأرقام' });
    keys.forEach((k) => {
      pad.append(
        el('button', {
          type: 'button',
          class: k === 'مسح' ? 'wide act' : k === '⌫' ? 'act' : '',
          text: k,
          on: {
            mousedown: (e) => e.preventDefault(),
            click: () => {
              if (!active || active.disabled) return;
              let v = active.value;
              if (k === '⌫') v = v.slice(0, -1);
              else if (k === 'مسح') v = '';
              else if (k === '−') v = v.startsWith('-') || v.startsWith('−') ? v.slice(1) : '-' + v;
              else if (k === '.' && v.includes('.')) return;
              else if (v.replace(/[^0-9]/g, '').length < 12) v += k;
              active.value = v;
              active.dispatchEvent(new Event('input'));
              if (!coarse) active.focus();
            },
          },
        })
      );
    });
    return pad;
  };

  /* ======================================================================
     محرك السحب والإفلات (مؤشر/لمس) + وضع «انقر ثم انقر» لإمكانية الوصول
     ====================================================================== */
  const DnD = (T27.DnD = {});
  let tapSel = null; // {cardId, from, host}
  DnD.clearTap = () => {
    tapSel = null;
    U.$$('.dcard.sel').forEach((n) => n.classList.remove('sel'));
  };
  /**
   * cardEl: عنصر البطاقة، info: {cardId, from}، host: عنصر السؤال
   * onDrop(targetZoneEl|null, info)
   */
  DnD.bind = function (cardEl, info, host, onDrop, isLocked) {
    let ghost = null;
    let start = null;
    let moved = false;
    cardEl.addEventListener('pointerdown', (e) => {
      if (isLocked()) return;
      if (e.button !== undefined && e.button !== 0) return;
      start = { x: e.clientX, y: e.clientY };
      moved = false;
      cardEl.setPointerCapture(e.pointerId);
    });
    cardEl.addEventListener('pointermove', (e) => {
      if (!start) return;
      if (!moved && Math.hypot(e.clientX - start.x, e.clientY - start.y) < 6) return;
      if (!moved) {
        moved = true;
        DnD.clearTap();
        ghost = cardEl.cloneNode(true);
        ghost.classList.add('ghost');
        ghost.style.width = cardEl.offsetWidth + 'px';
        document.body.append(ghost);
        cardEl.classList.add('placeholder');
      }
      ghost.style.left = e.clientX - cardEl.offsetWidth / 2 + 'px';
      ghost.style.top = e.clientY - cardEl.offsetHeight / 2 + 'px';
      U.$$('[data-drop]', host).forEach((z) => z.classList.remove('hot'));
      const z = zoneAt(e.clientX, e.clientY, host);
      if (z) z.classList.add('hot');
    });
    const finish = (e) => {
      if (!start) return;
      const wasMoved = moved;
      start = null;
      moved = false;
      U.$$('[data-drop]', host).forEach((z) => z.classList.remove('hot'));
      if (ghost) {
        ghost.remove();
        ghost = null;
      }
      cardEl.classList.remove('placeholder');
      if (wasMoved) {
        const z = e && e.type === 'pointerup' ? zoneAt(e.clientX, e.clientY, host) : null;
        onDrop(z, info);
      } else {
        // نقرة: (1) نقر البطاقة المحددة نفسها داخل خانة ← إرجاعها إلى البطاقات
        if (tapSel && tapSel.cardId === info.cardId && tapSel.from === info.from) {
          DnD.clearTap();
          if (info.from !== 'tray') onDrop('tray', info);
          return;
        }
        // (2) توجد بطاقة محددة ونُقرت بطاقة موضوعة في خانة أخرى ← انقل المحددة إلى تلك الخانة
        if (tapSel && tapSel.host === host && info.from !== 'tray') {
          const z = cardEl.closest('[data-drop]');
          if (z) {
            const sel = tapSel;
            DnD.clearTap();
            onDrop(z, sel);
            return;
          }
        }
        // (3) تحديد البطاقة
        DnD.clearTap();
        tapSel = { ...info, host };
        cardEl.classList.add('sel');
      }
    };
    cardEl.addEventListener('pointerup', finish);
    cardEl.addEventListener('pointercancel', finish);
    cardEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        DnD.clearTap();
        tapSel = { ...info, host };
        cardEl.classList.add('sel');
      }
    });
  };
  /** منطقة إفلات: عند النقر عليها وهناك بطاقة محددة ← نقلها */
  DnD.zone = function (zoneEl, host, onDrop, isLocked) {
    zoneEl.setAttribute('data-drop', '1');
    zoneEl.addEventListener('click', (e) => {
      if (isLocked() || !tapSel || tapSel.host !== host) return;
      if (e.target.closest('.dcard')) return; // النقر على بطاقة يُعالَج في bind
      const info = tapSel;
      DnD.clearTap();
      onDrop(zoneEl, info);
    });
  };
  function zoneAt(x, y, host) {
    const n = document.elementFromPoint(x, y);
    const z = n && n.closest('[data-drop]');
    return z && host.contains(z) ? z : null;
  }

  /* ======================================================================
     الرسم على المستوى الإحداثي (تعيين نقاط/مضلع/قطعة) مع الالتقاط إلى الشبكة
     ====================================================================== */
  T27.GridPlot = function (item, host, state, onChange, isLocked) {
    const g = item.grid;
    const u = 34;
    const pad = 30;
    const W = (g.xmax - g.xmin) * u + 2 * pad;
    const H = (g.ymax - g.ymin) * u + 2 * pad;
    const X = (x) => pad + (x - g.xmin) * u;
    const Y = (y) => pad + (g.ymax - y) * u;
    const NS = 'http://www.w3.org/2000/svg';
    const mk = (tag, attrs) => {
      const n = document.createElementNS(NS, tag);
      for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v);
      return n;
    };
    const svg = mk('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'شبكة إحداثية للرسم', direction: 'ltr' });
    const wrap = el('div', { class: 'gridplot' });
    wrap.append(svg);
    const tools = el(
      'div',
      { class: 'row' },
      el('button', { type: 'button', class: 'btn alt sm', text: '↶ تراجع', on: { click: () => { if (!isLocked() && state.points.length) { state.points.pop(); draw(); onChange(); } } } }),
      el('button', { type: 'button', class: 'btn ghost sm', text: 'مسح الكل', on: { click: () => { if (!isLocked()) { state.points = []; draw(); onChange(); } } } }),
      el('span', { class: 'muted small', text: `النقاط المحددة: ` }, el('b', { class: 'cnt', text: '0' }), el('span', { text: item.count ? ` من ${item.count}` : '' }))
    );
    wrap.append(tools);
    host.append(wrap);

    function base() {
      svg.innerHTML = '';
      const gl = mk('g', { stroke: '#D5DAE3', 'stroke-width': 1 });
      for (let x = g.xmin; x <= g.xmax; x++) gl.append(mk('line', { x1: X(x), y1: Y(g.ymin), x2: X(x), y2: Y(g.ymax) }));
      for (let y = g.ymin; y <= g.ymax; y++) gl.append(mk('line', { x1: X(g.xmin), y1: Y(y), x2: X(g.xmax), y2: Y(y) }));
      svg.append(gl);
      const ax = g.xmin <= 0 && 0 <= g.xmax ? 0 : g.xmin;
      const ay = g.ymin <= 0 && 0 <= g.ymax ? 0 : g.ymin;
      svg.append(mk('line', { x1: X(g.xmin) - 6, y1: Y(ay), x2: X(g.xmax) + 10, y2: Y(ay), stroke: '#39465A', 'stroke-width': 2 }));
      svg.append(mk('line', { x1: X(ax), y1: Y(g.ymin) + 6, x2: X(ax), y2: Y(g.ymax) - 10, stroke: '#39465A', 'stroke-width': 2 }));
      const txt = (x, y, s, anchor, extra) => {
        const t = mk('text', { x, y, 'font-size': 12, fill: '#39465A', 'text-anchor': anchor || 'middle', 'dominant-baseline': 'central', direction: 'ltr', ...(extra || {}) });
        t.textContent = s;
        svg.append(t);
      };
      for (let x = g.xmin; x <= g.xmax; x++) if (x !== 0) txt(X(x), Y(ay) + 14, String(x).replace('-', '−'));
      for (let y = g.ymin; y <= g.ymax; y++) if (y !== 0) txt(X(ax) - 10, Y(y), String(y).replace('-', '−'), 'end');
      txt(X(ax) - 9, Y(ay) + 13, '0', 'end');
      txt(X(g.xmax) + 14, Y(ay) - 12, 'x', 'middle', { 'font-size': 16, 'font-style': 'italic' });
      txt(X(ax) + 13, Y(g.ymax) - 14, 'y', 'middle', { 'font-size': 16, 'font-style': 'italic' });
      const given = item.given || {};
      (given.polygons || []).forEach((pg) => {
        const pts = pg.points.map((p) => `${X(p[0])},${Y(p[1])}`).join(' ');
        svg.append(mk('polygon', { points: pts, fill: '#1B365D', 'fill-opacity': 0.14, stroke: '#1B365D', 'stroke-width': 2.4 }));
        const cx = pg.points.reduce((s, p) => s + X(p[0]), 0) / pg.points.length;
        const cy = pg.points.reduce((s, p) => s + Y(p[1]), 0) / pg.points.length;
        (pg.labels || []).forEach((lab, k) => {
          const px = X(pg.points[k][0]);
          const py = Y(pg.points[k][1]);
          const d = Math.hypot(px - cx, py - cy) || 1;
          txt(px + ((px - cx) / d) * 16, py + ((py - cy) / d) * 16, lab, 'middle', { 'font-size': 15, 'font-weight': 700, fill: '#1B365D' });
        });
      });
      (given.segments || []).forEach((sg) => svg.append(mk('line', { x1: X(sg.points[0][0]), y1: Y(sg.points[0][1]), x2: X(sg.points[1][0]), y2: Y(sg.points[1][1]), stroke: '#1B365D', 'stroke-width': 2.4 })));
      (given.points || []).forEach((p) => {
        svg.append(mk('circle', { cx: X(p.x), cy: Y(p.y), r: 5, fill: '#1B365D' }));
        if (p.label) txt(X(p.x) + 10, Y(p.y) - 12, p.label, 'start', { 'font-size': 14, 'font-weight': 700, fill: '#1B365D' });
      });
    }
    const layer = mk('g');
    const hits = mk('g');
    function draw() {
      layer.innerHTML = '';
      const P = state.points;
      const col = state.mark || '#8A1538';
      if (item.mode === 'polygon' && P.length >= 2) {
        const pts = P.map((p) => `${X(p[0])},${Y(p[1])}`).join(' ');
        const closed = item.count && P.length >= item.count;
        layer.append(mk(closed ? 'polygon' : 'polyline', { points: pts, fill: closed ? col : 'none', 'fill-opacity': closed ? 0.14 : 0, stroke: col, 'stroke-width': 2.6 }));
      }
      if (item.mode === 'segment' && P.length >= 2) layer.append(mk('line', { x1: X(P[0][0]), y1: Y(P[0][1]), x2: X(P[1][0]), y2: Y(P[1][1]), stroke: col, 'stroke-width': 2.8 }));
      P.forEach((p, k) => {
        layer.append(mk('circle', { cx: X(p[0]), cy: Y(p[1]), r: 6.5, fill: col, stroke: '#fff', 'stroke-width': 1.5 }));
        const t = mk('text', { x: X(p[0]) + 9, y: Y(p[1]) - 11, 'font-size': 11, fill: col, direction: 'ltr' });
        t.textContent = `(${String(p[0]).replace('-', '−')}, ${String(p[1]).replace('-', '−')})`;
        layer.append(t);
      });
      (state.keyPoints || []).forEach((p) => layer.append(mk('circle', { cx: X(p[0]), cy: Y(p[1]), r: 9, fill: 'none', stroke: '#2E7D32', 'stroke-width': 2.5, 'stroke-dasharray': '4 3' })));
      const c = wrap.querySelector('.cnt');
      if (c) c.textContent = String(P.length);
    }
    base();
    svg.append(layer);
    for (let x = g.xmin; x <= g.xmax; x++) {
      for (let y = g.ymin; y <= g.ymax; y++) {
        const h = mk('circle', { cx: X(x), cy: Y(y), r: 11, class: 'hitpt', 'data-x': x, 'data-y': y });
        const title = mk('title');
        title.textContent = `(${x}, ${y})`;
        h.append(title);
        hits.append(h);
      }
    }
    svg.append(hits);
    hits.addEventListener('click', (e) => {
      if (isLocked()) return;
      const t = e.target.closest('.hitpt');
      if (!t) return;
      const x = +t.dataset.x;
      const y = +t.dataset.y;
      const k = state.points.findIndex((p) => p[0] === x && p[1] === y);
      if (k >= 0) state.points.splice(k, 1);
      else {
        if (item.count && state.points.length >= item.count) {
          U.toast(`حددت ${item.count} نقاط. استعمل «تراجع» لتغيير نقطة.`);
          return;
        }
        state.points.push([x, y]);
      }
      draw();
      onChange();
    });
    draw();
    return { redraw: draw };
  };
})();
