/* ==========================================================================
   40_screens.js — الشاشات: الدخول، لوحة الطالب، التدريب، المحاكاة، النتائج، السجل، وضع المعلم
   ========================================================================== */
'use strict';
(function () {
  const U = T27.U;
  const D = T27.D;
  const I = T27.I;
  const el = U.el;
  const S = (T27.S = { profile: null, teacher: false, session: null, timer: null });
  const APP = document.getElementById('app');
  const BR = (window.BUILD_INFO && window.BUILD_INFO.brand) || {};

  /* ============================================================ الملفات الشخصية والتخزين */
  const P = (T27.P = {});
  P.list = () => U.store.get('profiles', []);
  P.saveList = (l) => U.store.set('profiles', l);
  P.current = () => {
    const id = U.store.get('current', null);
    return P.list().find((p) => p.id === id) || null;
  };
  P.use = (p) => {
    U.store.set('current', p.id);
    S.profile = p;
  };
  P.sessions = () => U.store.get('sessions.' + (S.profile ? S.profile.id : 'anon'), []);
  P.saveSessions = (l) => {
    if (!U.store.set('sessions.' + (S.profile ? S.profile.id : 'anon'), l)) U.toast('تعذّر الحفظ: مساحة التخزين ممتلئة. صدّر نتائجك.');
  };
  P.review = () => U.store.get('review.' + (S.profile ? S.profile.id : 'anon'), {});
  P.saveReview = (r) => U.store.set('review.' + (S.profile ? S.profile.id : 'anon'), r);

  /* ============================================================ الشريط العلوي */
  function topbar(right) {
    const brand = el('div', { class: 'brand' });
    if (BR.logo) brand.append(el('img', { src: BR.logo, alt: 'الشعار' }));
    else brand.append(el('span', { class: 'logo', text: 'T27' }));
    brand.append(el('span', { text: 'منصة TIMSS 2027 · رياضيات الصف الثامن' }));
    const bar = el('header', { class: 'topbar' }, brand, el('span', { class: 'spacer' }));
    if (S.profile) bar.append(el('span', { class: 'who', text: '👤 ' + S.profile.name + (S.profile.cls ? ' · ' + S.profile.cls : '') }));
    (right || []).forEach((n) => bar.append(n));
    bar.append(el('button', { class: 'tbtn', type: 'button', title: 'حجم الخط', 'aria-label': 'تكبير الخط', text: 'A+', on: { click: cycleFont } }));
    return bar;
  }
  function cycleFont() {
    const order = ['', 'fs-lg', 'fs-xl'];
    const cur = U.store.get('font', '');
    const next = order[(order.indexOf(cur) + 1) % order.length];
    document.body.classList.remove('fs-lg', 'fs-xl');
    if (next) document.body.classList.add(next);
    U.store.set('font', next);
  }
  const calcBtn = () => el('button', { class: 'tbtn', type: 'button', text: '🧮 الحاسبة', on: { click: () => T27.Calc.toggle() } });

  function screen(nodes, right, keepCalc) {
    stopTimer();
    if (!keepCalc) T27.Calc.hide();
    APP.innerHTML = '';
    APP.append(topbar(right));
    const w = el('main', { class: 'wrap' });
    nodes.forEach((n) => n && w.append(n));
    APP.append(w);
    window.scrollTo(0, 0);
    return w;
  }

  /* ============================================================ الدخول */
  T27.welcome = function () {
    const profiles = P.list();
    const name = el('input', { class: 'in', placeholder: 'مثال: مريم أحمد', maxlength: '60', 'aria-label': 'الاسم' });
    const cls = el('input', { class: 'in', placeholder: 'مثال: 8/3', maxlength: '20', 'aria-label': 'الشعبة' });
    const num = el('input', { class: 'in', placeholder: 'اختياري', maxlength: '20', dir: 'ltr', 'aria-label': 'رقم الطالب' });
    const start = () => {
      if (!name.value.trim()) {
        U.toast('اكتب اسمك أولاً');
        name.focus();
        return;
      }
      const p = { id: U.uid(), name: name.value.trim(), cls: cls.value.trim(), num: num.value.trim(), created: Date.now() };
      P.saveList(P.list().concat([p]));
      P.use(p);
      T27.hub();
    };
    const card = el('div', { class: 'card' },
      el('div', { class: 'kicker', text: BR.school || 'دولة قطر' }),
      el('h1', { text: 'مرحباً بك في منصة التدريب على TIMSS 2027' }),
      el('p', { class: 'muted', text: 'تدرّب على أسئلة الرياضيات للصف الثامن بواجهة تحاكي الاختبار الرقمي eTIMSS: اختيار من متعدد، وإدخال رقمي، وسحب وإفلات، ورسم على المستوى الإحداثي، وأسئلة التبرير.' }),
      el('label', { class: 'f', text: 'الاسم' }), name,
      el('div', { class: 'row' }, el('div', { style: { flex: '1' } }, el('label', { class: 'f', text: 'الشعبة' }), cls), el('div', { style: { flex: '1' } }, el('label', { class: 'f', text: 'رقم الطالب' }), num)),
      el('div', { class: 'row', style: { marginTop: '16px' } }, el('button', { class: 'btn', type: 'button', text: 'ابدأ التدريب', on: { click: start } }), el('span', { class: 'spacer' }), el('button', { class: 'btn ghost', type: 'button', text: '👩‍🏫 وضع المعلم', on: { click: T27.teacherLogin } }))
    );
    name.addEventListener('keydown', (e) => e.key === 'Enter' && start());
    const nodes = [card];
    if (profiles.length) {
      const list = el('div', { class: 'chips' });
      profiles.slice(-30).reverse().forEach((p) => list.append(el('button', { class: 'chip', type: 'button', text: p.name + (p.cls ? ' (' + p.cls + ')' : ''), on: { click: () => { P.use(p); T27.hub(); } } })));
      nodes.push(el('div', { class: 'card' }, el('h3', { text: 'متابعة بحساب سابق على هذا الجهاز' }), list));
    }
    nodes.push(el('p', { class: 'disclaimer', text: 'منصة تدريبية غير رسمية أُعدّت للتدريب على أسلوب اختبار TIMSS، ولا تتبع الرابطة الدولية لتقييم التحصيل التربوي (IEA). جميع الأسئلة أصلية. تُحفظ البيانات على هذا الجهاز فقط.' }));
    screen(nodes);
  };

  /* ============================================================ لوحة الطالب */
  T27.hub = function () {
    if (!S.profile) return T27.welcome();
    const sess = P.sessions();
    const hasDiag = sess.some((s) => s.type === 'diagnostic');
    const active = U.store.get('active.' + S.profile.id, null);
    const tile = (ic, title, desc, fn, cls, go) =>
      el('button', { class: 'tile ' + (cls || ''), type: 'button', on: { click: fn } }, el('span', { class: 'ic', text: ic }), el('b', { text: title }), el('span', { class: 'muted small', text: desc }), el('span', { class: 'go', text: (go || 'ابدأ') + ' ←' }));
    const tiles = el('div', { class: 'grid-cards' });
    if (active) tiles.append(tile('⏯️', 'استكمال: ' + active.title, 'لديك جلسة غير مكتملة محفوظة.', () => T27.run(active), 'gold', 'استكمل'));
    tiles.append(
      tile('🧭', 'الاختبار التشخيصي', hasDiag ? 'أعد التشخيص لقياس تقدمك.' : 'ابدأ به: 32 سؤالاً في 45 دقيقة تحدد نقاط قوتك وضعفك.', () => T27.startDiagnostic(), 'maroon'),
      tile('🎯', 'تدريب حسب الموضوع', 'اختر المجال والموضوع والمستوى، وتلقَّ تغذية راجعة فورية.', () => T27.practiceSetup()),
      tile('🧠', 'التدريب الذكي', 'أسئلة مختارة من موضوعاتك الأضعف، مع مراجعة متباعدة لأخطائك السابقة.', () => T27.startSmart()),
      tile('⏱️', 'محاكاة TIMSS', 'نموذج كامل: كتلتان (32 سؤالاً) في 45 دقيقة مع الحاسبة، دون تغذية راجعة حتى التسليم.', () => T27.startSim(), 'gold'),
      tile('🧩', 'مهام حل المشكلات PSI', 'مواقف متعددة الخطوات بسياقات قطرية.', () => T27.psiList()),
      tile('🔒', 'الاختبارات التجريبية', 'تحتاج رمز دخول يعطيك إياه المعلم يوم الاختبار.', () => T27.mocks()),
      tile('📈', 'سجلي وتقدمي', sess.length ? `${sess.length} جلسة محفوظة.` : 'لا جلسات بعد.', () => T27.history(), '', 'عرض'),
      tile('🛈', 'جولة تعريفية', 'تعرّف على أنواع الأسئلة وطريقة الإجابة والحاسبة.', () => T27.startTutorial(), '', 'ابدأ الجولة')
    );
    const studentDocs = ((window.DOCS || []).filter((d) => d.audience === 'student'));
    const docsRow = studentDocs.length ? el('div', { class: 'card' }, el('h3', { text: 'أدلة للطالب' }), el('div', { class: 'chips' }, ...studentDocs.map((d) => el('button', { class: 'chip', type: 'button', text: d.title, on: { click: () => T27.doc(d.id, T27.hub) } })))) : null;
    screen([
      el('div', { class: 'row' }, el('h1', { text: 'مرحباً ' + S.profile.name + ' 👋' }), el('span', { class: 'spacer' }), el('button', { class: 'btn ghost sm', type: 'button', text: 'تبديل الطالب', on: { click: () => { U.store.del('current'); S.profile = null; T27.welcome(); } } })),
      tiles,
      docsRow,
    ]);
  };

  /* ============================================================ إعداد التدريب */
  T27.practiceSetup = function () {
    const f = { domain: '', topic: '', cognitive: '', difficulty: '', n: 10 };
    const sel = (opts, key, label) => {
      const s = el('select', { class: 'in', 'aria-label': label });
      opts.forEach(([v, t]) => s.append(el('option', { value: v, text: t })));
      s.addEventListener('change', () => {
        f[key] = s.value;
        if (key === 'domain') refreshTopics();
        count();
      });
      return s;
    };
    const dSel = sel([['', 'كل المجالات']].concat(D.DOMAIN_ORDER.map((d) => [d, D.domainName(d)])), 'domain', 'المجال');
    const tSel = el('select', { class: 'in', 'aria-label': 'الموضوع' });
    tSel.addEventListener('change', () => {
      f.topic = tSel.value;
      count();
    });
    function refreshTopics() {
      tSel.innerHTML = '';
      tSel.append(el('option', { value: '', text: 'كل الموضوعات' }));
      D.topicsOf(f.domain).forEach((t) => tSel.append(el('option', { value: t, text: t + ' — ' + D.topicName(t) })));
      f.topic = '';
    }
    refreshTopics();
    const cSel = sel([['', 'كل المستويات المعرفية']].concat(D.COG_ORDER.map((c) => [c, D.cogName(c)])), 'cognitive', 'المستوى المعرفي');
    const fSel = sel([['', 'كل مستويات الصعوبة']].concat(D.DIFF_ORDER.map((c) => [c, D.diffName(c)])), 'difficulty', 'الصعوبة');
    const nSel = sel([['5', '5 أسئلة'], ['10', '10 أسئلة'], ['15', '15 سؤالاً'], ['20', '20 سؤالاً']], 'n', 'العدد');
    nSel.value = '10';
    const info = el('p', { class: 'muted' });
    function count() {
      const pool = D.filter(f, D.practicePool());
      info.textContent = `الأسئلة المتاحة بهذه المواصفات: ${pool.length}`;
    }
    count();
    const go = () => {
      const pool = D.filter(f, D.practicePool());
      if (!pool.length) return U.toast('لا توجد أسئلة بهذه المواصفات بعد.');
      const seen = D.seenSet();
      const fresh = U.shuffle(pool.filter((i) => !seen.has(i.id)));
      const old = U.shuffle(pool.filter((i) => seen.has(i.id)));
      const ids = fresh.concat(old).slice(0, Number(f.n) || 10).map((i) => i.id);
      T27.run(newSession('practice', 'تدريب: ' + (f.topic ? D.topicShort(f.topic) : f.domain ? D.domainName(f.domain) : 'كل المجالات'), [{ id: 'P', items: ids }], null));
    };
    screen([
      el('div', { class: 'card' },
        el('h2', { text: '🎯 تدريب حسب الموضوع' }),
        el('div', { class: 'grid-cards' },
          el('div', null, el('label', { class: 'f', text: 'المجال' }), dSel),
          el('div', null, el('label', { class: 'f', text: 'الموضوع' }), tSel),
          el('div', null, el('label', { class: 'f', text: 'المستوى المعرفي' }), cSel),
          el('div', null, el('label', { class: 'f', text: 'الصعوبة' }), fSel),
          el('div', null, el('label', { class: 'f', text: 'عدد الأسئلة' }), nSel)),
        info,
        el('div', { class: 'row' }, el('button', { class: 'btn', type: 'button', text: 'ابدأ التدريب', on: { click: go } }), el('button', { class: 'btn ghost', type: 'button', text: 'رجوع', on: { click: T27.hub } }))),
    ]);
  };

  /* ============================================================ الجلسات */
  function newSession(type, title, blocks, limitSec, extra) {
    return Object.assign({ id: U.uid(), type, title, blocks, started: Date.now(), limit: limitSec, remaining: limitSec, cur: 0, responses: {}, flags: {}, times: {}, checked: {}, results: {} }, extra || {});
  }
  const flatIds = (s) => s.blocks.reduce((a, b) => a.concat(b.items), []);
  const isTest = (s) => ['diagnostic', 'sim', 'mock'].includes(s.type);
  function saveActive(s) {
    if (!S.profile) return;
    if (s.type === 'tutorial') return;
    U.store.set('active.' + S.profile.id, s);
  }

  T27.startDiagnostic = () => T27.run(newSession('diagnostic', 'الاختبار التشخيصي', D.diagnosticBlocks(), 45 * 60));
  T27.startSim = () => T27.run(newSession('sim', 'محاكاة TIMSS', D.assembleSim(), 45 * 60));
  T27.startTutorial = function () {
    const want = ['mc', 'numeric', 'multi_numeric', 'dragdrop_order', 'dragdrop_slots', 'dragdrop_categorize', 'grid_plot', 'select_explain'];
    const ids = [];
    want.forEach((f) => {
      const pool = D.practicePool();
      const it = pool.find((i) => i.format === f && ['foundation', 'easy', 'medium'].includes(i.difficulty)) || pool.find((i) => i.format === f);
      if (it) ids.push(it.id);
    });
    T27.run(newSession('tutorial', 'جولة تعريفية', [{ id: 'T', items: ids }], null));
  };

  /** التدريب الذكي: مراجعة متباعدة + موضوعات ضعيفة */
  T27.mastery = function (sessions) {
    const m = {};
    Object.keys(D.B.topics).forEach((t) => (m[t] = { p: 0, max: 0, n: 0 }));
    const recent = {};
    (sessions || []).slice().sort((a, b) => b.finished - a.finished).forEach((s) =>
      (s.items || []).forEach((r) => {
        const it = metaOf(r);
        if (!it || r.pend || !m[it.topic]) return;
        recent[it.topic] = recent[it.topic] || [];
        if (recent[it.topic].length < 14) recent[it.topic].push(r);
      })
    );
    Object.entries(recent).forEach(([t, rs]) =>
      rs.forEach((r) => {
        m[t].p += r.p;
        m[t].max += r.m;
        m[t].n += 1;
      })
    );
    return m;
  };
  T27.startSmart = function () {
    const sess = P.sessions();
    const rev = P.review();
    const now = Date.now();
    const due = Object.entries(rev).filter(([id, v]) => v.due <= now && D.byId.get(id) && !D.byId.get(id).psi).map(([id]) => id);
    const reviewIds = U.shuffle(due).slice(0, 3);
    const m = T27.mastery(sess);
    const weak = Object.keys(m).map((t) => {
      const v = m[t];
      const rate = v.max ? v.p / v.max : null;
      const dom = D.B.topics[t].domain;
      const boost = dom === 'geometry_measurement' || dom === 'data_probability' ? 0.08 : 0;
      return { t, score: rate === null ? 0.35 - boost : rate - boost, rate };
    }).sort((a, b) => a.score - b.score);
    const seen = D.seenSet();
    const ids = reviewIds.slice();
    for (const w of weak) {
      if (ids.length >= 10) break;
      const level = w.rate === null || w.rate < 0.5 ? ['foundation', 'easy'] : w.rate < 0.75 ? ['easy', 'medium'] : ['medium', 'hard'];
      const pool = D.practicePool().filter((i) => i.topic === w.t && !ids.includes(i.id));
      const pref = pool.filter((i) => level.includes(i.difficulty) && !seen.has(i.id));
      const cand = pref.length ? pref : pool.filter((i) => !seen.has(i.id)).length ? pool.filter((i) => !seen.has(i.id)) : pool;
      U.sample(cand, 2).forEach((i) => ids.length < 10 && ids.push(i.id));
    }
    if (!ids.length) return U.toast('لا توجد أسئلة متاحة بعد.');
    T27.run(newSession('smart', 'التدريب الذكي', [{ id: 'S', items: ids }], null));
  };
  function updateReview(item, correct) {
    const rev = P.review();
    const day = 86400000;
    const cur = rev[item.id];
    if (!correct) rev[item.id] = { box: 1, due: Date.now() + day };
    else if (cur) {
      const box = cur.box + 1;
      if (box > 3) delete rev[item.id];
      else rev[item.id] = { box, due: Date.now() + (box === 2 ? 3 : 7) * day };
    }
    P.saveReview(rev);
  }

  /* ============================================================ مشغّل الجلسة */
  let current = null; // {s, ids, ctl, t0}
  function stopTimer() {
    if (S.timer) clearInterval(S.timer);
    S.timer = null;
  }
  T27.run = function (s) {
    // استكمال اختبار تجريبي بعد إعادة تحميل الصفحة: أعد تسجيل بنوده المفكوكة
    if (s.formData && s.formData.blocks) s.formData.blocks.forEach((b) => b.items.forEach((i) => D.byId.set(i.id, i)));
    const ids = flatIds(s).filter((id) => D.byId.get(id));
    if (!ids.length) {
      U.toast('تعذّر تحميل أسئلة هذه الجلسة.');
      return T27.hub();
    }
    current = { s, ids, ctl: null, t0: Date.now() };
    if (s.limit) s.remaining = s.remaining === undefined || s.remaining === null ? s.limit : s.remaining;
    showItem(Math.min(s.cur || 0, ids.length - 1));
  };

  function recordTime() {
    if (!current || !current.ctl) return;
    const id = current.ids[current.s.cur];
    current.s.times[id] = (current.s.times[id] || 0) + (Date.now() - current.t0);
    current.t0 = Date.now();
  }
  function captureResponse() {
    if (!current || !current.ctl) return;
    const id = current.ids[current.s.cur];
    const r = current.ctl.get();
    if (r === null || r === undefined) delete current.s.responses[id];
    else current.s.responses[id] = r;
  }

  function showItem(k) {
    const { s, ids } = current;
    if (current.ctl) {
      captureResponse();
      recordTime();
    }
    s.cur = k;
    saveActive(s);
    const id = ids[k];
    const item = D.byId.get(id);
    const test = isTest(s);
    const right = [];
    if (s.limit) {
      const tm = el('span', { class: 'timer', 'aria-live': 'off', text: U.fmtTime(s.remaining) });
      right.push(tm);
      stopTimer();
    }
    right.push(calcBtn(), el('button', { class: 'tbtn', type: 'button', text: test ? 'حفظ وخروج' : 'إنهاء', on: { click: exitSession } }));
    const host = el('div');
    const nodes = [];
    if (item.psi) {
      const task = D.psi.find((t) => t.id === item.psi);
      if (task) {
        const intro = el('details', { class: 'psi-intro', open: k === 0 || ids[k - 1] && D.byId.get(ids[k - 1]).psi !== item.psi ? true : null }, el('summary', { html: '<b>🧩 ' + U.esc(task.title) + '</b> — السياق' }), el('div', { html: U.rich(task.intro || '') }));
        if (task.table) intro.append(U.table(task.table));
        if (task.figure_svg) intro.append(el('div', { class: 'figure', html: task.figure_svg }));
        nodes.push(intro);
      }
    }
    if (!test && s.type !== 'psi') nodes.push(el('div', { class: 'progress', style: { marginBottom: '12px' } }, el('i', { style: { width: U.pct(k, ids.length) + '%' } })));
    nodes.push(host);
    const fbHost = el('div');
    nodes.push(fbHost);
    screen(nodes, right, true);
    // (screen() يوقف المؤقت) — أعد تشغيله بعد البناء
    if (s.limit) startTimer();
    const ctl = I.render(item, host, {
      mode: test ? 'test' : 'practice',
      response: s.responses[id],
      onChange: () => {
        captureResponse();
        saveActive(s);
        updateStrip();
      },
      number: k + 1,
      total: ids.length,
      meta: !test,
    });
    current.ctl = ctl;
    current.t0 = Date.now();
    if (!test && s.checked[id]) {
      ctl.lock(true);
      const res = s.results[id] || I.score(item, s.responses[id]);
      ctl.reveal(res);
      fbHost.append(I.feedback(item, s.responses[id], res, null));
    }
    APP.append(navbar(item, test, fbHost));
    updateStrip();
  }

  function navbar(item, test, fbHost) {
    const { s, ids } = current;
    const k = s.cur;
    const bar = el('nav', { class: 'navbar', 'aria-label': 'التنقل بين الأسئلة' });
    const prev = el('button', { class: 'btn alt', type: 'button', text: '→ السابق', disabled: k === 0 ? true : null, on: { click: () => showItem(k - 1) } });
    const strip = el('div', { class: 'qstrip' });
    let n = 0;
    s.blocks.forEach((b, bi) => {
      if (bi > 0) strip.append(el('span', { class: 'sep' }));
      b.items.forEach((id) => {
        const idx = ids.indexOf(id);
        if (idx < 0) return;
        n++;
        strip.append(el('button', { type: 'button', 'data-i': String(idx), text: String(n), 'aria-label': 'السؤال ' + n, on: { click: () => showItem(idx) } }));
      });
    });
    bar.append(prev, strip);
    if (test) {
      const flag = el('button', { class: 'btn ghost', type: 'button', text: s.flags[ids[k]] ? '🚩 إلغاء الوسم' : '🏳️ وسم للمراجعة', on: { click: () => { s.flags[ids[k]] = !s.flags[ids[k]]; saveActive(s); flag.textContent = s.flags[ids[k]] ? '🚩 إلغاء الوسم' : '🏳️ وسم للمراجعة'; updateStrip(); } } });
      bar.append(flag);
      if (k < ids.length - 1) bar.append(el('button', { class: 'btn', type: 'button', text: 'التالي ←', on: { click: () => showItem(k + 1) } }));
      else bar.append(el('button', { class: 'btn maroon', type: 'button', text: 'مراجعة وتسليم', on: { click: reviewScreen } }));
    } else {
      const checked = !!s.checked[ids[k]];
      if (!checked) {
        bar.append(el('button', { class: 'btn gold', type: 'button', text: '✓ تحقق', on: { click: () => checkPractice(item, fbHost, bar) } }));
      }
      if (k < ids.length - 1) bar.append(el('button', { class: 'btn' + (checked ? '' : ' alt'), type: 'button', text: checked ? 'التالي ←' : 'تخطَّ ←', on: { click: () => showItem(k + 1) } }));
      else bar.append(el('button', { class: 'btn maroon', type: 'button', text: 'إنهاء وعرض النتيجة', on: { click: () => finish() } }));
    }
    return bar;
  }
  function updateStrip() {
    if (!current) return;
    const { s, ids } = current;
    U.$$('.qstrip button').forEach((b) => {
      const idx = Number(b.dataset.i);
      const id = ids[idx];
      const item = D.byId.get(id);
      b.classList.toggle('cur', idx === s.cur);
      b.classList.toggle('ans', I.answered(item, s.responses[id]));
      b.classList.toggle('flag', !!s.flags[id]);
    });
    const cur = U.$('.qstrip button.cur');
    if (cur && cur.scrollIntoView) cur.scrollIntoView({ block: 'nearest', inline: 'center' });
  }
  function checkPractice(item, fbHost, bar) {
    const { s, ids } = current;
    captureResponse();
    const id = ids[s.cur];
    const r = s.responses[id];
    if (!I.answered(item, r)) {
      U.toast('أجب عن السؤال أولاً، أو اضغط «تخطَّ».');
      return;
    }
    const res = I.score(item, r);
    s.checked[id] = true;
    s.results[id] = res;
    current.ctl.lock(true);
    current.ctl.reveal(res);
    fbHost.innerHTML = '';
    const human = item.format === 'select_explain' || item.format === 'cr_explain';
    fbHost.append(
      I.feedback(item, r, res, (pts) => {
        const rr = Object.assign({}, s.responses[id], { human: pts, scorer: 'self' });
        s.responses[id] = rr;
        s.results[id] = I.score(item, rr);
        saveActive(s);
      })
    );
    if (!human) updateReview(item, res.correct);
    saveActive(s);
    // حدّث شريط التنقل
    const nb = U.$('.navbar');
    if (nb) nb.replaceWith(navbar(item, false, fbHost));
    updateStrip();
    fbHost.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  function startTimer() {
    stopTimer();
    const s = current.s;
    let last = Date.now();
    S.timer = setInterval(() => {
      const now = Date.now();
      s.remaining = Math.max(0, s.remaining - (now - last) / 1000);
      last = now;
      const tm = U.$('.timer');
      if (tm) {
        tm.textContent = U.fmtTime(s.remaining);
        tm.classList.toggle('low', s.remaining <= 300);
      }
      if (Math.floor(s.remaining) % 5 === 0) saveActive(s);
      if (s.remaining <= 0) {
        stopTimer();
        U.toast('انتهى الوقت. جارٍ التسليم…');
        finish(true);
      }
    }, 1000);
  }
  async function exitSession() {
    const { s } = current;
    captureResponse();
    recordTime();
    if (isTest(s)) {
      const ok = await U.confirm('حفظ وخروج', 'ستُحفظ إجاباتك ويتوقف المؤقت، ويمكنك الاستكمال لاحقاً من لوحة الطالب.', 'حفظ وخروج');
      if (!ok) return;
      saveActive(s);
      stopTimer();
      return T27.hub();
    }
    const ok = await U.confirm('إنهاء التدريب', 'هل تريد إنهاء الجلسة وعرض النتيجة؟', 'إنهاء');
    if (ok) finish();
  }
  function reviewScreen() {
    const { s, ids } = current;
    captureResponse();
    recordTime();
    saveActive(s);
    const un = ids.filter((id) => !I.answered(D.byId.get(id), s.responses[id]));
    const fl = ids.filter((id) => s.flags[id]);
    const list = (arr) => el('div', { class: 'chips' }, ...arr.map((id) => el('button', { class: 'chip', type: 'button', text: String(ids.indexOf(id) + 1), on: { click: () => showItem(ids.indexOf(id)) } })));
    const right = [];
    if (s.limit) right.push(el('span', { class: 'timer', text: U.fmtTime(s.remaining) }));
    screen([
      el('div', { class: 'card' },
        el('h2', { text: 'مراجعة قبل التسليم' }),
        el('p', { text: `أجبت عن ${ids.length - un.length} من ${ids.length} سؤالاً.` }),
        un.length ? el('div', null, el('b', { text: 'أسئلة بلا إجابة (انقر للعودة إليها):' }), list(un)) : el('p', { class: 'badge ok', text: 'أجبت عن جميع الأسئلة ✓' }),
        fl.length ? el('div', { style: { marginTop: '10px' } }, el('b', { text: 'أسئلة موسومة للمراجعة:' }), list(fl)) : null,
        el('p', { class: 'muted small', text: 'نصيحة TIMSS: لا تترك أي سؤال دون إجابة، فالسؤال المتروك يُحتسب خطأ.' }),
        el('div', { class: 'row' },
          el('button', { class: 'btn alt', type: 'button', text: 'العودة إلى الأسئلة', on: { click: () => showItem(s.cur) } }),
          el('button', { class: 'btn maroon', type: 'button', text: 'تسليم نهائي', on: { click: async () => { if (await U.confirm('تسليم نهائي', 'لن تتمكن من تعديل إجاباتك بعد التسليم.', 'سلّم الآن')) finish(); } } }))),
    ], right, true);
    if (s.limit) startTimer();
  }

  /* ============================================================ إنهاء الجلسة والنتائج */
  function finish() {
    stopTimer();
    const { s, ids } = current;
    if (current.ctl) {
      captureResponse();
      recordTime();
    }
    s.finished = Date.now();
    const recs = ids.map((id) => {
      const item = D.byId.get(id);
      const r = s.responses[id];
      const res = s.results[id] && !isTest(s) ? s.results[id] : I.score(item, r);
      if (isTest(s) && s.type !== 'mock' && item.format !== 'select_explain' && item.format !== 'cr_explain') updateReview(item, res.correct);
      // تُحفظ بيانات التصنيف مع كل إجابة حتى تعمل الملخصات دون البنك (مثل بنود الاختبارات المحمية)
      return { id, r: r === undefined ? null : r, p: res.points, m: res.max, c: res.correct, pend: !!res.pending, t: Math.round((s.times[id] || 0) / 1000), f: s.flags[id] ? 1 : 0,
        tp: item.topic, dm: item.domain, cg: item.cognitive, bm: item.benchmark, fm: item.format };
    });
    const record = { id: s.id, type: s.type, title: s.title, form: s.form || null, started: s.started, finished: s.finished, limit: s.limit || null, used: s.limit ? Math.round(s.limit - s.remaining) : Math.round((s.finished - s.started) / 1000), items: recs, v: 1 };
    if (s.type !== 'tutorial') {
      const all = P.sessions();
      all.push(record);
      P.saveSessions(all);
    }
    U.store.del('active.' + (S.profile ? S.profile.id : 'anon'));
    current = null;
    T27.results(record);
  }

  /** ملخص حسب المجال والمستوى المعرفي والموضوع ونطاق الجاهزية */
  const metaOf = (r) => D.byId.get(r.id) || (r.tp ? { topic: r.tp, domain: r.dm, cognitive: r.cg, benchmark: r.bm, format: r.fm } : null);
  T27.metaOf = metaOf;
  T27.summarize = function (recs) {
    const agg = (keyFn) => {
      const m = {};
      recs.forEach((r) => {
        const it = metaOf(r);
        if (!it || r.pend) return;
        const k = keyFn(it);
        m[k] = m[k] || { p: 0, m: 0, n: 0 };
        m[k].p += r.p;
        m[k].m += r.m;
        m[k].n += 1;
      });
      return m;
    };
    const total = recs.filter((r) => !r.pend).reduce((a, r) => ({ p: a.p + r.p, m: a.m + r.m }), { p: 0, m: 0 });
    const byB = agg((it) => it.benchmark);
    let band = null;
    let usedData = false;
    for (const b of D.BM_ORDER) {
      const v = byB[b];
      if (!v || v.m < 3) continue;
      usedData = true;
      if (v.p / v.m >= 0.6) band = b;
      else break;
    }
    if (!usedData && total.m) {
      const r = total.p / total.m;
      band = r >= 0.8 ? 'advanced' : r >= 0.65 ? 'high' : r >= 0.5 ? 'intermediate' : r >= 0.35 ? 'low' : null;
    }
    return { total, byDomain: agg((it) => it.domain), byCog: agg((it) => it.cognitive), byTopic: agg((it) => it.topic), byB, band, pending: recs.filter((r) => r.pend).length };
  };

  function barRow(label, v, cls) {
    const p = v && v.m ? Math.round((100 * v.p) / v.m) : 0;
    return el('tr', null, el('td', { text: label }), el('td', { text: v ? `${v.p} / ${v.m}` : '—', style: { direction: 'ltr', textAlign: 'center' } }), el('td', null, el('div', { class: 'bar-h ' + (cls || '') }, el('i', { style: { width: p + '%' } }))), el('td', { text: v && v.m ? p + '%' : '—', style: { direction: 'ltr' } }));
  }

  T27.results = function (rec) {
    const sm = T27.summarize(rec.items);
    const pct = sm.total.m ? Math.round((100 * sm.total.p) / sm.total.m) : 0;
    const test = ['diagnostic', 'sim', 'mock'].includes(rec.type);
    const bandTxt = sm.band ? D.bmName(sm.band) : 'دون المستوى المنخفض';
    const kpis = el('div', { class: 'kpis' },
      el('div', { class: 'kpi' }, el('div', { class: 'v', text: `${pct}%` }), el('div', { class: 'l', text: `الدرجة: ${sm.total.p} من ${sm.total.m}` })),
      el('div', { class: 'kpi' }, el('div', { class: 'v', text: String(rec.items.filter((r) => r.r !== null).length) + ' / ' + rec.items.length }), el('div', { class: 'l', text: 'أسئلة مُجاب عنها' })),
      el('div', { class: 'kpi' }, el('div', { class: 'v', text: U.fmtTime(rec.used || 0) }), el('div', { class: 'l', text: 'الوقت المستغرق' })),
      sm.pending ? el('div', { class: 'kpi' }, el('div', { class: 'v', text: String(sm.pending) }), el('div', { class: 'l', text: 'بانتظار تصحيح المعلم' })) : null
    );
    const nodes = [el('div', { class: 'card' }, el('div', { class: 'kicker', text: rec.title }), el('h1', { text: 'النتيجة' }), kpis)];
    if (test) {
      nodes.push(el('div', { class: 'bandbox' }, el('div', { text: 'نطاق الجاهزية التقديري (قياساً بمستويات TIMSS الدولية):' }), el('div', { class: 'b', text: bandTxt }),
        el('div', { class: 'small', text: 'تقدير تقريبي مبني على نسبة إجابتك الصحيحة عن أسئلة كل مستوى، وليس درجة TIMSS رسمية.' })));
    }
    const tbl = (title, rows) => el('div', { class: 'card' }, el('h3', { text: title }), el('table', { class: 'tbl' }, el('thead', null, el('tr', null, el('th', { text: 'البند' }), el('th', { text: 'الدرجة' }), el('th', { text: '' }), el('th', { text: '%' }))), el('tbody', null, ...rows)));
    nodes.push(tbl('حسب المجال', D.DOMAIN_ORDER.filter((d) => sm.byDomain[d]).map((d) => barRow(D.domainName(d), sm.byDomain[d]))));
    nodes.push(tbl('حسب المستوى المعرفي', D.COG_ORDER.filter((c) => sm.byCog[c]).map((c) => barRow(D.cogName(c), sm.byCog[c], 'm'))));
    // التوصيات
    const weak = Object.entries(sm.byTopic).filter(([, v]) => v.m && v.p / v.m < 0.6).sort((a, b) => a[1].p / a[1].m - b[1].p / b[1].m).slice(0, 4);
    if (weak.length) {
      nodes.push(el('div', { class: 'card' }, el('h3', { text: '🎯 موضوعات أوصيك بالتدرب عليها' }),
        el('div', { class: 'chips' }, ...weak.map(([t]) => el('button', { class: 'chip', type: 'button', text: D.topicShort(t), on: { click: () => quickPractice(t) } })))));
    }
    // مراجعة الأسئلة
    const list = el('div', { class: 'list-items' });
    rec.items.forEach((r, k) => {
      const it = D.byId.get(r.id);
      if (!it) return;
      const status = r.pend ? el('span', { class: 'badge warn', text: 'بانتظار التصحيح' }) : r.c ? el('span', { class: 'badge ok', text: '✓ صحيح' }) : r.p > 0 ? el('span', { class: 'badge warn', text: 'جزئي' }) : el('span', { class: 'badge bad', text: r.r === null ? 'بلا إجابة' : '✗ خطأ' });
      list.append(el('div', { class: 'li' }, el('div', { class: 'meta' }, el('b', { text: 'السؤال ' + (k + 1) }), status, el('span', { class: 'badge', text: D.topicShort(it.topic) }), el('span', { class: 'badge m', text: D.cogName(it.cognitive) })),
        el('div', { class: 'small', html: U.rich(U.plain(it.stem).slice(0, 140) + (U.plain(it.stem).length > 140 ? '…' : '')) }),
        el('button', { class: 'btn ghost sm', type: 'button', text: 'عرض السؤال والحل', on: { click: () => reviewItem(it, r) } })));
    });
    nodes.push(el('div', { class: 'card' }, el('h3', { text: 'مراجعة الأسئلة' }), list));
    nodes.push(el('div', { class: 'row' }, el('button', { class: 'btn', type: 'button', text: 'العودة إلى لوحة الطالب', on: { click: T27.hub } }), el('button', { class: 'btn alt', type: 'button', text: '⬇ تصدير نتائجي (لإرسالها للمعلم)', on: { click: T27.exportMine } })));
    screen(nodes);
  };
  function quickPractice(topic) {
    const seen = D.seenSet();
    const pool = D.practicePool().filter((i) => i.topic === topic);
    const ids = U.shuffle(pool.filter((i) => !seen.has(i.id))).concat(U.shuffle(pool.filter((i) => seen.has(i.id)))).slice(0, 8).map((i) => i.id);
    T27.run(newSession('practice', 'تدريب: ' + D.topicShort(topic), [{ id: 'P', items: ids }], null));
  }
  function reviewItem(it, r) {
    const host = el('div');
    const ctl = I.render(it, host, { mode: 'review', response: r ? r.r : null, meta: true });
    ctl.lock(true);
    const res = I.score(it, r ? r.r : null);
    ctl.reveal(res);
    host.append(I.feedback(it, r ? r.r : null, res, null));
    U.modal({ title: 'مراجعة السؤال', body: host, actions: [{ label: 'إغلاق' }] }).box.style.maxWidth = '900px';
  }

  T27.exportMine = function () {
    const data = { app: 'TIMSS27-G8M', v: 1, exported: Date.now(), profile: S.profile, sessions: P.sessions() };
    const nm = (S.profile ? S.profile.name : 'student').replace(/\s+/g, '_');
    U.download(`TIMSS27_نتائج_${nm}_${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(data));
  };

  /* ============================================================ السجل */
  T27.history = function () {
    const sess = P.sessions().slice().sort((a, b) => b.finished - a.finished);
    const m = T27.mastery(sess);
    const rows = Object.keys(D.B.topics).map((t) => barRow(t + ' — ' + D.topicName(t), m[t].max ? m[t] : null, D.B.topics[t].domain === 'geometry_measurement' || D.B.topics[t].domain === 'data_probability' ? 'm' : ''));
    const types = { practice: 'تدريب', smart: 'تدريب ذكي', diagnostic: 'تشخيصي', sim: 'محاكاة', mock: 'تجريبي', psi: 'PSI' };
    const list = el('table', { class: 'tbl' }, el('thead', null, el('tr', null, el('th', { text: 'التاريخ' }), el('th', { text: 'النوع' }), el('th', { text: 'الجلسة' }), el('th', { text: 'الدرجة' }), el('th', { text: '' }))),
      el('tbody', null, ...sess.map((s) => {
        const sm = T27.summarize(s.items);
        return el('tr', null, el('td', { text: U.fmtDate(s.finished) }), el('td', { text: types[s.type] || s.type }), el('td', { text: s.title }), el('td', { text: sm.total.m ? Math.round((100 * sm.total.p) / sm.total.m) + '%' : '—', style: { direction: 'ltr' } }), el('td', null, el('button', { class: 'btn ghost sm', type: 'button', text: 'التفاصيل', on: { click: () => T27.results(s) } })));
      })));
    screen([
      el('div', { class: 'row' }, el('h1', { text: '📈 سجلي وتقدمي' }), el('span', { class: 'spacer' }), el('button', { class: 'btn alt sm', type: 'button', text: '⬇ تصدير نتائجي', on: { click: T27.exportMine } }), el('button', { class: 'btn ghost sm', type: 'button', text: 'رجوع', on: { click: T27.hub } })),
      el('div', { class: 'card' }, el('h3', { text: 'إتقان الموضوعات (آخر المحاولات)' }), el('table', { class: 'tbl' }, el('thead', null, el('tr', null, el('th', { text: 'الموضوع' }), el('th', { text: 'الدرجة' }), el('th', { text: '' }), el('th', { text: '%' }))), el('tbody', null, ...rows))),
      el('div', { class: 'card' }, el('h3', { text: 'الجلسات' }), sess.length ? list : el('p', { class: 'muted', text: 'لا توجد جلسات بعد.' })),
    ]);
  };

  /* ============================================================ مهام PSI */
  T27.psiList = function () {
    const cards = el('div', { class: 'grid-cards' });
    D.psi.forEach((t) =>
      cards.append(el('button', { class: 'tile gold', type: 'button', on: { click: () => T27.run(newSession('psi', 'PSI: ' + t.title, [{ id: t.id, items: t.items.map((i) => i.id) }], null)) } },
        el('span', { class: 'ic', text: '🧩' }), el('b', { text: t.title }), el('span', { class: 'muted small', text: `${t.items.length} أسئلة مترابطة` }), el('span', { class: 'go', text: 'ابدأ ←' })))
    );
    screen([el('div', { class: 'row' }, el('h1', { text: '🧩 مهام حل المشكلات والاستقصاء (PSI)' }), el('span', { class: 'spacer' }), el('button', { class: 'btn ghost sm', type: 'button', text: 'رجوع', on: { click: T27.hub } })),
      el('p', { class: 'muted', text: 'في كل مهمة موقف واحد تُبنى عليه عدة أسئلة، كما في مهام PSI في TIMSS. اقرأ السياق جيداً قبل الإجابة.' }),
      D.psi.length ? cards : el('div', { class: 'card muted', text: 'ستُضاف المهام قريباً.' })]);
  };

  /* ============================================================ الاختبارات التجريبية */
  T27.mocks = function () {
    const done = new Set(P.sessions().filter((s) => s.type === 'mock').map((s) => s.form));
    const cards = el('div', { class: 'grid-cards' });
    D.secure.forEach((f) =>
      cards.append(el('button', { class: 'tile maroon', type: 'button', on: { click: () => askCode(f) } }, el('span', { class: 'ic', text: '🔒' }), el('b', { text: f.title }), el('span', { class: 'muted small', text: `${f.n} سؤالاً · ${f.minutes} دقيقة` + (done.has(f.id) ? ' · أُنجز سابقاً' : '') }), el('span', { class: 'go', text: 'أدخل الرمز ←' })))
    );
    screen([el('div', { class: 'row' }, el('h1', { text: '🔒 الاختبارات التجريبية' }), el('span', { class: 'spacer' }), el('button', { class: 'btn ghost sm', type: 'button', text: 'رجوع', on: { click: T27.hub } })),
      el('p', { class: 'muted', text: 'كل اختبار كتلتان في 45 دقيقة مطابقتان لمخطط TIMSS 2027. يعطيك المعلم رمز الدخول عند بدء الاختبار.' }),
      D.secure.length ? cards : el('div', { class: 'card muted', text: 'لم تُضف الاختبارات التجريبية إلى هذه النسخة بعد.' })]);
  };
  function askCode(f) {
    const inp = el('input', { class: 'in', dir: 'ltr', placeholder: 'رمز الدخول', autocomplete: 'off', style: { textAlign: 'center', letterSpacing: '3px', fontSize: '1.3rem' } });
    U.modal({ title: 'رمز دخول: ' + f.title, body: el('div', null, el('p', { class: 'muted', text: 'اكتب الرمز الذي أعلنه المعلم.' }), inp),
      actions: [{ label: 'إلغاء', kind: 'ghost' }, { label: 'ابدأ الاختبار', onClick: async () => {
        try {
          const form = await D.decryptForm(f, inp.value);
          T27.run(newSession('mock', form.title || f.title, form.blocks.map((b) => ({ id: b.id, items: b.items.map((i) => i.id) })), (form.minutes || 45) * 60, { form: f.id, formData: form }));
          return true;
        } catch (e) {
          U.toast('الرمز غير صحيح.');
          inp.select();
          return false;
        }
      } }] });
  }

  /* ============================================================ وضع المعلم */
  const DEFAULT_PIN = '2027';
  T27.teacherLogin = function () {
    const inp = el('input', { class: 'in', type: 'password', dir: 'ltr', inputmode: 'numeric', placeholder: 'رمز المعلم', autocomplete: 'off' });
    U.modal({ title: '👩‍🏫 وضع المعلم', body: el('div', null, el('p', { class: 'muted small', text: 'الرمز الافتراضي مذكور في دليل التشغيل، ويمكن تغييره من الإعدادات.' }), inp),
      actions: [{ label: 'إلغاء', kind: 'ghost' }, { label: 'دخول', onClick: () => {
        const h = U.store.get('teacher.pin', U.hash(DEFAULT_PIN));
        if (U.hash(inp.value.trim()) !== h) {
          U.toast('الرمز غير صحيح');
          return false;
        }
        S.teacher = true;
        T27.teacher('bank');
        return true;
      } }] });
  };

  T27.teacher = function (tab) {
    if (!S.teacher) return T27.teacherLogin();
    const tabs = [['bank', '🗂️ بنك الأسئلة'], ['class', '📊 نتائج الصف'], ['mocks', '🔒 الاختبارات التجريبية'], ['docs', '📚 الإطار والمصادر'], ['settings', '⚙️ الإعدادات']];
    const bar = el('div', { class: 'tabs' }, ...tabs.map(([k, t]) => el('button', { type: 'button', class: k === tab ? 'on' : '', text: t, on: { click: () => T27.teacher(k) } })));
    const body = el('div');
    screen([el('div', { class: 'row' }, el('h1', { text: 'وضع المعلم' }), el('span', { class: 'spacer' }), el('button', { class: 'btn ghost sm', type: 'button', text: 'خروج', on: { click: () => { S.teacher = false; S.profile ? T27.hub() : T27.welcome(); } } })), bar, body]);
    ({ bank: teacherBank, class: teacherClass, mocks: teacherMocks, docs: teacherDocs, settings: teacherSettings }[tab] || teacherBank)(body);
  };

  /* ---------- بنك الأسئلة */
  const TB = { f: {}, page: 0, sel: new Set() };
  function teacherBank(host) {
    const f = TB.f;
    const mkSel = (key, label, opts) => {
      const s = el('select', { class: 'in', 'aria-label': label });
      s.append(el('option', { value: '', text: label }));
      opts.forEach(([v, t]) => s.append(el('option', { value: v, text: t })));
      s.value = f[key] || '';
      s.addEventListener('change', () => {
        f[key] = s.value;
        if (key === 'domain') f.topic = '';
        TB.page = 0;
        teacherBank((host.innerHTML = '', host));
      });
      return s;
    };
    const search = el('input', { class: 'in', placeholder: 'بحث في النص أو المعرّف…', value: f.text || '' });
    search.addEventListener('change', () => {
      f.text = search.value;
      TB.page = 0;
      teacherBank((host.innerHTML = '', host));
    });
    const filters = el('div', { class: 'grid-cards', style: { gridTemplateColumns: 'repeat(auto-fill,minmax(190px,1fr))' } },
      mkSel('domain', 'كل المجالات', D.DOMAIN_ORDER.map((d) => [d, D.domainName(d)])),
      mkSel('topic', 'كل الموضوعات', D.topicsOf(f.domain).map((t) => [t, t + ' ' + D.B.topics[t].area_ar])),
      mkSel('cognitive', 'كل المستويات المعرفية', D.COG_ORDER.map((c) => [c, D.cogName(c)])),
      mkSel('difficulty', 'كل الصعوبات', D.DIFF_ORDER.map((c) => [c, D.diffName(c)])),
      mkSel('format', 'كل الأنواع', Object.keys(D.B.formats).map((c) => [c, D.fmtName(c)])),
      mkSel('benchmark', 'كل المستويات الدولية', D.BM_ORDER.map((c) => [c, D.bmName(c)])),
      mkSel('context', 'كل السياقات', Object.keys(D.B.contexts).map((c) => [c, D.ctxName(c)])),
      search);
    const items = D.filter(f);
    const per = 12;
    const pages = Math.max(1, Math.ceil(items.length / per));
    TB.page = Math.min(TB.page, pages - 1);
    const pageItems = items.slice(TB.page * per, TB.page * per + per);
    const selInfo = el('b', { text: `محدد لورقة العمل: ${TB.sel.size}` });
    const tools = el('div', { class: 'row', style: { margin: '10px 0' } },
      el('span', { text: `${items.length} بنداً` }), el('span', { class: 'spacer' }), selInfo,
      el('button', { class: 'btn sm', type: 'button', text: '🖨️ طباعة ورقة عمل', on: { click: () => printWorksheet(false) } }),
      el('button', { class: 'btn alt sm', type: 'button', text: '🖨️ مع مفتاح الإجابة', on: { click: () => printWorksheet(true) } }),
      el('button', { class: 'btn ghost sm', type: 'button', text: 'تحديد الصفحة', on: { click: () => { pageItems.forEach((i) => TB.sel.add(i.id)); teacherBank((host.innerHTML = '', host)); } } }),
      el('button', { class: 'btn ghost sm', type: 'button', text: 'إلغاء التحديد', on: { click: () => { TB.sel.clear(); teacherBank((host.innerHTML = '', host)); } } }));
    const list = el('div', { class: 'list-items' });
    pageItems.forEach((it) => {
      const cb = el('input', { type: 'checkbox', 'aria-label': 'تحديد ' + it.id });
      cb.checked = TB.sel.has(it.id);
      cb.addEventListener('change', () => {
        cb.checked ? TB.sel.add(it.id) : TB.sel.delete(it.id);
        selInfo.textContent = `محدد لورقة العمل: ${TB.sel.size}`;
      });
      list.append(el('div', { class: 'li' },
        el('div', { class: 'meta' }, cb, el('code', { text: it.id }), el('span', { class: 'badge', text: D.topicShort(it.topic) }), el('span', { class: 'badge m', text: D.cogName(it.cognitive) + ' · ' + D.areaName(it.cognitive, it.area) }), el('span', { class: 'badge', text: D.diffName(it.difficulty) }), el('span', { class: 'badge warn', text: D.bmName(it.benchmark) }), el('span', { class: 'badge', text: D.fmtName(it.format) }), it.verified === true ? el('span', { class: 'badge ok', text: 'مُتحقق آلياً' }) : null),
        el('div', { html: U.rich(it.stem) }),
        el('div', { class: 'row' }, el('button', { class: 'btn ghost sm', type: 'button', text: '👁️ معاينة كاملة مع الحل', on: { click: () => previewItem(it) } }))));
    });
    const pager = el('div', { class: 'row', style: { justifyContent: 'center', marginTop: '10px' } },
      el('button', { class: 'btn ghost sm', type: 'button', text: '→ السابق', disabled: TB.page === 0 ? true : null, on: { click: () => { TB.page--; teacherBank((host.innerHTML = '', host)); } } }),
      el('span', { text: `صفحة ${TB.page + 1} من ${pages}` }),
      el('button', { class: 'btn ghost sm', type: 'button', text: 'التالي ←', disabled: TB.page >= pages - 1 ? true : null, on: { click: () => { TB.page++; teacherBank((host.innerHTML = '', host)); } } }));
    host.append(el('div', { class: 'card' }, filters, tools), list, pager);
  }
  function previewItem(it) {
    const host = el('div');
    const ctl = I.render(it, host, { mode: 'teacher', meta: true, showId: true });
    const res = { correct: true, points: it.points, max: it.points };
    ctl.set(demoResponse(it));
    ctl.lock(true);
    ctl.reveal(res);
    const fb = el('div', { class: 'feedback info' }, el('div', { class: 'ttl', text: 'الإجابة الصحيحة' }), el('div', { class: 'sec', html: U.rich(I.keyText(it)) }));
    if (it.rationale) fb.append(el('div', { class: 'sec', html: '<b>تفسير المشتّتات:</b><br>' + Object.entries(it.rationale).map(([k, v]) => '<b>' + k + ':</b> ' + U.rich(v)).join('<br>') }));
    if (it.rubric) fb.append(I.rubricNode(it));
    if (it.solution) fb.append(el('div', { class: 'sec', html: '<b>الحل:</b><br>' + U.rich(it.solution) }));
    if (it.remediation) fb.append(el('div', { class: 'sec', html: '<b>اقتراح علاجي:</b><br>' + U.rich(it.remediation) }));
    if (it.misconceptions) fb.append(el('div', { class: 'sec small muted', text: 'المفاهيم الخاطئة المستهدفة: ' + it.misconceptions.join('، ') }));
    if (it.qatar_link) fb.append(el('div', { class: 'sec small muted', text: 'الارتباط بمنهج قطر: ' + it.qatar_link }));
    host.append(fb);
    U.modal({ title: 'معاينة البند ' + it.id, body: host, actions: [{ label: 'إغلاق' }] }).box.style.maxWidth = '920px';
  }
  function demoResponse(it) {
    switch (it.format) {
      case 'mc':
        return it.key;
      case 'numeric':
        return String(it.answer.value);
      case 'multi_numeric':
        return it.fields.map((f) => String(f.value));
      case 'dragdrop_slots':
      case 'dragdrop_categorize':
        return it.key;
      case 'dragdrop_order':
        return it.key.slice();
      case 'grid_plot':
        return it.key.map((p) => p.slice());
      case 'select_explain':
        return { choice: it.key, text: '' };
      default:
        return null;
    }
  }
  function printWorksheet(withKey) {
    const ids = Array.from(TB.sel);
    if (!ids.length) return U.toast('حدد بنوداً أولاً من القائمة.');
    const root = document.getElementById('print-root');
    root.innerHTML = '';
    const head = el('div', null, el('h2', { text: (BR.school ? BR.school + ' — ' : '') + 'ورقة عمل: التدريب على TIMSS 2027 (رياضيات الصف الثامن)' }), el('div', { class: 'row' }, el('span', { text: 'الاسم: ....................................' }), el('span', { text: 'الشعبة: ..........' }), el('span', { text: 'التاريخ: ..........' })), el('p', { class: 'small', text: 'يُسمح باستعمال الآلة الحاسبة. أجب عن جميع الأسئلة.' }));
    root.append(head);
    ids.forEach((id, k) => root.append(I.printNode(D.byId.get(id), k + 1, false)));
    if (withKey) {
      root.append(el('div', { class: 'pbreak' }), el('h2', { text: 'مفتاح الإجابة ودليل التصحيح' }));
      ids.forEach((id, k) => root.append(I.printNode(D.byId.get(id), k + 1, true)));
    }
    document.body.classList.add('printing');
    const done = () => {
      document.body.classList.remove('printing');
      window.removeEventListener('afterprint', done);
    };
    window.addEventListener('afterprint', done);
    setTimeout(() => window.print(), 150);
  }

  /* ---------- نتائج الصف */
  const CL = () => U.store.get('class', { students: {} });
  const saveCL = (c) => U.store.set('class', c) || U.toast('تعذّر حفظ بيانات الصف (المساحة ممتلئة).');
  function teacherClass(host) {
    const data = CL();
    const file = el('input', { type: 'file', accept: '.json,application/json', multiple: true });
    file.addEventListener('change', async () => {
      const files = await U.readFiles(file.files);
      let n = 0;
      const d = CL();
      files.forEach((f) => {
        try {
          const j = JSON.parse(f.text);
          if (j.app !== 'TIMSS27-G8M' || !j.profile) return;
          const st = d.students[j.profile.id] || { profile: j.profile, sessions: {} };
          st.profile = j.profile;
          (j.sessions || []).forEach((s) => {
            const old = st.sessions[s.id];
            if (old) (s.items || []).forEach((r, k) => { const o = (old.items || [])[k]; if (o && o.teacher) Object.assign(r, { p: o.p, pend: false, c: o.c, teacher: true }); });
            st.sessions[s.id] = s;
          });
          d.students[j.profile.id] = st;
          n++;
        } catch (e) { /* ملف غير صالح */ }
      });
      saveCL(d);
      U.toast(`تم استيراد ${n} ملفاً`);
      T27.teacher('class');
    });
    const studs = Object.values(data.students);
    const typeSel = el('select', { class: 'in', style: { maxWidth: '280px' } });
    const forms = new Map();
    studs.forEach((st) => Object.values(st.sessions).forEach((s) => {
      const key = s.type === 'mock' ? 'mock:' + s.form : s.type;
      if (!forms.has(key)) forms.set(key, s.type === 'mock' ? 'تجريبي: ' + (s.title || s.form) : { diagnostic: 'التشخيصي', sim: 'المحاكاة', practice: 'التدريب', smart: 'التدريب الذكي', psi: 'PSI' }[s.type] || s.type);
    }));
    forms.forEach((t, k) => typeSel.append(el('option', { value: k, text: t })));
    const out = el('div');
    const render = () => {
      out.innerHTML = '';
      const key = typeSel.value;
      if (!key) return;
      const recs = [];
      studs.forEach((st) => {
        const ss = Object.values(st.sessions).filter((s) => (s.type === 'mock' ? 'mock:' + s.form : s.type) === key).sort((a, b) => b.finished - a.finished);
        if (ss.length) recs.push({ st, s: ss[0] });
      });
      // جدول الطلاب
      const rows = recs.map(({ st, s }) => {
        const sm = T27.summarize(s.items);
        const p = sm.total.m ? Math.round((100 * sm.total.p) / sm.total.m) : 0;
        return { st, s, sm, p };
      }).sort((a, b) => a.p - b.p);
      const bandName = (b) => (b ? D.bmName(b) : 'دون المنخفض');
      const bands = {};
      rows.forEach((r) => (bands[bandName(r.sm.band)] = (bands[bandName(r.sm.band)] || 0) + 1));
      out.append(el('div', { class: 'kpis' },
        el('div', { class: 'kpi' }, el('div', { class: 'v', text: String(rows.length) }), el('div', { class: 'l', text: 'طالباً' })),
        el('div', { class: 'kpi' }, el('div', { class: 'v', text: rows.length ? Math.round(rows.reduce((a, r) => a + r.p, 0) / rows.length) + '%' : '—' }), el('div', { class: 'l', text: 'متوسط الصف' })),
        ...Object.entries(bands).map(([b, n]) => el('div', { class: 'kpi' }, el('div', { class: 'v', text: String(n) }), el('div', { class: 'l', text: b })))));
      out.append(el('div', { class: 'card' }, el('h3', { text: 'الطلاب (من الأضعف إلى الأقوى) — لتشكيل مجموعات الدعم' }),
        el('table', { class: 'tbl' }, el('thead', null, el('tr', null, el('th', { text: 'الطالب' }), el('th', { text: 'الشعبة' }), el('th', { text: '%' }), el('th', { text: 'النطاق التقديري' }), el('th', { text: 'الأعداد' }), el('th', { text: 'الجبر' }), el('th', { text: 'الهندسة' }), el('th', { text: 'البيانات' }))),
          el('tbody', null, ...rows.map((r) => el('tr', null, el('td', { text: r.st.profile.name }), el('td', { text: r.st.profile.cls || '' }), el('td', { text: r.p + '%' }), el('td', { text: bandName(r.sm.band) }),
            ...D.DOMAIN_ORDER.map((d) => { const v = r.sm.byDomain[d]; return el('td', { text: v && v.m ? Math.round((100 * v.p) / v.m) + '%' : '—' }); })))))));
      // تحليل البنود
      const itemStats = {};
      recs.forEach(({ s }) => (s.items || []).forEach((r) => {
        const a = (itemStats[r.id] = itemStats[r.id] || { n: 0, p: 0, m: 0, choices: {}, blank: 0, tp: r.tp });
        a.n++;
        if (!r.pend) { a.p += r.p; a.m += r.m; }
        const it = D.byId.get(r.id);
        if (it && it.format === 'mc') { const ch = r.r || '—'; a.choices[ch] = (a.choices[ch] || 0) + 1; }
        if (r.r === null) a.blank++;
      }));
      const ist = Object.entries(itemStats).map(([id, a]) => ({ id, a, pv: a.m ? a.p / a.m : null })).sort((x, y) => (x.pv === null) - (y.pv === null) || x.pv - y.pv);
      out.append(el('div', { class: 'card' }, el('h3', { text: 'تحليل البنود (نسبة الصواب وتوزيع البدائل)' }),
        el('table', { class: 'tbl' }, el('thead', null, el('tr', null, el('th', { text: 'البند' }), el('th', { text: 'الموضوع' }), el('th', { text: 'نسبة الصواب' }), el('th', { text: 'البدائل (عدد الطلاب)' }), el('th', { text: 'بلا إجابة' }), el('th', { text: '' }))),
          el('tbody', null, ...ist.map(({ id, a, pv }) => {
            const it = D.byId.get(id);
            const ch = it && it.format === 'mc' ? 'ABCD'.split('').map((L) => (L === it.key ? '<b>' + L + '✓</b>' : L) + ':' + (a.choices[L] || 0)).join(' · ') : '—';
            return el('tr', null, el('td', null, el('code', { text: id })), el('td', { text: it ? it.topic : a.tp || '' }), el('td', null, el('div', { class: 'bar-h' }, el('i', { style: { width: (pv === null ? 0 : Math.round(pv * 100)) + '%' } })), el('span', { class: 'small', text: pv === null ? 'بانتظار التصحيح' : Math.round(pv * 100) + '%' })), el('td', { html: ch, style: { direction: 'ltr' } }), el('td', { text: String(a.blank) }), el('td', null, it ? el('button', { class: 'btn ghost sm', type: 'button', text: 'عرض', on: { click: () => previewItem(it) } }) : null));
          })))));
      // تصحيح الإجابات المفتوحة
      const pend = [];
      recs.forEach(({ st, s }) => (s.items || []).forEach((r, k) => { if (r.pend) pend.push({ st, s, r, k }); }));
      if (pend.length) {
        const q = el('div', { class: 'list-items' });
        pend.forEach(({ st, s, r, k }) => {
          const it = D.byId.get(r.id);
          if (!it) return;
          const btns = el('div', { class: 'row' });
          for (let pts = 0; pts <= (it.points || 1); pts++) {
            btns.append(el('button', { class: 'btn sm ' + (pts ? '' : 'alt'), type: 'button', text: String(pts) + (pts === (it.points || 1) ? ' (كاملة)' : ''), on: { click: () => {
              const d = CL();
              const rr = d.students[st.profile.id].sessions[s.id].items[k];
              rr.p = pts; rr.pend = false; rr.c = pts >= rr.m; rr.teacher = true;
              saveCL(d);
              U.toast('حُفظت الدرجة');
              T27.teacher('class');
            } } }));
          }
          const ans = r.r || {};
          q.append(el('div', { class: 'li' }, el('div', { class: 'meta' }, el('b', { text: st.profile.name }), el('code', { text: it.id })),
            el('div', { class: 'small', html: U.rich(it.stem) }),
            ans.choice ? el('div', { html: '<b>الاختيار:</b> ' + ans.choice + (ans.choice === it.key ? ' ✓' : ' ✗') }) : null,
            el('div', { class: 'feedback info', html: '<b>إجابة الطالب:</b><br>' + U.esc(ans.text || '—').replace(/\n/g, '<br>') }),
            I.rubricNode(it), btns));
        });
        out.append(el('div', { class: 'card' }, el('h3', { text: `✍️ إجابات تنتظر التصحيح (${pend.length})` }), q));
      }
      out.append(el('div', { class: 'row' }, el('button', { class: 'btn alt sm', type: 'button', text: '⬇ تصدير ملخص الطلاب CSV', on: { click: () => {
        const head = ['الطالب', 'الشعبة', 'النسبة', 'النطاق'].concat(D.DOMAIN_ORDER.map((d) => D.domainName(d)), D.COG_ORDER.map((c) => D.cogName(c)));
        const body = rows.map((r) => [r.st.profile.name, r.st.profile.cls || '', r.p, bandName(r.sm.band)].concat(D.DOMAIN_ORDER.map((d) => { const v = r.sm.byDomain[d]; return v && v.m ? Math.round((100 * v.p) / v.m) : ''; }), D.COG_ORDER.map((c) => { const v = r.sm.byCog[c]; return v && v.m ? Math.round((100 * v.p) / v.m) : ''; })));
        U.download('TIMSS27_ملخص_الصف.csv', U.csv([head].concat(body)), 'text/csv;charset=utf-8');
      } } }), el('button', { class: 'btn alt sm', type: 'button', text: '⬇ تصدير تحليل البنود CSV', on: { click: () => {
        const body = ist.map(({ id, a, pv }) => [id, (D.byId.get(id) || {}).topic || '', pv === null ? '' : Math.round(pv * 100), a.n, a.blank, JSON.stringify(a.choices)]);
        U.download('TIMSS27_تحليل_البنود.csv', U.csv([['البند', 'الموضوع', 'نسبة الصواب', 'عدد الطلاب', 'بلا إجابة', 'البدائل']].concat(body)), 'text/csv;charset=utf-8');
      } } })));
    };
    typeSel.addEventListener('change', render);
    host.append(el('div', { class: 'card' }, el('h3', { text: 'استيراد ملفات نتائج الطلاب' }),
      el('p', { class: 'muted small', text: 'يصدّر كل طالب ملف نتائجه من شاشة «سجلي» أو «النتيجة»، ثم تستورد الملفات هنا (يمكن اختيار عدة ملفات معاً). تبقى البيانات على جهازك فقط.' }),
      el('div', { class: 'row' }, file, el('span', { class: 'spacer' }), el('span', { class: 'muted', text: `الطلاب المستوردون: ${studs.length}` }), studs.length ? el('button', { class: 'btn ghost sm', type: 'button', text: 'حذف بيانات الصف', on: { click: async () => { if (await U.confirm('حذف بيانات الصف', 'سيُحذف كل ما استوردته على هذا الجهاز.', 'حذف')) { U.store.del('class'); T27.teacher('class'); } } } }) : null),
      studs.length ? el('div', { class: 'row', style: { marginTop: '10px' } }, el('b', { text: 'نوع الجلسة:' }), typeSel) : null), out);
    if (studs.length) render();
  }

  /* ---------- الاختبارات التجريبية (معاينة المعلم) */
  function teacherMocks(host) {
    host.append(el('p', { class: 'muted', text: 'لمعاينة نموذج وطباعته مع مفتاحه، أدخل رمزه. الرموز محفوظة في ملف المعلم (02_بنك_الأسئلة/secure/access_codes.yaml) ولا تُضمَّن في هذا الملف.' }));
    if (!D.secure.length) return host.append(el('div', { class: 'card muted', text: 'لم تُضف الاختبارات التجريبية إلى هذه النسخة بعد.' }));
    D.secure.forEach((f) => {
      const inp = el('input', { class: 'in', dir: 'ltr', placeholder: 'الرمز', style: { maxWidth: '180px' } });
      host.append(el('div', { class: 'card' }, el('h3', { text: f.title }), el('p', { class: 'muted', text: `${f.n} سؤالاً · ${f.minutes} دقيقة` }), el('div', { class: 'row' }, inp,
        el('button', { class: 'btn sm', type: 'button', text: 'فتح وطباعة مع المفتاح', on: { click: async () => {
          try {
            const form = await D.decryptForm(f, inp.value);
            TB.sel = new Set(form.blocks.reduce((a, b) => a.concat(b.items.map((i) => i.id)), []));
            printWorksheet(true);
          } catch (e) { U.toast('الرمز غير صحيح'); }
        } } }))));
    });
  }

  /* ---------- الوثائق */
  // مقطع لاتيني أو رياضي داخل نص عربي (عدد بإشارته، تعبير، وحدة، رمز درس): يُعزل LTR حتى لا ينقلب ترتيبه
  // مثل «2 + 3 × 4» (لا «4 × 3 + 2») و«12 cm» (لا «cm 12») و«−10» و«1-1 … 1-9»
  // و«V = π × r² × h» كاملة، والقوس الذي لا يقابله قوس داخل المقطع يبقى خارجه مع النص العربي: «(الجواب: 9 + 16 = 25)»
  // والنقطتان والنقطة داخل المقطع فقط ملاصقتين لرقم بعدهما أو بمسافتين حول النقطتين (6:00، 3.14، 1 : 50)،
  // فلا يلتصق رقم الخطوة بالصيغة بعده: «الخطوة 4: V = …» (بلا lookbehind ليعمل في متصفحات iPad القديمة)
  const LTR_RUN = /[+−-]?[0-9A-Za-z√(π](?:[0-9A-Za-z ,/()+−×÷=<>≤≥≈%°²³…√π-]| :(?= [0-9])|[:.](?=[0-9]))*[0-9A-Za-z%)°²³π]|[+−-]?[0-9A-Za-zπ]/g;
  function isolateLtr(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: (n) => (/[؀-ۿ]/.test(n.data) && /[0-9A-Za-zπ]/.test(n.data) && !n.parentElement.closest('code, pre, bdi, .katex') ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT),
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((n) => {
      const frag = document.createDocumentFragment();
      let last = 0;
      const put = (s, e) => { // يعزل [s, e) بعد فصل أي قوس لا يقابله قوس داخل المقطع: «الحصة 1 (45 دقيقة)»
        while (e > s && n.data[e - 1] === ' ') e--;
        while (e > s && n.data[s] === ' ') s++;
        if (e <= s) return;
        const t = n.data.slice(s, e), open = [];
        let cut = -1;
        for (let i = 0; i < t.length && cut < 0; i++) {
          if (t[i] === '(') open.push(i);
          else if (t[i] === ')') { if (open.length) open.pop(); else cut = i; }
        }
        if (cut < 0 && open.length) cut = open[0];
        if (cut >= 0) { put(s, s + cut); put(s + cut + 1, e); return; }
        if (s > last) frag.append(n.data.slice(last, s));
        const b = document.createElement('bdi');
        b.dir = 'ltr';
        b.textContent = t;
        frag.append(b);
        last = e;
      };
      n.data.replace(LTR_RUN, (m, off) => { put(off, off + m.length); return m; });
      if (last < n.data.length) frag.append(n.data.slice(last));
      n.replaceWith(frag);
    });
  }
  function mdToHtml(md) {
    if (window.marked) {
      try {
        const box = document.createElement('div');
        box.innerHTML = window.marked.parse ? window.marked.parse(md) : window.marked(md);
        isolateLtr(box);
        return box.innerHTML;
      } catch (e) { /* يتابع */ }
    }
    return '<pre style="white-space:pre-wrap">' + U.esc(md) + '</pre>';
  }
  T27.mdToHtml = mdToHtml;
  T27.isolateLtr = isolateLtr;
  T27.doc = function (id, back) {
    const d = (window.DOCS || []).find((x) => x.id === id);
    if (!d) return;
    screen([el('div', { class: 'row' }, el('h1', { text: d.title }), el('span', { class: 'spacer' }), el('button', { class: 'btn ghost sm', type: 'button', text: 'رجوع', on: { click: back || T27.hub } })), el('article', { class: 'doc', html: mdToHtml(d.md) })]);
  };
  function teacherDocs(host) {
    const docs = window.DOCS || [];
    if (!docs.length) return host.append(el('div', { class: 'card muted', text: 'لا توجد وثائق في هذه النسخة.' }));
    const g = el('div', { class: 'grid-cards' });
    docs.forEach((d) => g.append(el('button', { class: 'tile', type: 'button', on: { click: () => T27.doc(d.id, () => T27.teacher('docs')) } }, el('span', { class: 'ic', text: '📄' }), el('b', { text: d.title }), el('span', { class: 'muted small', text: d.desc || '' }), el('span', { class: 'go', text: 'فتح ←' }))));
    host.append(g);
  }

  /* ---------- الإعدادات */
  function teacherSettings(host) {
    const p1 = el('input', { class: 'in', type: 'password', dir: 'ltr', placeholder: 'الرمز الجديد', style: { maxWidth: '220px' } });
    host.append(
      el('div', { class: 'card' }, el('h3', { text: 'تغيير رمز المعلم (على هذا الجهاز)' }), el('div', { class: 'row' }, p1, el('button', { class: 'btn sm', type: 'button', text: 'حفظ', on: { click: () => { if (p1.value.trim().length < 4) return U.toast('4 خانات على الأقل'); U.store.set('teacher.pin', U.hash(p1.value.trim())); U.toast('تم تغيير الرمز'); p1.value = ''; } } }))),
      el('div', { class: 'card' }, el('h3', { text: 'معلومات النسخة' }), el('p', { html: `عدد بنود التدريب: <b>${D.items.length}</b> · مهام PSI: <b>${D.psi.length}</b> · اختبارات تجريبية: <b>${D.secure.length}</b><br>تاريخ البناء: <span dir="ltr">${U.esc(D.build.built || '')}</span>` })),
      el('div', { class: 'card' }, el('h3', { text: 'بيانات هذا الجهاز' }), el('p', { class: 'muted small', text: 'تُحفظ حسابات الطلاب ونتائجهم في متصفح هذا الجهاز فقط.' }),
        el('button', { class: 'btn ghost', type: 'button', text: 'حذف جميع بيانات المنصة من هذا الجهاز', on: { click: async () => { if (await U.confirm('حذف كل البيانات', 'سيُحذف كل الطلاب والنتائج وبيانات الصف من هذا المتصفح نهائياً.', 'حذف الكل')) { try { Object.keys(localStorage).filter((k) => k.startsWith('t27.')).forEach((k) => localStorage.removeItem(k)); } catch (e) { /* */ } location.reload(); } } } }))
    );
  }
})();
