# -*- coding: utf-8 -*-
"""
gemini_anchors.py — نماذج إجابات للتدريب على التصحيح (Anchor papers) للأسئلة المفتوحة و«اختر وبرّر».

1) توليد: لكل بند ثلاث إجابات طلاب واقعية (كاملة، جزئية، خطأ شائع) مع الكود المقصود.
2) تصحيح أعمى: استدعاء منفصل يصحح الإجابات بدليل التصحيح دون معرفة المستوى المقصود.
اختلاف المقصود عن الأعمى = غموض محتمل في دليل التصحيح (للمهمة 02-08).

المخرجات: 02_بنك_الأسئلة/anchors.json (يدمجه build_bank في المنصة)
          05_الاعتماد/11_الأدلة_وتدريب_المعلمين/نماذج_الإجابات/ (raw + ملخص)
"""
import argparse
import concurrent.futures as cf
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gemini_review import AGY, MODEL, LET, load_all, parse_response  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
BANK = ROOT / "02_بنك_الأسئلة"
OUT = ROOT / "05_الاعتماد" / "11_الأدلة_وتدريب_المعلمين" / "نماذج_الإجابات"
LEVEL_AR = {"full": "إجابة كاملة", "partial": "إجابة جزئية", "incorrect": "إجابة خاطئة"}
TERMS = {"المقطع الصادي": "المقطع $y$", "المقطع السيني": "المقطع $x$", "الخصم": "الحسم"}


def tidy(s):
    """مصطلحات القاموس، والمتغير اللاتيني المفرد خارج $…$ يدخل الترميز الرياضي (المحور y ← المحور $y$)."""
    for a, b in TERMS.items():
        s = s.replace(a, b)
    parts = re.split(r"(\$[^$]*\$)", s)
    return "".join(p if p.startswith("$") else re.sub(r"(?<![A-Za-z\\])([a-z])(?![A-Za-z])", r"$\1$", p) for p in parts)


# مراجعة ثالثة للحالات التي اختلف فيها الكود المقصود والتصحيح الأعمى أو أشار المصحح إلى غموض الدليل،
# بعد توضيح الدليل نفسه في البنك. تُطبَّق في كل تجميع (المسودات الخام في raw تبقى كما ولّدها النموذج).
REVIEW = {
    ("M8-D1-021", "partial"): dict(code="10", note="حالة حدّية: اختياران صحيحان (الخطوط والانتشار) وتعليل صحيح لأحدهما، فتنال درجة جزئية؛ وأوضح الدليل هذه الحالة."),
    ("M8-N2-013", "partial"): dict(code="0", note="حالة حدّية: السؤال يطلب مثالاً، وعبارة «سالب وسالب يصير موجب» قاعدة عامة غير دقيقة، فلا تنال الدرجة؛ وأضيفت الحالة إلى الدليل."),
    ("M8-PSI3-05", "partial"): dict(level="full", code="1",
        reason="اختار «لا» وبرّر بأن الزيادة في العدد متساوية لكن أعداد البداية مختلفة، وهذا أحد التبريرين اللذين يقبلهما الدليل.",
        note="كان الكود المقصود عند التوليد 0، وصحّحته المراجعة إلى 1 لأن الدليل يقبل مقارنة الأساسين نصاً دون حساب."),
    ("M8-X1-32", "partial"): dict(level="incorrect", code="70",
        reason="تفسيره في الجزء (1) عبارة عامة لا تذكر الوتر ولا المربعات، وفي الجزء (2) جمع المربعين بدل طرحهما.",
        note="كان الكود المقصود عند التوليد 10، وصحّحته المراجعة إلى 70؛ وأوضح الدليل أن العبارة العامة لا تُعد تفسيراً."),
    ("M8-X3-13", "partial"): dict(level="full", code="1",
        reason="اختار «لا» وبرّر بأن أحد المقدارين خطي والآخر تربيعي، وهذا تبرير يقبله الدليل.",
        note="كان الكود المقصود عند التوليد 0، وصحّحته المراجعة إلى 1 لأن الدليل يقبل هذا التبرير نصاً."),
    ("M8-N1-004", "partial"): dict(note="صفر: عبارة عامة لا تحسب الطرفين ولا تذكر القاعدة؛ وأضيفت الحالة إلى الدليل."),
    ("M8-N5-013", "partial"): dict(note="صفر: ذكر الطول الصحيح وحده دون بيان التضاعف أو النسبة لا يكفي؛ وأضيفت الحالة إلى الدليل."),
    ("M8-N6-013", "partial"): dict(note="صفر: بيان أن عدد الطلاب مختلف لا يحدد أي النسبتين أكبر، والمطلوب الحكم على العبارة؛ وأضيفت الحالة إلى الدليل."),
}

