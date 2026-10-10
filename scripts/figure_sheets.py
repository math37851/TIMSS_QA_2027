# -*- coding: utf-8 -*-
"""
figure_sheets.py — أوراق مجمّعة منخفضة الدقة لرسوم البنود، للمراجعة البصرية بأقل توكنز.
كل خلية: المعرّف · الموضوع · المفتاح/الإجابة + مقتطف من المتن + الرسم (والبدائل المرسومة إن وُجدت).
بنود الرسم على الشبكة تُعرض بمعطياتها ونقاط مفتاحها (K) للتحقق من اتساق المفتاح.

  python figure_sheets.py --topics G1 G2          # موضوعات من بنك التدريب
  python figure_sheets.py --psi --secure          # مهام PSI والاختبارات المحمية
  python figure_sheets.py --ids M8-G2-013 M8-D1-004
خيارات: --per 12 (خلايا لكل ورقة) · --out مجلد الإخراج (افتراضياً مجلد مؤقت خارج المشروع،
حتى لا تُحفظ صور البنود المحمية داخل مجلد قد يوزَّع).
"""
import argparse
import html
import pathlib
import re
import sys
import tempfile

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import figures  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
BANK = ROOT / "02_بنك_الأسئلة"
LET = "ABCD"

CSS = """
body{font-family:'Segoe UI',Tahoma,sans-serif;margin:8px;background:#fff;color:#222}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.cell{border:1px solid #bbb;border-radius:6px;padding:6px;min-width:0}
.hd{font:bold 13px Consolas,monospace;direction:ltr;text-align:left;color:#8A1538}
.st{font-size:11px;line-height:1.35;max-height:44px;overflow:hidden;margin:2px 0}
.fg svg{max-width:100%;height:auto;max-height:230px;display:block;margin:4px auto}
.fig-row{display:flex;gap:4px;justify-content:center;flex-wrap:wrap}
.fig-row svg{max-width:48%}
.op{display:grid;grid-template-columns:repeat(2,1fr);gap:4px}
.op div{font:bold 11px Consolas,monospace;direction:ltr}
.op svg{max-width:100%;height:auto;max-height:110px;display:block}
"""


def sq(s, n):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[:n] + "…"


def answer_of(it):
    f = it.get("format")
    if f in ("mc", "select_explain"):
        return f"key {it.get('key')}"
    if f == "numeric":
        a = it.get("answer") or {}
        return f"= {a.get('value')} {a.get('unit', '')}".strip()
    if f == "multi_numeric":
        return "= " + ", ".join(str(x.get("value")) for x in it.get("fields", []))
    if f == "grid_plot":
        return f"grid {it.get('mode')}"
    return str(f)


def grid_spec(it):
    """يحوّل بند grid_plot إلى رسم coord يجمع المعطيات ونقاط المفتاح."""
    g = dict(it.get("grid") or {})
    given = it.get("given") or {}
    spec = {"type": "coord", **{k: g[k] for k in ("xmin", "xmax", "ymin", "ymax") if k in g}}
    if given.get("polygons"):
        spec["polygons"] = given["polygons"]
    if given.get("segments"):
        spec["segments"] = given["segments"]
    pts = list(given.get("points") or [])
    pts += [{"x": p[0], "y": p[1], "label": "K"} for p in it.get("key") or []]
    if pts:
        spec["points"] = pts
    return spec


def collect(a):
    rows = []
    sources = []
    if a.topics or a.ids or not (a.psi or a.secure):
        for p in sorted((BANK / "items").glob("*.yaml")):
            sources += [(it, "practice") for it in (yaml.safe_load(p.read_text(encoding="utf-8")) or [])]
    if a.psi or a.ids:
        for p in sorted((BANK / "psi").glob("*.yaml")):
            d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            if d.get("figure"):
                sources.append(({"id": d.get("id"), "topic": "PSI", "format": "-", "stem": d.get("intro"), "figure": d["figure"]}, "psi"))
            sources += [(it, "psi") for it in d.get("items", [])]
    if a.secure:
        for p in sorted((BANK / "secure").glob("mock_*.yaml")):
            d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            sources += [(it, "mock") for b in d.get("blocks", []) for it in b.get("items", [])]
    for it, src in sources:
        if a.ids and it.get("id") not in a.ids:
            continue
        if a.topics and src == "practice" and it.get("topic") not in a.topics:
            continue
        figs = it.get("figure")
        if it.get("format") == "grid_plot":
            figs = [figs, grid_spec(it)] if figs else grid_spec(it)
        opts = [o.get("figure") for o in (it.get("options") or []) if isinstance(o, dict) and o.get("figure")]
        if figs or opts:
            rows.append((it, figs, opts))
    return rows


def cell(it, figs, opts):
    try:
        fg = figures.render(figs) if figs else ""
        op = "".join(f"<div>{LET[i]}{figures.render(f)}</div>" for i, f in enumerate(opts))
    except Exception as e:  # noqa: BLE001
        fg, op = f"<b style='color:red'>RENDER ERROR: {html.escape(str(e))}</b>", ""
    hd = f"{it.get('id')} · {it.get('topic')} · {answer_of(it)}"
    return (f"<div class='cell'><div class='hd'>{html.escape(hd)}</div>"
            f"<div class='st' dir='rtl'>{html.escape(sq(it.get('stem'), 170))}</div>"
            f"<div class='fg'>{fg}</div>" + (f"<div class='op'>{op}</div>" if op else "") + "</div>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topics", nargs="*")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--psi", action="store_true")
    ap.add_argument("--secure", action="store_true")
    ap.add_argument("--per", type=int, default=12)
    ap.add_argument("--out")
    a = ap.parse_args()
    out = pathlib.Path(a.out) if a.out else pathlib.Path(tempfile.gettempdir()) / "timss_figure_sheets"
    out.mkdir(parents=True, exist_ok=True)
    rows = collect(a)
    pages = [rows[i:i + a.per] for i in range(0, len(rows), a.per)]
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1400, "height": 900}, device_scale_factor=1)
        for k, chunk in enumerate(pages, 1):
            doc = (f"<!doctype html><html lang='ar'><head><meta charset='utf-8'><style>{CSS}</style></head>"
                   f"<body><div class='grid'>{''.join(cell(*r) for r in chunk)}</div></body></html>")
            hp = out / f"sheet_{k:02d}.html"
            hp.write_text(doc, encoding="utf-8")
            page.goto(hp.as_uri())
            page.screenshot(path=str(out / f"sheet_{k:02d}.png"), full_page=True)
            print(out / f"sheet_{k:02d}.png", "|", " ".join(r[0].get("id", "?") for r in chunk))
        browser.close()
    print(f"أوراق: {len(pages)} | بنود: {len(rows)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
