/* ==========================================================================
   30_items.js — عرض البنود وجمع الإجابات وتصحيحها + التغذية الراجعة + نسخة الطباعة
   ========================================================================== */
'use strict';
(function () {
  const U = T27.U;
  const D = T27.D;
  const el = U.el;
  const I = (T27.I = {});
  const LET = 'ABCD';

  const hasAr = (s) => /[؀-ۿ]/.test(String(s || ''));
  const unitEl = (u) => (u ? el('span', { class: 'unit', dir: hasAr(u) ? 'rtl' : 'ltr', text: u }) : null);

  /* ============================================================ التصحيح */
  function numEq(input, spec) {
    const v = U.parseNum(input);
    if (isNaN(v)) return false;
    const tol = spec.tol ? Number(spec.tol) : 1e-9;
    const targets = [spec.value].concat(spec.accept || []);
    return targets.some((t) => {
      const tv = U.parseNum(String(t));
      return !isNaN(tv) && Math.abs(v - tv) <= tol + 1e-12;
    });
  }
  function checkFn(expr, n) {
    const args = [];
    for (let k = 1; k <= n; k++) args.push('s' + k);
    try {
      return new Function(...args, '"use strict"; return (' + expr + ');');
    } catch (e) {
      return null;
    }
  }
  const ptKey = (p) => p[0] + ',' + p[1];

  /** يعيد {points, max, correct, pending, choiceOk} */
  I.score = function (item, r) {
    const max = item.points || 1;
    const res = (pts, extra) => Object.assign({ points: pts, max, correct: pts >= max, pending: false }, extra || {});
    if (r === null || r === undefined) return res(0, { correct: false, blank: true });
    switch (item.format) {
      case 'mc':
        return res(r === item.key ? max : 0);
      case 'numeric':
        return res(numEq(r, item.answer) ? max : 0);
      case 'multi_numeric': {
        const oks = item.fields.map((f, k) => numEq((r || [])[k], f));
        const n = oks.filter(Boolean).length;
        const mode = (item.scoring || {}).mode || 'all';
        let pts = 0;
        if (mode === 'each') pts = n;
        else if (mode === 'partial') pts = n === oks.length ? max : n >= ((item.scoring || {}).partial_min || 1) ? 1 : 0;
        else pts = n === oks.length ? max : 0;
        return res(pts, { fieldOk: oks });
      }
      case 'dragdrop_slots': {
        const slots = (item.template.match(/\[\[(\w+)\]\]/g) || []).map((s) => s.slice(2, -2));
        if (slots.some((s) => !r[s])) return res(0, { correct: false });
        if (item.check) {
          const byId = Object.fromEntries(item.cards.map((c) => [c.id, c]));
          const vals = slots.map((s) => (byId[r[s]] || {}).value);
          const fn = checkFn(item.check, slots.length);
          let ok = false;
          try {
            ok = !!(fn && fn(...vals));
          } catch (e) {
            ok = false;
          }
          return res(ok ? max : 0);
        }
        return res(slots.every((s) => r[s] === item.key[s]) ? max : 0);
      }
      case 'dragdrop_order':
        return res(Array.isArray(r) && item.key.every((c, k) => r[k] === c) ? max : 0);
      case 'dragdrop_categorize': {
        const cards = item.cards.map((c) => c.id);
        const n = cards.filter((c) => r[c] === item.key[c]).length;
        const mode = (item.scoring || {}).mode || 'all';
        if (mode === 'partial') return res(n === cards.length ? max : n >= ((item.scoring || {}).partial_min || cards.length - 1) ? 1 : 0);
        return res(n === cards.length ? max : 0, { cardOk: Object.fromEntries(cards.map((c) => [c, r[c] === item.key[c]])) });
      }
      case 'grid_plot': {
        const pts = (r || []).map(ptKey).sort();
        const key = item.key.map(ptKey).sort();
        return res(pts.length === key.length && pts.every((p, k) => p === key[k]) ? max : 0);
      }
      case 'select_explain': {
        const choiceOk = r.choice === item.key;
        if (typeof r.human === 'number') return res(r.human, { choiceOk, scorer: r.scorer });
        return Object.assign(res(0, { choiceOk }), { pending: !!(r.choice || r.text), correct: null });
      }
      case 'cr_explain':
        if (typeof r.human === 'number') return res(r.human, { scorer: r.scorer });
        return Object.assign(res(0), { pending: !!(r.text && r.text.trim()), correct: null });
    }
    return res(0);
  };

  /** هل أجاب الطالب؟ */
  I.answered = function (item, r) {
    if (r === null || r === undefined) return false;
    switch (item.format) {
      case 'mc':
        return !!r;
      case 'numeric':
        return String(r).trim() !== '';
      case 'multi_numeric':
        return Array.isArray(r) && r.some((v) => v && String(v).trim());
      case 'dragdrop_slots':
      case 'dragdrop_categorize':
        return Object.keys(r).length > 0;
      case 'dragdrop_order':
        return Array.isArray(r) && r.some(Boolean);
      case 'grid_plot':
        return Array.isArray(r) && r.length > 0;
      case 'select_explain':
        return !!(r.choice || (r.text && r.text.trim()));
      case 'cr_explain':
        return !!(r.text && r.text.trim());
    }
    return false;
  };

  /** تمثيل نصي للإجابة الصحيحة */
  I.keyText = function (item) {
    const byId = item.cards ? Object.fromEntries(item.cards.map((c) => [c.id, c])) : {};
    switch (item.format) {
      case 'mc':
      case 'select_explain':
        // عزل «A)» باتجاه LTR (U+2066 … U+2069) حتى لا تنقلب إلى «(A» داخل السطر العربي
        return '⁦' + item.key + ')⁩ ' + (item.options[LET.indexOf(item.key)] || '');
      case 'numeric': {
        // العدد مع وحدة لاتينية يُعزل LTR فيظهر «12 cm» لا «cm 12»؛ والوحدة العربية تبقى في السياق العربي
        const u = item.answer.unit;
        const v = '$' + String(item.answer.value) + '$';
        if (!u) return v;
        return hasAr(u) ? v + ' ' + u : '⁦' + v + ' ' + u + '⁩';
      }
      case 'multi_numeric':
        return item.fields.map((f) => f.label + ' $= ' + f.value + '$').join('، ');
      case 'dragdrop_slots':
        return item.template.replace(/\[\[(\w+)\]\]/g, (m, s) => ' ' + ((byId[item.key[s]] || {}).text || '?') + ' ');
      case 'dragdrop_order':
        return item.key.map((c) => (byId[c] || {}).text).join('، ');
      case 'dragdrop_categorize': {
        const cats = {};
        Object.entries(item.key).forEach(([c, cat]) => (cats[cat] = cats[cat] || []).push((byId[c] || {}).text));
        return Object.entries(cats).map(([cat, cs]) => '**' + cat + ':** ' + cs.join('، ')).join('\n');
      }
      case 'grid_plot':
        return item.key.map((p) => '$(' + p[0] + ', ' + p[1] + ')$').join('، ');
      case 'cr_explain':
        return item.model_answer || '';
    }
    return '';
  };

  /* ============================================================ العرض */
  /**
   * ctx: {mode: 'practice'|'test'|'review'|'teacher', response, onChange, number, total, meta:boolean}
   * يعيد متحكماً: {get(), set(r), answered(), lock(bool), reveal(result)}
   */
  I.render = function (item, host, ctx) {
    ctx = ctx || {};
    host.innerHTML = '';
    let locked = false;
    const c = {
      locked: () => locked,
      changed: () => ctx.onChange && ctx.onChange(),
      response: ctx.response === undefined ? null : JSON.parse(JSON.stringify(ctx.response)),
    };
    const frame = el('div', { class: 'item-frame', 'data-id': item.id });
    const head = el('div', { class: 'item-head' });
    if (ctx.number) head.append(el('span', { class: 'qn', text: ctx.total ? `السؤال ${ctx.number} من ${ctx.total}` : `السؤال ${ctx.number}` }));
    if (ctx.meta) {
      head.append(
        el('span', { class: 'badge', text: D.topicShort(item.topic) }),
        el('span', { class: 'badge m', text: D.cogName(item.cognitive) + ' · ' + D.areaName(item.cognitive, item.area) }),
        el('span', { class: 'badge', text: D.diffName(item.difficulty) }),
        el('span', { class: 'badge warn', text: D.bmName(item.benchmark) })
      );
    }
    if (ctx.showId) head.append(el('span', { class: 'spacer' }), el('code', { class: 'small muted', text: item.id }));
    frame.append(head);
    frame.append(el('div', { class: 'stem', html: U.rich(item.stem) }));
    if (item.table) frame.append(U.table(item.table));
    if (item.figure_svg) frame.append(el('div', { class: 'figure', html: item.figure_svg }));
    if (ctx.mode !== 'review' && ctx.mode !== 'teacher') frame.append(el('div', { class: 'howto', text: '🛈 ' + (D.HOWTO[item.format] || '') }));
    const resp = el('div', { class: 'response' });
    frame.append(resp);
    host.append(frame);
    const make = RENDER[item.format];
    const ctl = make ? make(item, resp, c) : { get: () => null, set() {}, answered: () => false, reveal() {} };
    ctl.lock = function (v) {
      locked = !!v;
      frame.classList.toggle('locked', locked);
      U.$$('input,textarea', frame).forEach((n) => (n.disabled = locked));
    };
    ctl.frame = frame;
    return ctl;
  };

  const RENDER = {};

  RENDER.mc = function (item, host, c) {
    let sel = c.response;
    const svgs = item.options_svg || [];
    const short = !svgs.some(Boolean) && item.options.every((o) => U.plain(o).length <= 16);
    const list = el('div', { class: 'opts' + (short ? ' cols2' : ''), role: 'radiogroup', 'aria-label': 'البدائل' });
    const btns = item.options.map((o, i) => {
      const L = LET[i];
      const b = el('button', { type: 'button', class: 'opt', role: 'radio', 'aria-checked': String(sel === L), 'data-l': L },
        el('span', { class: 'opt-l', text: L }),
        el('span', { class: 'opt-t', html: svgs[i] || U.rich(o) }));
      b.addEventListener('click', () => {
        if (c.locked()) return;
        sel = L;
        sync();
        c.changed();
      });
      list.append(b);
      return b;
    });
    function sync() {
      btns.forEach((b) => b.setAttribute('aria-checked', String(b.dataset.l === sel)));
    }
    host.append(list);
    return {
      get: () => sel,
      set: (r) => {
        sel = r;
        sync();
      },
      answered: () => !!sel,
      reveal: () =>
        btns.forEach((b) => {
          b.classList.toggle('is-ok', b.dataset.l === item.key);
          b.classList.toggle('is-bad', b.dataset.l === sel && sel !== item.key);
        }),
    };
  };

  RENDER.numeric = function (item, host, c) {
    const inp = el('input', { class: 'numbox', type: 'text', autocomplete: 'off', spellcheck: 'false', dir: 'ltr', 'aria-label': 'الإجابة' });
    if (c.response) inp.value = c.response;
    host.append(el('div', { class: 'numrow' }, el('div', { class: 'numfield' }, el('span', { class: 'lab', text: 'الإجابة:' }), inp, unitEl(item.answer.unit))));
    host.append(T27.NumPad([inp], { allowFraction: item.answer.allow_fraction, onChange: c.changed }));
    return {
      get: () => (inp.value.trim() ? inp.value.trim() : null),
      set: (r) => (inp.value = r || ''),
      answered: () => !!inp.value.trim(),
      reveal: (res) => {
        inp.classList.toggle('is-ok', !!res.correct);
        inp.classList.toggle('is-bad', !res.correct);
      },
    };
  };

  RENDER.multi_numeric = function (item, host, c) {
    const prev = c.response || [];
    const inputs = item.fields.map((f, k) => {
      const inp = el('input', { class: 'numbox sm', type: 'text', autocomplete: 'off', dir: 'ltr', 'aria-label': U.plain(f.label) });
      if (prev[k]) inp.value = prev[k];
      return inp;
    });
    const row = el('div', { class: 'numrow' });
    item.fields.forEach((f, k) => row.append(el('div', { class: 'numfield' }, el('span', { class: 'lab', html: U.rich(f.label) + ' =' }), inputs[k], unitEl(f.unit))));
    host.append(row, T27.NumPad(inputs, { onChange: c.changed }));
    return {
      get: () => {
        const v = inputs.map((i) => i.value.trim());
        return v.some(Boolean) ? v : null;
      },
      set: (r) => inputs.forEach((i, k) => (i.value = (r || [])[k] || '')),
      answered: () => inputs.some((i) => i.value.trim()),
      reveal: (res) =>
        inputs.forEach((i, k) => {
          const ok = res.fieldOk ? res.fieldOk[k] : res.correct;
          i.classList.toggle('is-ok', !!ok);
          i.classList.toggle('is-bad', !ok);
        }),
    };
  };

  function cardNode(card, from, host, onDrop, c) {
    const n = el('div', { class: 'dcard', tabindex: '0', role: 'button', 'data-card': card.id, 'aria-label': U.plain(card.text), html: U.rich(card.text) });
    T27.DnD.bind(n, { cardId: card.id, from }, host, onDrop, c.locked);
    return n;
  }

  RENDER.dragdrop_slots = function (item, host, c) {
    const byId = Object.fromEntries(item.cards.map((x) => [x.id, x]));
    let state = Object.assign({}, c.response || {});
    const tray = el('div', { class: 'tray', 'data-tray': '1', 'aria-label': 'البطاقات' });
    const tpl = el('div', { class: 'tpl' + (item.template_dir === 'rtl' ? ' rtl' : '') });
    host.append(el('div', { class: 'tray-label', text: 'البطاقات:' }), tray, tpl);
    let revealed = null;
    function onDrop(zone, info) {
      if (!zone) return render();
      const toTray = zone === 'tray' || (zone.dataset && zone.dataset.tray);
      if (toTray) {
        if (info.from !== 'tray') delete state[info.from];
      } else {
        const sid = zone.dataset.slot;
        const prev = state[sid];
        if (info.from !== 'tray') {
          if (prev) state[info.from] = prev;
          else delete state[info.from];
        }
        state[sid] = info.cardId;
      }
      render();
      c.changed();
    }
    T27.DnD.zone(tray, host, onDrop, c.locked);
    function render() {
      tray.innerHTML = '';
      tpl.innerHTML = '';
      const used = new Set(Object.values(state));
      item.cards.forEach((card) => {
        if (item.reuse || !used.has(card.id)) tray.append(cardNode(card, 'tray', host, onDrop, c));
      });
      if (!tray.children.length) tray.append(el('span', { class: 'muted small', text: 'لا بطاقات متبقية' }));
      item.template.split(/\[\[(\w+)\]\]/).forEach((p, i) => {
        if (i % 2 === 0) {
          if (p) tpl.append(el('span', { html: U.rich(p) }));
          return;
        }
        const z = el('span', { class: 'slot', 'data-slot': p, 'aria-label': 'خانة ' + p });
        if (state[p] && byId[state[p]]) z.append(cardNode(byId[state[p]], p, host, onDrop, c));
        if (revealed) z.classList.add(revealed.correct ? 'is-ok' : 'is-bad');
        T27.DnD.zone(z, host, onDrop, c.locked);
        tpl.append(z);
      });
    }
    render();
    return {
      get: () => (Object.keys(state).length ? Object.assign({}, state) : null),
      set: (r) => {
        state = Object.assign({}, r || {});
        render();
      },
      answered: () => Object.keys(state).length > 0,
      reveal: (res) => {
        revealed = res;
        render();
      },
    };
  };

  RENDER.dragdrop_order = function (item, host, c) {
    const byId = Object.fromEntries(item.cards.map((x) => [x.id, x]));
    const n = item.cards.length;
    let state = Array.isArray(c.response) ? c.response.slice() : new Array(n).fill(null);
    const tray = el('div', { class: 'tray', 'data-tray': '1' });
    const row = el('div', { class: 'orderrow', style: { direction: 'ltr' } });
    const asc = (item.direction || 'asc') === 'asc';
    const lbl = item.order_labels || (asc ? ['الأصغر', 'الأكبر'] : ['الأكبر', 'الأصغر']);
    const ends = el('div', { class: 'order-dir', style: { direction: 'ltr' } }, el('span', { text: '(1) ' + lbl[0] }), el('span', { text: lbl[1] + ' (' + n + ')' }));
    host.append(el('div', { class: 'tray-label', text: 'البطاقات:' }), tray, el('div', { style: { height: '10px' } }), ends, row);
    let revealed = null;
    function onDrop(zone, info) {
      if (!zone) return render();
      const toTray = zone === 'tray' || (zone.dataset && zone.dataset.tray);
      const fromPos = info.from === 'tray' ? -1 : Number(info.from);
      if (toTray) {
        if (fromPos >= 0) state[fromPos] = null;
      } else {
        const pos = Number(zone.dataset.pos);
        const prev = state[pos];
        if (fromPos >= 0) state[fromPos] = prev || null;
        state[pos] = info.cardId;
      }
      render();
      c.changed();
    }
    T27.DnD.zone(tray, host, onDrop, c.locked);
    function render() {
      tray.innerHTML = '';
      row.innerHTML = '';
      const used = new Set(state.filter(Boolean));
      item.cards.forEach((card) => {
        if (!used.has(card.id)) tray.append(cardNode(card, 'tray', host, onDrop, c));
      });
      if (!tray.children.length) tray.append(el('span', { class: 'muted small', text: 'رُتّبت كل البطاقات' }));
      for (let k = 0; k < n; k++) {
        const z = el('div', { class: 'slot', 'data-pos': String(k), 'aria-label': 'الموقع ' + (k + 1) });
        if (state[k]) z.append(cardNode(byId[state[k]], String(k), host, onDrop, c));
        if (revealed) z.classList.add(state[k] === item.key[k] ? 'is-ok' : 'is-bad');
        T27.DnD.zone(z, host, onDrop, c.locked);
        row.append(el('div', { style: { textAlign: 'center' } }, el('div', { class: 'small muted', text: String(k + 1) }), z));
      }
    }
    render();
    return {
      get: () => (state.some(Boolean) ? state.slice() : null),
      set: (r) => {
        state = Array.isArray(r) ? r.slice() : new Array(n).fill(null);
        render();
      },
      answered: () => state.some(Boolean),
      reveal: (res) => {
        revealed = res;
        render();
      },
    };
  };

  RENDER.dragdrop_categorize = function (item, host, c) {
    const byId = Object.fromEntries(item.cards.map((x) => [x.id, x]));
    let state = Object.assign({}, c.response || {});
    const tray = el('div', { class: 'tray', 'data-tray': '1' });
    const cats = el('div', { class: 'cats' });
    host.append(el('div', { class: 'tray-label', text: 'البطاقات:' }), tray, cats);
    let revealed = false;
    function onDrop(zone, info) {
      if (!zone) return render();
      const toTray = zone === 'tray' || (zone.dataset && zone.dataset.tray);
      if (toTray) delete state[info.cardId];
      else state[info.cardId] = item.categories[Number(zone.dataset.cat)];
      render();
      c.changed();
    }
    T27.DnD.zone(tray, host, onDrop, c.locked);
    const boxes = item.categories.map((cat, k) => {
      const inner = el('div', { class: 'inner' });
      const box = el('div', { class: 'catbox', 'data-cat': String(k) }, el('h4', { html: U.rich(cat) }), inner);
      T27.DnD.zone(box, host, onDrop, c.locked);
      cats.append(box);
      return inner;
    });
    function render() {
      tray.innerHTML = '';
      boxes.forEach((b) => (b.innerHTML = ''));
      item.cards.forEach((card) => {
        const cat = state[card.id];
        const node = cardNode(card, cat ? 'cat' : 'tray', host, onDrop, c);
        if (cat) {
          if (revealed) node.classList.add(item.key[card.id] === cat ? 'is-ok' : 'is-bad');
          boxes[item.categories.indexOf(cat)].append(node);
        } else tray.append(node);
      });
      if (!tray.children.length) tray.append(el('span', { class: 'muted small', text: 'صُنّفت كل البطاقات' }));
    }
    render();
    return {
      get: () => (Object.keys(state).length ? Object.assign({}, state) : null),
      set: (r) => {
        state = Object.assign({}, r || {});
        render();
      },
      answered: () => Object.keys(state).length > 0,
      reveal: () => {
        revealed = true;
        render();
      },
    };
  };

  RENDER.grid_plot = function (item, host, c) {
    const state = { points: Array.isArray(c.response) ? c.response.map((p) => p.slice()) : [] };
    const gp = T27.GridPlot(item, host, state, c.changed, c.locked);
    return {
      get: () => (state.points.length ? state.points.map((p) => p.slice()) : null),
      set: (r) => {
        state.points = Array.isArray(r) ? r.map((p) => p.slice()) : [];
        gp.redraw();
      },
      answered: () => state.points.length > 0,
      reveal: (res) => {
        state.mark = res.correct ? '#2E7D32' : '#C62828';
        if (!res.correct) state.keyPoints = item.key;
        gp.redraw();
      },
    };
  };

  RENDER.select_explain = function (item, host, c) {
    const r0 = c.response || {};
    const mcCtl = RENDER.mc(Object.assign({}, item, { key: item.key }), host, Object.assign({}, c, { response: r0.choice || null }));
    const ta = el('textarea', { class: 'in', placeholder: 'اكتب تبريرك هنا…', 'aria-label': 'التبرير' });
    ta.value = r0.text || '';
    ta.addEventListener('input', c.changed);
    host.append(el('div', { class: 'explain-box' }, el('label', { class: 'f', text: 'التبرير:' }), ta));
    let human = typeof r0.human === 'number' ? r0.human : undefined;
    let scorer = r0.scorer;
    return {
      get: () => {
        const ch = mcCtl.get();
        const t = ta.value;
        if (!ch && !t.trim()) return null;
        const o = { choice: ch, text: t };
        if (human !== undefined) {
          o.human = human;
          o.scorer = scorer;
        }
        return o;
      },
      set: (r) => {
        mcCtl.set((r || {}).choice || null);
        ta.value = (r || {}).text || '';
      },
      setHuman: (pts, who) => {
        human = pts;
        scorer = who;
      },
      answered: () => !!(mcCtl.get() || ta.value.trim()),
      reveal: () => mcCtl.reveal(),
    };
  };

  RENDER.cr_explain = function (item, host, c) {
    const r0 = c.response || {};
    const ta = el('textarea', { class: 'in', placeholder: 'اكتب إجابتك هنا…', 'aria-label': 'الإجابة' });
    ta.value = r0.text || '';
    ta.addEventListener('input', c.changed);
    host.append(ta);
    let human = typeof r0.human === 'number' ? r0.human : undefined;
    let scorer = r0.scorer;
    return {
      get: () => {
        if (!ta.value.trim()) return null;
        const o = { text: ta.value };
        if (human !== undefined) {
          o.human = human;
          o.scorer = scorer;
        }
        return o;
      },
      set: (r) => (ta.value = (r || {}).text || ''),
      setHuman: (pts, who) => {
        human = pts;
        scorer = who;
      },
      answered: () => !!ta.value.trim(),
      reveal: () => {},
    };
  };

  /* ============================================================ دليل التصحيح */
  I.rubricNode = function (item) {
    const rb = item.rubric || {};
    const box = el('div', { class: 'rubric' }, el('h4', { text: 'دليل التصحيح' }));
    if (rb.codes) {
      const ul = el('ul');
      rb.codes.forEach((cd) => ul.append(el('li', { html: `<b dir="ltr">${cd.code}</b> (${cd.points} ${cd.points === 1 ? 'درجة' : 'درجات'}): ` + U.rich(cd.desc) })));
      box.append(ul);
    } else {
      const ul = el('ul');
      ul.append(el('li', { html: '<b>درجة كاملة:</b> ' + U.rich(rb.full) }));
      if (rb.partial) ul.append(el('li', { html: '<b>درجة جزئية:</b> ' + U.rich(rb.partial) }));
      ul.append(el('li', { html: '<b>صفر:</b> ' + U.rich(rb.zero) }));
      box.append(ul);
    }
    const ex = rb.examples || {};
    if (ex.correct && ex.correct.length) box.append(el('div', { html: '<b>أمثلة مقبولة:</b> ' + ex.correct.map((x) => '«' + U.rich(x) + '»').join('، ') }));
    if (ex.incorrect && ex.incorrect.length) box.append(el('div', { html: '<b>أمثلة غير مقبولة:</b> ' + ex.incorrect.map((x) => '«' + U.rich(x) + '»').join('، ') }));
    if (item.model_answer) box.append(el('div', { class: 'sec', html: '<b>إجابة نموذجية:</b> ' + U.rich(item.model_answer) }));
    if (item.anchors && item.anchors.length) {
      // نماذج إجابات طلاب للتدريب على التصحيح: مطوية، فيصحح المعلم أولاً ثم يقارن بالكود المقترح
      // في بند الدرجة الواحدة لا درجة جزئية: الإجابة «الجزئية» المولّدة إجابة ناقصة تنال صفراً
      const LV = { full: 'إجابة كاملة', partial: rb.codes || rb.partial ? 'إجابة جزئية' : 'إجابة ناقصة', incorrect: 'إجابة خاطئة' };
      const det = el('details', { class: 'anchors' }, el('summary', { html: '<b>نماذج إجابات طلاب للتدريب على التصحيح</b> <span class="muted small">(مولّدة آلياً ومراجَعة: صحّح كل نموذج أولاً ثم قارن بالكود)</span>' }));
      item.anchors.forEach((a, k) => {
        const key = el('details', { class: 'anchor-key' }, el('summary', { text: 'أظهر الكود المقترح' }),
          el('div', { class: 'small', html: U.esc(LV[a.level] || a.level || '') + ' · الكود: <b dir="ltr">' + U.esc(String(a.code)) + '</b>' }),
          el('div', { class: 'small', html: '<b>السبب:</b> ' + U.rich(a.reason || '') }));
        if (a.note) key.append(el('div', { class: 'small anchor-note', html: '<b>قرار المراجعة:</b> ' + U.rich(a.note) }));
        det.append(el('div', { class: 'anchor' }, el('div', { class: 'small muted', text: 'النموذج ' + (k + 1) }),
          el('div', { html: '«' + U.rich(a.text || '') + '»' }), key));
      });
      if (T27.isolateLtr) T27.isolateLtr(det);
      box.append(det);
    }
    return box;
  };

  /* ============================================================ التغذية الراجعة (التدريب) */
  /** onSelf(points) يُستدعى عند التقييم الذاتي للأسئلة المفتوحة */
  I.feedback = function (item, response, result, onSelf) {
    const human = item.format === 'select_explain' || item.format === 'cr_explain';
    const box = el('div', { class: 'feedback ' + (human ? 'info' : result.correct ? 'ok' : 'bad'), role: 'status' });
    if (human) {
      let msg = '📝 سؤال بتصحيح بشري: قارن إجابتك بدليل التصحيح ثم قيّمها بنفسك.';
      if (item.format === 'select_explain' && response && response.choice) msg += response.choice === item.key ? ' (اختيارك صحيح، والتبرير يحدد الدرجة)' : ' (اختيارك غير صحيح)';
      box.append(el('div', { class: 'ttl', text: msg }));
      box.append(I.rubricNode(item));
      const maxp = item.points || 1;
      const row = el('div', { class: 'row', style: { marginTop: '10px' } }, el('b', { text: 'تقييمي الذاتي:' }));
      for (let p = 0; p <= maxp; p++) {
        row.append(el('button', { type: 'button', class: 'btn sm ' + (p === maxp ? '' : 'alt'), text: p === maxp ? `درجة كاملة (${p})` : p === 0 ? 'صفر (0)' : `جزئية (${p})`, on: { click: (e) => { U.$$('button', row).forEach((b) => (b.disabled = true)); e.target.classList.add('gold'); onSelf && onSelf(p); } } }));
      }
      box.append(row);
    } else {
      box.append(el('div', { class: 'ttl', text: result.correct ? '✅ إجابة صحيحة!' : result.blank ? '⚪ لم تُجب عن السؤال.' : result.points > 0 ? `🟡 إجابة صحيحة جزئياً (${result.points} من ${result.max})` : '❌ إجابة غير صحيحة.' }));
      if (!result.correct) {
        if (item.format === 'mc' && response && item.rationale && item.rationale[response]) {
          box.append(el('div', { class: 'sec', html: '<b>لماذا البديل ' + response + ' غير صحيح؟</b> ' + U.rich(item.rationale[response]) }));
        }
        box.append(el('div', { class: 'sec', html: '<b>الإجابة الصحيحة:</b> ' + U.rich(I.keyText(item)) }));
      }
    }
    if (item.solution) box.append(el('div', { class: 'sec', html: '<b>الحل:</b><br>' + U.rich(item.solution) }));
    if (item.remediation && !result.correct) box.append(el('div', { class: 'sec', html: '<b>للمراجعة:</b><br>' + U.rich(item.remediation) }));
    return box;
  };

  /* ============================================================ نسخة الطباعة */
  I.printNode = function (item, n, withKey) {
    const box = el('div', { class: 'pitem' });
    box.append(el('div', { html: `<span class="qn">${n}.</span> ` + U.rich(item.stem) }));
    if (item.table) box.append(U.table(item.table));
    if (item.format === 'grid_plot') box.append(el('div', { class: 'figure', html: withKey ? item.key_svg || item.print_svg : item.print_svg }));
    else if (item.figure_svg) box.append(el('div', { class: 'figure', html: item.figure_svg }));
    const f = item.format;
    if (f === 'mc' || f === 'select_explain') {
      const list = el('div', { class: 'opts' + (f === 'mc' && (item.options || []).every((o) => U.plain(o).length <= 16) ? ' cols2' : '') });
      item.options.forEach((o, i) =>
        list.append(el('div', { class: 'opt' + (withKey && LET[i] === item.key ? ' is-ok' : '') }, el('span', { class: 'opt-l', text: LET[i] }), el('span', { class: 'opt-t', html: (item.options_svg || [])[i] || U.rich(o) })))
      );
      box.append(list);
      if (f === 'select_explain') box.append(el('div', { html: '<b>التبرير:</b>' }), el('div', { class: 'ansline' }), el('div', { class: 'ansline' }));
    } else if (f === 'numeric') {
      box.append(el('div', { class: 'numrow' }, el('b', { text: 'الإجابة: ' }), withKey ? el('b', { html: U.rich(I.keyText(item)) }) : el('span', { class: 'pbox' }), unitEl(!withKey && item.answer.unit)));
    } else if (f === 'multi_numeric') {
      const r = el('div', { class: 'numrow' });
      item.fields.forEach((fl) => r.append(el('span', { html: U.rich(fl.label) + ' = ' }), withKey ? el('b', { html: U.rich('$' + fl.value + '$') }) : el('span', { class: 'pbox' })));
      box.append(r);
    } else if (f.startsWith('dragdrop')) {
      box.append(el('div', { class: 'chips' }, ...item.cards.map((cd) => el('span', { class: 'chip', html: U.rich(cd.text) }))));
      if (f === 'dragdrop_slots') box.append(el('div', { class: 'tpl', html: U.rich(item.template.replace(/\[\[\w+\]\]/g, ' $\\boxed{\\phantom{00}}$ ')) }));
      if (f === 'dragdrop_order') {
        // خانات فارغة من اليسار إلى اليمين بين تسميتي الطرفين (الأولى يساراً)، بلا رموز LaTeX خام
        const asc = (item.direction || 'asc') === 'asc';
        const lbl = item.order_labels || (asc ? ['الأصغر', 'الأكبر'] : ['الأكبر', 'الأصغر']);
        const row = el('div', { class: 'order-print', dir: 'ltr' }, el('span', { class: 'olab', text: lbl[0] }));
        item.cards.forEach(() => row.append(el('span', { class: 'pbox sm' })));
        row.append(el('span', { class: 'olab', text: lbl[1] }));
        box.append(row);
      }
      if (f === 'dragdrop_categorize') box.append(el('div', { class: 'cats' }, ...item.categories.map((cat) => el('div', { class: 'catbox' }, el('h4', { html: U.rich(cat) })))));
      if (withKey) box.append(el('div', { html: '<b>الإجابة:</b> ' + U.rich(I.keyText(item)) }));
    } else if (f === 'cr_explain') {
      for (let k = 0; k < 4; k++) box.append(el('div', { class: 'ansline' }));
    }
    if (withKey) {
      if (f === 'select_explain' || f === 'cr_explain') box.append(I.rubricNode(item));
      if (item.solution) box.append(el('div', { class: 'small', html: '<b>الحل:</b> ' + U.rich(item.solution) }));
    }
    return box;
  };
})();