GEN = """You are an experienced Grade 8 mathematics teacher in Qatar preparing scoring anchors ("anchor papers")
for TIMSS-style open-response items, to train teachers to score consistently. Items are in Arabic; math is in LaTeX.
Do not use any tools or files.

For EACH item write exactly 3 realistic student responses in Arabic, as a real 13-14 year old student in Qatar would
write them: short, natural, sometimes imperfect wording. One response for each level:
- "full": a correct answer with a valid, complete justification.
- "partial": the right direction but an incomplete or partly flawed justification. For a 1-point select_explain item,
  write the correct choice with a missing or invalid justification (it earns 0).
- "incorrect": built on a typical misconception (use the item's listed misconceptions when relevant).
Give the code each response deserves under the item's rubric (cr_explain: one rubric code such as 20, 10, 70, 79;
select_explain: 1 or 0) and one short Arabic sentence explaining why.
Rules: math inside $...$ when needed; digits 0-9 only; fractions as \\frac{a}{b}; units inside math, e.g. $12\\,\\text{cm}$.

Return ONLY a JSON object: {"results": [{"id": "...", "responses": [
  {"level": "full|partial|incorrect", "text": "...", "intended_code": "...", "reason": "..."}]}]}
"""

SCORE = """You are a trained TIMSS scorer. For each item below, read the stem and the scoring guide, then score each
numbered student response strictly by the guide. You do NOT know which response was meant to be correct.
Do not use any tools or files. If the guide does not clearly decide a response, say so in rubric_issue (Arabic).
Return ONLY a JSON object: {"results": [{"id": "...", "scores": [
  {"n": 1, "code": "...", "reason": "...", "rubric_issue": ""}]}]}
(cr_explain: use the rubric codes; select_explain: code 1 for full credit, 0 otherwise.)
"""


def rubric_text(it):
    rb = it.get("rubric") or {}
    if rb.get("codes"):
        s = " | ".join(f"code {c['code']} ({c['points']} pt): {c['desc']}" for c in rb["codes"])
    else:
        s = f"full credit (1 pt): {rb.get('full', '')} | zero: {rb.get('zero', '')}"
    if it.get("model_answer"):
        s += f" | model answer: {it['model_answer']}"
    return re.sub(r"\s+", " ", s)


def item_block(it, ctx, with_key=True):
    L = [f"### {it['id']} | format: {it['format']} | points: {it.get('points', 1)}"]
    if ctx:
        L.append("SHARED CONTEXT: " + re.sub(r"\s+", " ", ctx.get("intro", "")))
    L.append("STEM: " + re.sub(r"\s+", " ", it.get("stem", "")))
    if it.get("table"):
        L.append("TABLE: " + json.dumps(it["table"], ensure_ascii=False))
    if it.get("options"):
        L.append("OPTIONS: " + " | ".join(f"{LET[i]}) {o}" for i, o in enumerate(it["options"]) if isinstance(o, str)))
        if with_key:
            L.append("CORRECT CHOICE: " + str(it.get("key")))
    L.append("SCORING GUIDE: " + rubric_text(it))
    if with_key and it.get("misconceptions"):
        L.append("KNOWN MISCONCEPTIONS: " + ", ".join(it["misconceptions"]))
    return "\n".join(L)


