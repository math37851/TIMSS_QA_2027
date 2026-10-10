# -*- coding: utf-8 -*-
"""
test_platform.py — اختبارات آلية شاملة للمنصة (الملف الواحد) عبر Playwright ودون شبكة.

  python test_platform.py              # الاختبارات الوظيفية
  python test_platform.py --screens    # + لقطة شاشة لكل بند في 02_بنك_الأسئلة/reports/screens/
  python test_platform.py --codes      # + اختبار فك تشفير الاختبارات التجريبية بالرموز الحقيقية

يعيد رمز خروج 1 عند فشل أي اختبار.
"""

import argparse
import json
import pathlib
import sys

import yaml
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
HTML = ROOT / "03_منصة_التدريب_eTIMSS" / "منصة_TIMSS_رياضيات_الصف_الثامن.html"
SCREENS = ROOT / "02_بنك_الأسئلة" / "reports" / "screens"
CODES = ROOT / "02_بنك_الأسئلة" / "secure" / "access_codes.yaml"

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("  ✅ " if cond else "  ❌ ") + name + (f" — {detail}" if detail and not cond else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screens", action="store_true")
    ap.add_argument("--codes", action="store_true")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    url = HTML.resolve().as_uri()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=not args.headed)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="ar-QA", accept_downloads=True)
        ctx.set_offline(True)
        page = ctx.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        requests = []
        page.on("request", lambda r: requests.append(r.url) if not r.url.startswith(("file:", "data:", "blob:")) else None)

        print("▶ التحميل")
        page.goto(url)
        page.wait_for_timeout(800)
        check("تُحمَّل الصفحة دون أخطاء", not errors, "; ".join(errors[:3]))
        check("لا طلبات شبكة خارجية (يعمل دون إنترنت)", not requests, ", ".join(requests[:3]))
        n_items = page.evaluate("T27.D.items.length")
        check("البنك محمَّل", n_items > 0, str(n_items))

        print("▶ الحاسبة")
        calc = page.evaluate("""() => { const C = T27.Calc; const seq = (ks) => { C.press('C'); ks.forEach(k => C.press(k)); return C.display(); };
            return { a: seq(['2','+','3','×','4','=']), b: seq(['1','6','√']), c: seq(['5','÷','0','=']), d: seq(['5','±']), e: seq(['7','−','9','=']),
                     f: seq(['0','.','1','+','0','.','2','=']), g: seq(['1','0','÷','4','=']) }; }""")
        check("2 + 3 × 4 = 20 (عملية واحدة في كل مرة)", calc["a"] == "20", calc["a"])
        check("√16 = 4", calc["b"] == "4", calc["b"])
        check("القسمة على صفر ← Error", calc["c"] == "Error", calc["c"])
        check("الإشارة السالبة", calc["d"] == "-5", calc["d"])
        check("7 − 9 = −2", calc["e"] == "-2", calc["e"])
        check("0.1 + 0.2 = 0.3", calc["f"] == "0.3", calc["f"])
        check("10 ÷ 4 = 2.5", calc["g"] == "2.5", calc["g"])

        print("▶ محرك التصحيح (كل البنود بإجاباتها الصحيحة والخاطئة)")
        sc = page.evaluate("""() => {
          const out = [];
          const demo = (it) => { switch (it.format) {
            case 'mc': return it.key; case 'numeric': return String(it.answer.value);
            case 'multi_numeric': return it.fields.map(f => String(f.value));
            case 'dragdrop_slots': case 'dragdrop_categorize': return it.key;
            case 'dragdrop_order': return it.key.slice(); case 'grid_plot': return it.key.map(p => p.slice());
            case 'select_explain': return {choice: it.key, text: 'x', human: it.points || 1};
            case 'cr_explain': return {text: 'x', human: it.points || 1}; } };
          const wrong = (it) => { switch (it.format) {
            case 'mc': return 'ABCD'.split('').find(L => L !== it.key); case 'numeric': return String(Number(it.answer.value) + Math.max(1, 2 * (Number(it.answer.tol) || 0) + 1));
            case 'multi_numeric': return it.fields.map(f => String(Number(f.value) + Math.max(1, 2 * (Number(f.tol) || 0) + 1)));
            case 'dragdrop_order': return it.key.slice().reverse();
            case 'grid_plot': return it.key.map(p => [p[0] + 1, p[1]]);
            case 'dragdrop_categorize': { const r = {}; Object.keys(it.key).forEach(c => r[c] = it.categories.find(x => x !== it.key[c])); return r; }
            case 'dragdrop_slots': { const ids = it.cards.map(c => c.id); const r = Object.assign({}, it.key); const s0 = Object.keys(r)[0];
                                     const used = Object.values(it.key); r[s0] = ids.find(c => !used.includes(c)) || ids.find(c => c !== it.key[s0]); return r; }
            default: return null; } };
          const all = T27.D.items.concat(...T27.D.psi.map(t => t.items));
          all.forEach(it => {
            const g = T27.I.score(it, demo(it)); const b = T27.I.score(it, wrong(it));
            out.push({id: it.id, fmt: it.format, good: g.points === g.max, bad: b.points < b.max || it.format.endsWith('explain'), gp: g.points, bp: b.points});
          });
          return out; }""")
        bad_good = [s["id"] for s in sc if not s["good"]]
        bad_bad = [s["id"] for s in sc if not s["bad"]]
        check(f"الإجابة الصحيحة تنال الدرجة الكاملة ({len(sc)} بنداً)", not bad_good, ", ".join(bad_good))
        check("الإجابة الخاطئة لا تنال الدرجة الكاملة", not bad_bad, ", ".join(bad_bad))

        print("▶ الرياضيات والعرض")
        raw = page.evaluate("""() => { const host = document.createElement('div'); document.body.append(host); const bad = [];
          T27.D.items.forEach(it => { host.innerHTML = ''; T27.I.render(it, host, {mode:'review'});
            const txt = host.querySelector('.stem').innerText; if (/\\$/.test(txt)) bad.push(it.id);
            if (host.querySelector('.katex-error')) bad.push(it.id + ':katex'); });
          host.remove(); return bad; }""")
        check("لا رموز $ خام ولا أخطاء KaTeX في نص البنود", not raw, ", ".join(raw))
        narrow = page.evaluate("""() => { const host = document.createElement('div'); host.style.width = '320px'; document.body.append(host); const bad = [];
          T27.D.items.concat(...T27.D.psi.map(t => t.items)).forEach(it => { host.innerHTML = ''; T27.I.render(it, host, {mode:'review'});
            host.querySelectorAll('svg.fig').forEach(s => { if (s.getBoundingClientRect().width > 321) bad.push(it.id); }); });
          host.remove(); return [...new Set(bad)]; }""")
        check("الرسوم تتقلّص داخل شاشة ضيقة (320px) دون تجاوز", not narrow, ", ".join(narrow[:10]))
        prn = page.evaluate(r"""() => { const host = document.createElement('div'); document.body.append(host); const bad = [];
          T27.D.items.concat(...T27.D.psi.map(t => t.items)).forEach(it => { [false, true].forEach(k => { host.innerHTML = ''; host.append(T27.I.printNode(it, 1, k));
            const t = host.innerText; if (t.includes('$') || t.includes('boxed') || host.querySelector('.katex-error')) bad.push(it.id + (k ? ':key' : '')); }); });
          host.remove(); return bad; }""")
        check("نسخة الطباعة وورقة المفتاح بلا رموز $ أو LaTeX خام", not prn, ", ".join(prn[:10]))
        docs_bad = page.evaluate(r"""() => { const bad = [];
          (window.DOCS || []).forEach(d => { const box = document.createElement('div'); box.innerHTML = T27.mdToHtml(d.md);
            const w = document.createTreeWalker(box, NodeFilter.SHOW_TEXT); let n;
            while ((n = w.nextNode())) { if (n.parentElement.closest('bdi, code, pre')) continue;
              if (/[؀-ۿ]/.test(n.data) && /[0-9A-Za-zπ]/.test(n.data)) bad.push(d.id + ': ' + n.data.trim().slice(0, 30)); }
            box.querySelectorAll('bdi').forEach(b => { const t = b.textContent;
              if ((t.match(/\(/g) || []).length !== (t.match(/\)/g) || []).length) bad.push(d.id + ': قوس مبتور ' + t.slice(0, 30)); }); });
          return bad; }""")
        check("الأدلة: كل مقطع لاتيني أو رياضي داخل النص العربي معزول الاتجاه", not docs_bad, " | ".join(docs_bad[:5]))

        print("▶ الدخول وجولة الطالب")
        page.fill("input[aria-label='الاسم']", "طالب تجريبي")
        page.fill("input[aria-label='الشعبة']", "8/1")
        page.click("text=ابدأ التدريب")
        page.wait_for_timeout(300)
        check("لوحة الطالب تظهر", page.locator("text=الاختبار التشخيصي").count() > 0)

        # جلسة تدريب على بند اختيار من متعدد
        mc_id = page.evaluate("T27.D.items.find(i => i.format === 'mc').id")
        page.evaluate(f"T27.run(Object.assign({{id:'t1', type:'practice', title:'اختبار', blocks:[{{id:'P', items:['{mc_id}']}}], started: Date.now(), cur:0, responses:{{}}, flags:{{}}, times:{{}}, checked:{{}}, results:{{}}}}))")
        page.wait_for_timeout(300)
        key = page.evaluate(f"T27.D.byId.get('{mc_id}').key")
        page.click(f".opt[data-l='{key}']")
        page.click("text=✓ تحقق")
        page.wait_for_timeout(300)
        check("التحقق في التدريب يعرض «إجابة صحيحة»", page.locator(".feedback.ok").count() == 1)
        page.click("text=إنهاء وعرض النتيجة")
        page.wait_for_timeout(300)
        check("شاشة النتيجة تظهر بنسبة 100%", page.locator(".kpi .v").first.inner_text().strip() == "100%", page.locator(".kpi .v").first.inner_text())

        # سحب وإفلات فعلي بالفأرة (ترتيب)
        ord_id = page.evaluate("(T27.D.items.find(i => i.format === 'dragdrop_order') || {}).id")
        if ord_id:
            page.evaluate(f"T27.run(Object.assign({{id:'t2', type:'practice', title:'ترتيب', blocks:[{{id:'P', items:['{ord_id}']}}], started: Date.now(), cur:0, responses:{{}}, flags:{{}}, times:{{}}, checked:{{}}, results:{{}}}}))")
            page.wait_for_timeout(300)
            keys = page.evaluate(f"T27.D.byId.get('{ord_id}').key")
            for k, cid in enumerate(keys):
                card = page.locator(f".tray .dcard[data-card='{cid}']")
                slot = page.locator(f".slot[data-pos='{k}']")
                cb, sb = card.bounding_box(), slot.bounding_box()
                page.mouse.move(cb["x"] + cb["width"] / 2, cb["y"] + cb["height"] / 2)
                page.mouse.down()
                page.mouse.move(cb["x"] + 30, cb["y"] + 30, steps=4)
                page.mouse.move(sb["x"] + sb["width"] / 2, sb["y"] + sb["height"] / 2, steps=8)
                page.mouse.up()
                page.wait_for_timeout(120)
            page.click("text=✓ تحقق")
            page.wait_for_timeout(250)
            check("السحب والإفلات بالفأرة (ترتيب) يُصحَّح صحيحاً", page.locator(".feedback.ok").count() == 1)

        # نقر ثم نقر (خانات)
        sl_id = page.evaluate("(T27.D.items.find(i => i.format === 'dragdrop_slots') || {}).id")
        if sl_id:
            page.evaluate(f"T27.run(Object.assign({{id:'t3', type:'practice', title:'خانات', blocks:[{{id:'P', items:['{sl_id}']}}], started: Date.now(), cur:0, responses:{{}}, flags:{{}}, times:{{}}, checked:{{}}, results:{{}}}}))")
            page.wait_for_timeout(300)
            key = page.evaluate(f"T27.D.byId.get('{sl_id}').key")
            for s, cid in key.items():
                page.click(f".tray .dcard[data-card='{cid}']")
                page.click(f".slot[data-slot='{s}']")
                page.wait_for_timeout(80)
            page.click("text=✓ تحقق")
            page.wait_for_timeout(250)
            check("وضع «انقر ثم انقر» (خانات) يعمل ويُصحَّح", page.locator(".feedback.ok").count() == 1)

        # الرسم على الشبكة
        gp_id = page.evaluate("(T27.D.items.find(i => i.format === 'grid_plot') || {}).id")
        if gp_id:
            page.evaluate(f"T27.run(Object.assign({{id:'t4', type:'practice', title:'شبكة', blocks:[{{id:'P', items:['{gp_id}']}}], started: Date.now(), cur:0, responses:{{}}, flags:{{}}, times:{{}}, checked:{{}}, results:{{}}}}))")
            page.wait_for_timeout(300)
            for x, y in page.evaluate(f"T27.D.byId.get('{gp_id}').key"):
                page.locator(f".hitpt[data-x='{x}'][data-y='{y}']").click()
            page.click("text=✓ تحقق")
            page.wait_for_timeout(250)
            check("الرسم على المستوى الإحداثي يُصحَّح صحيحاً", page.locator(".feedback.ok").count() == 1)

        # الإدخال الرقمي عبر لوحة الأرقام
        nm_id = page.evaluate("(T27.D.items.find(i => i.format === 'numeric') || {}).id")
        if nm_id:
            page.evaluate(f"T27.run(Object.assign({{id:'t5', type:'practice', title:'رقمي', blocks:[{{id:'P', items:['{nm_id}']}}], started: Date.now(), cur:0, responses:{{}}, flags:{{}}, times:{{}}, checked:{{}}, results:{{}}}}))")
            page.wait_for_timeout(300)
            val = str(page.evaluate(f"T27.D.byId.get('{nm_id}').answer.value"))
            page.click("input.numbox")
            for ch in val:
                page.click(f".numpad button:text-is('{ch}')")
            page.click("text=✓ تحقق")
            page.wait_for_timeout(250)
            check("لوحة الأرقام تُدخل الإجابة وتُصحَّح", page.locator(".feedback.ok").count() == 1)

        print("▶ محاكاة TIMSS كاملة (مؤقت، مراجعة، تسليم)")
        page.evaluate("T27.hub()")
        page.click("text=محاكاة TIMSS")
        page.wait_for_timeout(300)
        check("المؤقت يبدأ من 45:00", page.locator(".timer").inner_text().strip() in ("45:00", "44:59"), page.locator(".timer").inner_text())
        total = page.locator(".qstrip button").count()
        check("شريط التنقل يعرض كل الأسئلة", total > 0, str(total))
        page.click(".qstrip button >> nth=-1")
        page.wait_for_timeout(200)
        page.click("text=مراجعة وتسليم")
        page.wait_for_timeout(200)
        page.click("text=تسليم نهائي")
        page.click(".modal .btn.maroon")
        page.wait_for_timeout(400)
        check("النتيجة ونطاق الجاهزية بعد التسليم", page.locator(".bandbox").count() == 1)

        print("▶ التصدير والاستيراد في وضع المعلم")
        with page.expect_download() as dl:
            page.click("text=⬇ تصدير نتائجي (لإرسالها للمعلم)")
        path = dl.value.path()
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        check("ملف النتائج صالح ويحوي الجلسات", data.get("app") == "TIMSS27-G8M" and len(data.get("sessions", [])) >= 2, str(len(data.get("sessions", []))))
        page.evaluate("T27.S.teacher = true; T27.teacher('class')")
        page.wait_for_timeout(200)
        page.set_input_files("input[type=file]", path)
        page.wait_for_timeout(600)
        check("لوحة الصف تعرض الطالب المستورد", page.locator("text=طالب تجريبي").count() > 0)

        if args.codes and CODES.exists():
            print("▶ فك تشفير الاختبارات التجريبية")
            codes = yaml.safe_load(CODES.read_text(encoding="utf-8")) or {}
            for fid, code in codes.items():
                ok = page.evaluate(f"""async () => {{ const f = T27.D.secure.find(x => x.id === '{fid}'); if (!f) return 'missing';
                    try {{ const form = await T27.D.decryptForm(f, '{code}'); return form.blocks.length; }} catch (e) {{ return 'fail'; }} }}""")
                bad = page.evaluate(f"""async () => {{ const f = T27.D.secure.find(x => x.id === '{fid}'); if (!f) return 'missing';
                    try {{ await T27.D.decryptForm(f, 'WRONG1'); return 'opened'; }} catch (e) {{ return 'rejected'; }} }}""")
                check(f"{fid}: الرمز الصحيح يفتح النموذج والخاطئ يُرفض", ok == 2 and bad == "rejected", f"{ok}/{bad}")

        if args.screens:
            print("▶ لقطات الشاشة لكل بند")
            SCREENS.mkdir(parents=True, exist_ok=True)
            for f in SCREENS.glob("*.png"):
                f.unlink()
            ids = page.evaluate("T27.D.items.concat(...T27.D.psi.map(t => t.items)).map(i => i.id)")
            page.evaluate("""() => { document.getElementById('app').innerHTML = '<main class="wrap" id="shots" style="max-width:980px"></main>'; }""")
            for iid in ids:
                page.evaluate(f"""() => {{ const it = T27.D.byId.get('{iid}'); const h = document.getElementById('shots'); h.innerHTML = '';
                    const c = T27.I.render(it, h, {{mode:'review', meta:true, showId:true}}); }}""")
                page.wait_for_timeout(60)
                page.locator("#shots .item-frame").screenshot(path=str(SCREENS / f"{iid}.png"))
            check(f"لقطات {len(ids)} بنداً محفوظة", True)

        check("لا أخطاء JavaScript طوال الاختبار", not errors, "; ".join(errors[:3]))
        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nالنتيجة: {len(results) - len(failed)} ناجح / {len(failed)} فاشل")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
