/* ==========================================================================
   90_main.js — التشغيل
   ========================================================================== */
'use strict';
(function () {
  const U = T27.U;
  const font = U.store.get('font', '');
  if (font) document.body.classList.add(font);
  window.addEventListener('error', (e) => {
    try {
      console.error(e.error || e.message);
      U.toast('حدث خطأ غير متوقع. إن تكرر، أعد تحميل الصفحة؛ إجاباتك محفوظة.');
    } catch (x) { /* تجاهل */ }
  });
  const p = T27.P.current();
  if (p) {
    T27.S.profile = p;
    T27.hub();
  } else T27.welcome();
})();
