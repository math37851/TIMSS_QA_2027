# -*- coding: utf-8 -*-
"""
gemini_review.py — مراجعة مسبقة مستقلة بنموذج من عائلة أخرى (Gemini عبر Antigravity CLI «agy»).

لكل بند، ودون إرسال المفتاح أو الحل أو التحقق: حلّ أعمى، وتصنيف الموضوع والمستوى المعرفي،
وملاحظات رياضية ولغوية وثقافية. النتائج دليل للمراجعين البشر، لا قرار اعتماد.

  python gemini_review.py                    # كل البنود (دفعات 12، ثلاث متوازية)
  python gemini_review.py --ids M8-A4-016    # بنود محددة
  python gemini_review.py --resume           # يتخطى الدفعات المحفوظة سابقاً
المخرجات: 05_الاعتماد/02_التدقيق_العلمي_الرياضي/فحص_Gemini/ (raw/ + results.json)
"""
import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
BANK = ROOT / "02_بنك_الأسئلة"
OUT = ROOT / "05_الاعتماد" / "02_التدقيق_العلمي_الرياضي" / "فحص_Gemini"
AGY = pathlib.Path(os.environ.get("USERPROFILE", "")) / ".gemini" / "bin" / "agy.exe"
MODEL = "gemini-3.1-pro-high"
LET = "ABCD"

INSTRUCTIONS = """You are an independent reviewer of a Grade 8 mathematics item bank for TIMSS 2027 preparation in Qatar.
Items are written in Arabic; mathematics is in LaTeX between $...$. Figures are given as JSON specifications
(chart data, coordinates, labels): read the data from them. Do not use any tools or files; answer from the text only.

For EACH item, WITHOUT any answer key:
1. Solve it yourself. Give your final answer in this form:
   - mc or select_explain: the option letter (A, B, C or D).
   - numeric: a number. multi_numeric: an array of numbers in the order of the fields.
   - dragdrop_order: an array of card ids in the order the stem asks for.
   - dragdrop_categorize: an object {card_id: category text exactly as written}.
   - dragdrop_slots: an object {slot number: card id}.
   - grid_plot: an array of [x, y] points.
   - cr_explain: one short sentence with the final answer or conclusion.
2. Classify the item: topic (one code from TOPICS) and cognitive domain (knowing, applying or reasoning).
3. Report REAL problems only, as short Arabic notes, and use empty arrays when there are none:
   - issues: a mathematical error, an ambiguity, more than one defensible answer, missing information, or data that does not match the figure.
   - language_issues: Arabic language errors or unclear wording.
   - sensitivity_issues: cultural, religious, gender or bias concerns for students in Qatar.

Return ONLY a JSON object of the form {"results": [ ... ]} with one entry per item:
{"id": "...", "answer": ..., "confidence": 0.0-1.0, "unambiguous": true/false, "topic": "...", "cognitive": "...",
 "issues": [...], "language_issues": [...], "sensitivity_issues": [...]}
"""

