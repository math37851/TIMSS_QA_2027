/* ==========================================================================
   10_data.js — الوصول إلى البنك: الفهارس، التسميات، التصفية، تجميع النماذج، فك التشفير
   ========================================================================== */
'use strict';
(function () {
  const U = T27.U;
  const B = window.BANK || { items: [], psi: [], topics: {}, domains: {}, cognitive_domains: {}, benchmarks: {}, difficulty_levels: {}, formats: {}, contexts: {}, forms: {} };
  const D = (T27.D = { B });

  D.items = B.items || [];
  D.psi = B.psi || [];
  D.byId = new Map();
  D.items.forEach((i) => D.byId.set(i.id, i));
  D.psi.forEach((t) => (t.items || []).forEach((i) => D.byId.set(i.id, i)));
  D.secure = (window.SECURE && window.SECURE.forms) || [];
  D.build = window.BUILD_INFO || {};

  const DOMAIN_ORDER = ['number', 'algebra', 'geometry_measurement', 'data_probability'];
  D.DOMAIN_ORDER = DOMAIN_ORDER;
  D.COG_ORDER = ['knowing', 'applying', 'reasoning'];
  D.DIFF_ORDER = ['foundation', 'easy', 'medium', 'hard'];
  D.BM_ORDER = ['low', 'intermediate', 'high', 'advanced'];

  D.domainName = (d) => (B.domains[d] || {}).ar || d;
  D.topicName = (t) => (B.topics[t] || {}).ar || t;
  D.topicShort = (t) => {
    const tp = B.topics[t];
    return tp ? t + ' · ' + tp.area_ar : t;
  };
  D.cogName = (c) => (B.cognitive_domains[c] || {}).ar || c;
  D.areaName = (c, a) => ((B.cognitive_domains[c] || {}).areas || {})[a] || a;
  D.diffName = (d) => (B.difficulty_levels[d] || {}).ar || d;
  D.bmName = (b) => (B.benchmarks[b] || {}).ar || b;
  D.fmtName = (f) => (B.formats[f] || {}).ar || f;
  D.ctxName = (c) => B.contexts[c] || c;
  D.topicsOf = (domain) => Object.keys(B.topics).filter((t) => !domain || B.topics[t].domain === domain);

  /** تصفية البنود (pool اختياري: افتراضياً البنك كله كما في تصفح المعلم) */
  D.filter = function (f, pool) {
    f = f || {};
    const q = (f.text || '').trim();
    return (pool || D.items).filter((i) => {
      if (f.domain && i.domain !== f.domain) return false;
      if (f.topic && i.topic !== f.topic) return false;
      if (f.cognitive && i.cognitive !== f.cognitive) return false;
      if (f.difficulty && i.difficulty !== f.difficulty) return false;
      if (f.format && i.format !== f.format) return false;
      if (f.benchmark && i.benchmark !== f.benchmark) return false;
      if (f.context && i.context !== f.context) return false;
      if (q && !(i.id.includes(q) || U.plain(i.stem).includes(q))) return false;
      return true;
    });
  };

  /** جلسات الملف الحالي (T27.P يُعرَّف لاحقاً في 40_screens.js، ويُستدعى هنا وقت التشغيل فقط) */
  const sessions = () => (T27.P && T27.P.sessions ? T27.P.sessions() : []) || [];

  /** سجل ما رآه الطالب (لتفضيل البنود الجديدة) */
  D.seenSet = function () {
    const s = new Set();
    sessions().forEach((ss) => (ss.items || []).forEach((r) => s.add(r.id)));
    return s;
  };

  /** بنود التشخيصي تُحجب عن تدريب الطالب ومحاكاته حتى يُنهي التشخيصي، لتبقى نتيجته مؤشراً صادقاً */
  const diagRaw = ((B.forms || {}).diagnostic || {}).items;
  D.diagIds = Array.isArray(diagRaw) ? diagRaw : [];
  D.diagSet = new Set(D.diagIds);
  D.diagDone = () => sessions().some((s) => s.type === 'diagnostic');
  D.practicePool = function () {
    if (!D.diagSet.size || D.diagDone()) return D.items;
    return D.items.filter((i) => !D.diagSet.has(i.id));
  };

  /** اختيار n بنود من مجموعة مع تفضيل غير المرئية ثم تنويع المستويات المعرفية */
  function pick(pool, n, seen) {
    const fresh = U.shuffle(pool.filter((i) => !seen.has(i.id)));
    const old = U.shuffle(pool.filter((i) => seen.has(i.id)));
    return fresh.concat(old).slice(0, n);
  }

  /** نموذج محاكاة عشوائي وفق مخطط TIMSS (32 بنداً: 10/10/6/6) */
  D.assembleSim = function () {
    const fm = (B.forms && B.forms.mock) || { content: { number: 10, algebra: 10, geometry_measurement: 6, data_probability: 6 } };
    const seen = D.seenSet();
    let chosen = [];
    for (const d of DOMAIN_ORDER) {
      const need = fm.content[d] || 0;
      // طابور لكل موضوع: غير المرئية أولاً ثم المرئية، ثم سحب دوري بين الموضوعات لتنويعها
      const byTopic = {};
      D.practicePool().filter((i) => i.domain === d).forEach((i) => (byTopic[i.topic] = byTopic[i.topic] || []).push(i));
      const queues = U.shuffle(Object.keys(byTopic)).map((t) => pick(byTopic[t], byTopic[t].length, seen));
      const picked = [];
      let progress = true;
      while (picked.length < need && progress) {
        progress = false;
        for (const q of queues) {
          if (picked.length >= need) break;
          if (q.length) {
            picked.push(q.shift());
            progress = true;
          }
        }
      }
      chosen = chosen.concat(picked);
    }
    return orderForTest(chosen);
  };

  /** ترتيب بنود الاختبار: يبدأ بالأسهل كما في كتل TIMSS، مع تقسيم إلى كتلتين */
  function orderForTest(items) {
    const rank = { foundation: 0, easy: 1, medium: 2, hard: 3 };
    const half = Math.ceil(items.length / 2);
    const sh = U.shuffle(items);
    const b1 = sh.slice(0, half).sort((a, b) => rank[a.difficulty] - rank[b.difficulty]);
    const b2 = sh.slice(half).sort((a, b) => rank[a.difficulty] - rank[b.difficulty]);
    return [
      { id: 'B1', items: b1.map((i) => i.id) },
      { id: 'B2', items: b2.map((i) => i.id) },
    ];
  }
  D.orderForTest = orderForTest;

  /** الاختبار التشخيصي: من forms.diagnostic إن وُجد، وإلا يُجمَّع تلقائياً بند لكل موضوع + بنود من مجالي الضعف */
  D.diagnosticBlocks = function () {
    let items = D.diagIds.map((id) => D.byId.get(id)).filter(Boolean);
    if (items.length < 8) {
      items = [];
      Object.keys(B.topics).forEach((t) => {
        const pool = D.items.filter((i) => i.topic === t && ['foundation', 'easy', 'medium'].includes(i.difficulty));
        const alt = D.items.filter((i) => i.topic === t);
        const c = U.sample(pool.length ? pool : alt, 1);
        items = items.concat(c);
      });
      const extra = D.items.filter((i) => ['geometry_measurement', 'data_probability'].includes(i.domain) && !items.includes(i));
      items = items.concat(U.sample(extra, Math.max(0, 32 - items.length)));
    }
    const half = Math.ceil(items.length / 2);
    return [
      { id: 'B1', items: items.slice(0, half).map((i) => i.id) },
      { id: 'B2', items: items.slice(half).map((i) => i.id) },
    ];
  };

  /** فك تشفير نموذج تجريبي محمي (AES-GCM + PBKDF2-SHA256) */
  D.decryptForm = async function (desc, code) {
    if (!window.crypto || !crypto.subtle) throw new Error('المتصفح لا يدعم فك التشفير (WebCrypto)');
    const enc = new TextEncoder();
    const baseKey = await crypto.subtle.importKey('raw', enc.encode(code.trim().toUpperCase()), 'PBKDF2', false, ['deriveKey']);
    const key = await crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt: U.base64ToBytes(desc.salt), iterations: desc.iter, hash: 'SHA-256' },
      baseKey,
      { name: 'AES-GCM', length: 256 },
      false,
      ['decrypt']
    );
    const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: U.base64ToBytes(desc.iv) }, key, U.base64ToBytes(desc.ct));
    const form = JSON.parse(new TextDecoder().decode(plain));
    form.blocks.forEach((b) => b.items.forEach((i) => D.byId.set(i.id, i)));
    return form;
  };

  /** تعليمات الإجابة لكل نوع (تظهر فوق منطقة الإجابة) */
  D.HOWTO = {
    mc: 'اختر إجابة واحدة بالنقر عليها.',
    numeric: 'اكتب إجابتك في الخانة باستعمال لوحة الأرقام أو لوحة المفاتيح.',
    multi_numeric: 'اكتب إجابة في كل خانة.',
    dragdrop_slots: 'اسحب البطاقات إلى الخانات، أو انقر البطاقة ثم انقر الخانة.',
    dragdrop_order: 'رتّب البطاقات بسحبها إلى المواقع المرقمة، أو انقر البطاقة ثم انقر الموقع.',
    dragdrop_categorize: 'اسحب كل بطاقة إلى المجموعة المناسبة، أو انقر البطاقة ثم انقر المجموعة.',
    grid_plot: 'انقر نقاط الشبكة لتحديد الرؤوس. استعمل «تراجع» أو «مسح» للتعديل.',
    select_explain: 'اختر إجابتك، ثم اكتب تبريرك في المربع.',
    cr_explain: 'اكتب إجابتك وتوضيحك في المربع.',
  };
})();