def call(prompt, workdir):
    r = subprocess.run([str(AGY), "-p", prompt, "--model", MODEL, "--output-format", "json", "--print-timeout", "900s"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1000, cwd=workdir)
    return parse_response(r.stdout)


def run(kind, k, batch, workdir, extra=None):
    raw = OUT / "raw" / f"{kind}_{k:03d}.json"
    if raw.exists():
        return json.loads(raw.read_text(encoding="utf-8"))["results"]
    if kind == "gen":
        prompt = GEN + "\nITEMS:\n\n" + "\n\n".join(item_block(it, ctx) for it, ctx in batch)
    else:
        blocks = []
        for it, ctx in batch:
            resp = extra.get(it["id"], [])
            blocks.append(item_block(it, ctx, with_key=False) + "\nRESPONSES:\n" +
                          "\n".join(f"{n}. {x.get('text', '')}" for n, x in enumerate(resp, 1)))
        prompt = SCORE + "\nITEMS:\n\n" + "\n\n".join(blocks)
    for _ in range(2):
        try:
            results, usage = call(prompt, workdir)
            raw.write_text(json.dumps({"results": results, "usage": usage}, ensure_ascii=False, indent=1), encoding="utf-8")
            return results
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
            time.sleep(5)
    raw.with_suffix(".error.txt").write_text(err, encoding="utf-8")
    return []


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=6)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    items = [(it, ctx) for it, ctx in load_all() if it["format"] in ("select_explain", "cr_explain")]
    batches = [items[i:i + a.batch] for i in range(0, len(items), a.batch)]
    workdir = tempfile.mkdtemp(prefix="agy_ws_")
    print(f"بنود مفتوحة: {len(items)} | دفعات: {len(batches)}", flush=True)
    gen = {}
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for res in ex.map(lambda kb: run("gen", kb[0], kb[1], workdir), enumerate(batches, 1)):
            for x in res:
                gen[x.get("id")] = x.get("responses", [])
    print(f"توليد: {len(gen)} بنداً", flush=True)
    scores = {}
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for res in ex.map(lambda kb: run("score", kb[0], kb[1], workdir, gen), enumerate(batches, 1)):
            for x in res:
                scores[x.get("id")] = x.get("scores", [])
    print(f"تصحيح أعمى: {len(scores)} بنداً", flush=True)
    anchors, agree, total, issues = {}, 0, 0, []
    norm = lambda c: re.sub(r"\D", "", str(c)) or str(c).strip()
    for it, _ in items:
        resp = gen.get(it["id"], [])
        sc = {int(s.get("n", 0)): s for s in scores.get(it["id"], []) if str(s.get("n", "")).isdigit()}
        out = []
        for n, r in enumerate(resp, 1):
            s = sc.get(n, {})
            ok = norm(r.get("intended_code")) == norm(s.get("code")) if s else None
            total += ok is not None
            agree += bool(ok)
            e = {"level": r.get("level"), "text": tidy(r.get("text", "")), "code": str(r.get("intended_code", "")),
                 "reason": tidy(r.get("reason", "")), "blind_code": str(s.get("code", "")), "agree": ok,
                 "rubric_issue": s.get("rubric_issue", "")}
            rv = REVIEW.get((it["id"], r.get("level")))
            if rv:
                e.update(rv, adjudicated=True)
            out.append(e)
            if ok is False or s.get("rubric_issue"):
                issues.append((it["id"], LEVEL_AR.get(r.get("level"), r.get("level")), r.get("intended_code"), s.get("code"),
                               s.get("rubric_issue", ""), e["code"] + (" · " + e["note"] if rv and rv.get("note") else "")))
        if out:
            anchors[it["id"]] = out
    (BANK / "anchors.json").write_text(json.dumps(anchors, ensure_ascii=False, indent=1), encoding="utf-8")
    md = ["# نماذج إجابات الأسئلة المفتوحة: ملخص التحقق\n",
          f"- بنود مفتوحة: {len(items)} · لها نماذج: {len(anchors)} · إجابات: {total}",
          f"- اتفاق الكود المقصود مع التصحيح الأعمى: {agree} من {total} ({agree / max(1, total):.0%})",
          "- النماذج مولّدة آلياً بنموذج Gemini 3.1 Pro، وتظهر في المنصة تحت دليل التصحيح للتدريب على التصحيح، وتحتاج مراجعة المعلمين (المهمة 02-08).\n",
          f"- حُسمت الحالات المختلفة بمراجعة ثالثة (Claude) وفق الدليل بعد توضيحه في {len({i for i, *_ in issues})} بنود؛ القرار المعتمد في عمود «القرار» ويظهر في المنصة مع سببه.\n",
          "## إجابات اختلف تصحيحها أو أشار المصحح إلى غموض في الدليل\n", "| البند | المستوى المولَّد | المقصود | الأعمى | ملاحظة المصحح | القرار |", "|---|---|---|---|---|---|"]
    md += [f"| {i} | {lv} | {a1} | {a2} | {str(ri)[:140]} | {dec} |" for i, lv, a1, a2, ri, dec in issues]
    (OUT / "ملخص_نماذج_الإجابات.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"اكتمل: {len(anchors)} بنداً | اتفاق {agree}/{total} | للمراجعة {len(issues)}", flush=True)


if __name__ == "__main__":
    main()