SCHEMA = {
    "type": "object",
    "properties": {"results": {"type": "array", "items": {"type": "object", "properties": {
        "id": {"type": "string"}, "answer": {}, "confidence": {"type": "number"}, "unambiguous": {"type": "boolean"},
        "topic": {"type": "string"}, "cognitive": {"type": "string"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "language_issues": {"type": "array", "items": {"type": "string"}},
        "sensitivity_issues": {"type": "array", "items": {"type": "string"}}},
        "required": ["id", "answer", "topic", "cognitive", "issues"]}}},
    "required": ["results"],
}


def card_list(cards):
    """البطاقات مع معرّف ثابت: معرّف البطاقة إن وُجد، وإلا c1، c2، …"""
    out = []
    for k, c in enumerate(cards or [], 1):
        if isinstance(c, dict):
            out.append((str(c.get("id", f"c{k}")), str(c.get("text", ""))))
        else:
            out.append((f"c{k}", str(c)))
    return out


def compact(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def blind(it, psi_ctx=None):
    """نص البند كما يراه الطالب، بلا مفتاح ولا حل ولا تحقق."""
    f = it["format"]
    L = [f"### {it['id']} | format: {f}"]
    if psi_ctx:
        L.append("SHARED CONTEXT (PSI task): " + re.sub(r"\s+", " ", psi_ctx.get("intro", "")).strip())
        if psi_ctx.get("table"):
            L.append("SHARED TABLE: " + compact(psi_ctx["table"]))
        if psi_ctx.get("figure"):
            L.append("SHARED FIGURE: " + compact(psi_ctx["figure"]))
    L.append("STEM: " + re.sub(r"\s+", " ", it.get("stem", "")).strip())
    if it.get("table"):
        L.append("TABLE: " + compact(it["table"]))
    if it.get("figure"):
        L.append("FIGURE: " + compact(it["figure"]))
    if f in ("mc", "select_explain"):
        opts = []
        for i, o in enumerate(it.get("options") or []):
            opts.append(f"{LET[i]}) " + (compact(o.get("figure")) if isinstance(o, dict) else str(o)))
        L.append("OPTIONS: " + " | ".join(opts))
    if f == "numeric" and (it.get("answer") or {}).get("unit"):
        L.append("ANSWER UNIT: " + str(it["answer"]["unit"]))
    if f == "multi_numeric":
        L.append("FIELDS (in order): " + " | ".join(str(x.get("label", "")) for x in it.get("fields", [])))
    if f.startswith("dragdrop"):
        L.append("CARDS: " + " | ".join(f"{cid}: {txt}" for cid, txt in card_list(it.get("cards"))))
        if f == "dragdrop_slots":
            L.append("TEMPLATE (slots are [[n]]): " + str(it.get("template", "")))
        if f == "dragdrop_categorize":
            L.append("CATEGORIES: " + " | ".join(str(c) for c in it.get("categories", [])))
        if f == "dragdrop_order" and it.get("order_labels"):
            L.append("ORDER LABELS: " + " → ".join(it["order_labels"]))
    if f == "grid_plot":
        g = it.get("grid") or {}
        L.append(f"GRID: x {g.get('xmin')}..{g.get('xmax')}, y {g.get('ymin')}..{g.get('ymax')} | mode: {it.get('mode')} | points to plot: {it.get('count', len(it.get('key') or []))}")
        if it.get("given"):
            L.append("GIVEN ON GRID: " + compact(it["given"]))
    return "\n".join(L)


def load_all():
    items = []
    for p in sorted((BANK / "items").glob("*.yaml")):
        items += [(it, None) for it in (yaml.safe_load(p.read_text(encoding="utf-8")) or [])]
    for p in sorted((BANK / "psi").glob("*.yaml")):
        t = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        items += [(it, t) for it in t.get("items", [])]
    for p in sorted((BANK / "secure").glob("mock_*.yaml")):
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        items += [(it, None) for b in d.get("blocks", []) for it in b.get("items", [])]
    return items


def topics_text():
    bp = yaml.safe_load((BANK / "blueprint.yaml").read_text(encoding="utf-8"))
    return "\n".join(f"{k}: {v.get('ar', '')}" for k, v in bp["topics"].items())


def parse_response(stdout):
    """agy --output-format json ← {"response": "...json..."}؛ قد يكون الرد داخل سياج ```json."""
    env = json.loads(stdout)
    txt = env.get("response", "")
    m = re.search(r"```(?:json)?\s*(.*?)```", txt, re.S)
    body = m.group(1) if m else txt
    s, e = body.find("{"), body.rfind("}")
    data = json.loads(body[s:e + 1])
    return data.get("results", data if isinstance(data, list) else []), env.get("usage", {})


def run_batch(k, batch, topics, schema_path, workdir):
    raw = OUT / "raw" / f"batch_{k:03d}.json"
    prompt = INSTRUCTIONS + "\nTOPICS:\n" + topics + "\n\nITEMS:\n\n" + "\n\n".join(blind(it, ctx) for it, ctx in batch)
    last = ""
    for attempt in range(2):
        try:
            r = subprocess.run([str(AGY), "-p", prompt, "--model", MODEL, "--output-format", "json", "--print-timeout", "900s",
                                "--json-schema", str(schema_path)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1000, cwd=workdir)
            results, usage = parse_response(r.stdout)
            got = {x.get("id") for x in results}
            want = [it["id"] for it, _ in batch]
            missing = [i for i in want if i not in got]
            raw.write_text(json.dumps({"batch": k, "ids": want, "missing": missing, "usage": usage, "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
            return k, len(results), missing, usage.get("total_tokens", 0)
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            time.sleep(5)
    raw.with_suffix(".error.txt").write_text(last, encoding="utf-8")
    return k, 0, [it["id"] for it, _ in batch], 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--batch", type=int, default=12)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    items = load_all()
    if a.ids:
        items = [x for x in items if x[0]["id"] in a.ids]
    batches = [items[i:i + a.batch] for i in range(0, len(items), a.batch)]
    schema_path = OUT / "schema.json"
    schema_path.write_text(json.dumps(SCHEMA, ensure_ascii=False), encoding="utf-8")
    workdir = tempfile.mkdtemp(prefix="agy_ws_")          # مجلد فارغ: لا يصل الوكيل إلى ملفات المشروع
    topics = topics_text()
    todo = [(k, b) for k, b in enumerate(batches, 1) if not (a.resume and (OUT / "raw" / f"batch_{k:03d}.json").exists())]
    print(f"بنود: {len(items)} | دفعات: {len(batches)} | للتنفيذ: {len(todo)} | النموذج: {MODEL}", flush=True)
    t0 = time.time()
    tokens = 0
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(run_batch, k, b, topics, schema_path, workdir) for k, b in todo]
        for fu in cf.as_completed(futs):
            k, n, missing, tok = fu.result()
            tokens += tok
            print(f"دفعة {k:03d}: {n} نتيجة | ناقص: {len(missing)} | {int(time.time() - t0)}s", flush=True)
    # دمج كل الدفعات
    merged = {}
    for p in sorted((OUT / "raw").glob("batch_*.json")):
        for x in json.loads(p.read_text(encoding="utf-8")).get("results", []):
            if x.get("id"):
                merged[x["id"]] = x
    (OUT / "results.json").write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"اكتمل: {len(merged)} بنداً لها نتيجة من {len(items)} | توكنز هذه الجولة ≈ {tokens:,} | {int(time.time() - t0)}s", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
