# -*- coding: utf-8 -*-
"""
build_obsidian_vault.py — يولّد «غراف المعرفة» لمشروع TIMSS 2027 كمجلد Obsidian (بلا أي استهلاك توكنز).

العُقد: المجالات · الموضوعات العشرون · البنود · المفاهيم الخاطئة · المستويات المعرفية والمجالات الفرعية
        · أنواع البنود · المستويات الدولية · الوثائق · (اختياري) غراف الشيفرة من graphify
الروابط: [[روابط ويكي]] تُظهرها طريقة عرض الغراف (Graph View) في Obsidian.

المصدر: 02_بنك_الأسئلة/build/bank.json (شغّل build_bank.py أولاً). الاختبارات المحمية لا تُضمَّن.
الاستعمال:  python build_obsidian_vault.py
ثم في Obsidian: Open folder as vault ← D:\\TIMSS 2027\\04_غراف_المعرفة_Obsidian
"""

import json
import pathlib
import re
import shutil
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
BANK = ROOT / "02_بنك_الأسئلة"
DOCS = ROOT / "01_المصادر_والإطار"
VAULT = ROOT / "04_غراف_المعرفة_Obsidian"
GEN = ["مجالات", "موضوعات", "بنود", "مفاهيم_خاطئة", "مستويات_معرفية", "أنواع_البنود", "مستويات_دولية", "وثائق"]
DOMAIN_TAG = {"number": "number", "algebra": "algebra", "geometry_measurement": "geometry", "data_probability": "data"}
LET = "ABCD"


def safe(name):
    return re.sub(r'[<>:"/\\|?*#^\[\]]', "-", str(name)).strip()


def write(path, front, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = ""
    if front:
        lines = []
        for k, v in front.items():
            if isinstance(v, list):
                lines.append(f"{k}: [{', '.join(json.dumps(x, ensure_ascii=False) for x in v)}]")
            else:
                lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
        fm = "---\n" + "\n".join(lines) + "\n---\n"
    path.write_text(fm + body.rstrip() + "\n", encoding="utf-8")


def md_table(t):
    if not t:
        return ""
    rows = []
    if t.get("headers"):
        rows.append("| " + " | ".join(t["headers"]) + " |")
        rows.append("|" + "---|" * len(t["headers"]))
    for r in t.get("rows", []):
        rows.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(rows) + "\n"


def main():
    bank = json.loads((BANK / "build" / "bank.json").read_text(encoding="utf-8"))
    topics, domains, cogs = bank["topics"], bank["domains"], bank["cognitive_domains"]
    bms, diffs, fmts = bank["benchmarks"], bank["difficulty_levels"], bank["formats"]
    items = list(bank["items"]) + [i for t in bank.get("psi", []) for i in t["items"]]

    # تنظيف المجلدات المولَّدة فقط (لا تُمس ملاحظاتك الخاصة أو إعدادات .obsidian)
    for g in GEN:
        shutil.rmtree(VAULT / g, ignore_errors=True)
    VAULT.mkdir(parents=True, exist_ok=True)

    dname = {d: v["ar"] for d, v in domains.items()}
    cname = {c: v["ar"] for c, v in cogs.items()}
    aname = {a: lab for c in cogs.values() for a, lab in c["areas"].items()}
    bname = {b: v["ar"] for b, v in bms.items()}
    fname = {f: v["ar"] for f, v in fmts.items()}
    tlink = lambda t: f"[[{t}]]"

    by_topic = defaultdict(list)
    by_mis = defaultdict(list)
    by_area = defaultdict(list)
    by_fmt = defaultdict(list)
    by_bm = defaultdict(list)

    # ---- البنود
    figdir = VAULT / "بنود" / "رسوم"
    for it in items:
        iid = it["id"]
        by_topic[it["topic"]].append(it)
        by_area[it["area"]].append(iid)
        by_fmt[it["format"]].append(iid)
        by_bm[it["benchmark"]].append(iid)
        for m in it.get("misconceptions") or []:
            by_mis[m].append(it)
        body = [f"# {iid}", ""]
        body.append(f"**الموضوع:** {tlink(it['topic'])} · **المجال:** [[{dname[it['domain']]}]] · "
                    f"**المستوى المعرفي:** [[{cname[it['cognitive']]}]] / [[{aname.get(it['area'], it['area'])}]]")
        body.append(f"**الصعوبة:** {diffs[it['difficulty']]['ar']} · **المستوى الدولي:** [[{bname[it['benchmark']]}]] · "
                    f"**النوع:** [[{fname[it['format']]}]] · **السياق:** {bank['contexts'][it['context']]}"
                    + (f" · **PSI:** {it['psi']}" if it.get("psi") else ""))
        body += ["", "## السؤال", "", it["stem"].strip(), ""]
        if it.get("table"):
            body += [md_table(it["table"]), ""]
        svg = it.get("figure_svg") or it.get("print_svg")
        if svg:
            figdir.mkdir(parents=True, exist_ok=True)
            (figdir / f"{iid}.svg").write_text(svg, encoding="utf-8")
            body += [f"![[{iid}.svg]]", ""]
        if it.get("options"):
            for i, o in enumerate(it["options"]):
                mark = " ✅" if LET[i] == it.get("key") else ""
                body.append(f"- **{LET[i]}**{mark}: {o or '(شكل)'}")
            body.append("")
        if it.get("cards"):
            body.append("**البطاقات:** " + " · ".join(c["text"] for c in it["cards"]))
            body.append("")
        body.append("## الإجابة")
        f = it["format"]
        if f in ("mc", "select_explain"):
            body.append(f"البديل **{it['key']}**")
        elif f == "numeric":
            body.append(f"$ {it['answer']['value']} $ {it['answer'].get('unit', '')}")
        elif f == "multi_numeric":
            body.append("، ".join(f"{x['label']} $= {x['value']}$" for x in it["fields"]))
        elif f.startswith("dragdrop"):
            byid = {c["id"]: c["text"] for c in it["cards"]}
            k = it["key"]
            if isinstance(k, list):
                body.append(" ← ".join(byid.get(c, c) for c in k))
            else:
                body.append("، ".join(f"{s}: {byid.get(c, c)}" if f == "dragdrop_slots" else f"{byid.get(s, s)} ← {c}" for s, c in k.items()))
        elif f == "grid_plot":
            body.append("، ".join(f"$({p[0]}, {p[1]})$" for p in it["key"]))
        elif f == "cr_explain":
            body.append(it.get("model_answer", ""))
        if it.get("rationale"):
            body += ["", "## تفسير المشتّتات"] + [f"- **{k}:** {v}" for k, v in it["rationale"].items()]
        body += ["", "## الحل", "", it.get("solution", "").strip()]
        if it.get("remediation"):
            body += ["", "## اقتراح علاجي", "", it["remediation"].strip()]
        if it.get("misconceptions"):
            body += ["", "**المفاهيم الخاطئة المستهدفة:** " + "، ".join(f"[[{m}]]" for m in it["misconceptions"])]
        if it.get("qatar_link"):
            body += ["", f"**الارتباط بمنهج قطر:** {it['qatar_link']}"]
        front = {"id": iid, "topic": it["topic"], "cognitive": it["cognitive"], "difficulty": it["difficulty"],
                 "benchmark": it["benchmark"], "format": it["format"], "verified": bool(it.get("verified")),
                 "tags": ["بند", DOMAIN_TAG[it["domain"]], it["topic"]]}
        write(VAULT / "بنود" / it["topic"] / f"{safe(iid)}.md", front, "\n".join(body))

    # ---- الموضوعات
    for tid, tp in topics.items():
        lst = by_topic.get(tid, [])
        body = [f"# {tid} — {tp['ar']}", "", f"**المجال:** [[{dname[tp['domain']]}]] · **مجال الموضوعات:** {tp['area_ar']}",
                f"**بنود البنك:** {len(lst)} من {tp['bank_target']}", "", "> " + tp["en"], ""]
        for c in ("knowing", "applying", "reasoning"):
            sub = [i for i in lst if i["cognitive"] == c]
            if sub:
                body.append(f"## [[{cname[c]}]] ({len(sub)})")
                body += [f"- [[{i['id']}]] — {diffs[i['difficulty']]['ar']} · {fname[i['format']]}" for i in sub]
                body.append("")
        mis = sorted({m for i in lst for m in (i.get("misconceptions") or [])})
        if mis:
            body += ["## المفاهيم الخاطئة في هذا الموضوع", "، ".join(f"[[{m}]]" for m in mis)]
        write(VAULT / "موضوعات" / f"{tid}.md", {"aliases": [tp["ar"]], "tags": ["موضوع", DOMAIN_TAG[tp["domain"]]]}, "\n".join(body))

    # ---- المجالات
    for d, info in domains.items():
        tps = [t for t, v in topics.items() if v["domain"] == d]
        body = [f"# {info['ar']}", "", f"**وزن TIMSS:** {info['timss_pct']}% · **قطر 2023:** {info['qatar_2023']} ({info['qatar_diff']:+d})", "",
                "## الموضوعات"] + [f"- [[{t}]] — {topics[t]['ar']}" for t in tps] + ["", "[[00_الخريطة]]"]
        write(VAULT / "مجالات" / f"{safe(info['ar'])}.md", {"tags": ["مجال", DOMAIN_TAG[d]]}, "\n".join(body))

    # ---- المستويات المعرفية والمجالات الفرعية
    for c, info in cogs.items():
        body = [f"# {info['ar']}", "", f"**وزن TIMSS:** {info['timss_pct']}% · **قطر 2023:** {info['qatar_2023']} ({info['qatar_diff']:+d})", "",
                "## المجالات الفرعية"] + [f"- [[{lab}]]" for lab in info["areas"].values()] + ["", "[[00_الخريطة]]"]
        write(VAULT / "مستويات_معرفية" / f"{safe(info['ar'])}.md", {"tags": ["مستوى_معرفي"]}, "\n".join(body))
        for a, lab in info["areas"].items():
            ids = by_area.get(a, [])
            body = [f"# {lab}", "", f"ضمن [[{info['ar']}]] — {len(ids)} بنداً", ""] + [f"- [[{i}]]" for i in ids]
            write(VAULT / "مستويات_معرفية" / f"{safe(lab)}.md", {"tags": ["مجال_معرفي_فرعي"]}, "\n".join(body))

    # ---- الأنواع والمستويات الدولية
    for f, ids in by_fmt.items():
        write(VAULT / "أنواع_البنود" / f"{safe(fname[f])}.md", {"tags": ["نوع_بند"]},
              "\n".join([f"# {fname[f]}", "", f"{len(ids)} بنداً", ""] + [f"- [[{i}]]" for i in ids]))
    for b, ids in by_bm.items():
        write(VAULT / "مستويات_دولية" / f"{safe(bname[b])}.md", {"tags": ["مستوى_دولي"]},
              "\n".join([f"# {bname[b]} ({bms[b]['score']})", "", f"{len(ids)} بنداً", ""] + [f"- [[{i}]]" for i in ids]))

    # ---- المفاهيم الخاطئة
    for m, its in by_mis.items():
        body = [f"# المفهوم الخاطئ: {m}", "", f"تستهدفه {len(its)} بنود.", ""]
        for i in its:
            line = f"- [[{i['id']}]] ({tlink(i['topic'])})"
            rat = i.get("rationale") or {}
            hint = next(iter(rat.values()), "") if rat else ""
            if hint:
                line += f" — {hint}"
            body.append(line)
        write(VAULT / "مفاهيم_خاطئة" / f"{safe(m)}.md", {"tags": ["مفهوم_خاطئ"]}, "\n".join(body))

    # ---- الوثائق (نسخ للقراءة داخل Obsidian)
    docs = sorted(DOCS.glob("*.md"))
    for p in docs:
        (VAULT / "وثائق").mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, VAULT / "وثائق" / p.name)
    rep = BANK / "reports" / "coverage_report.md"
    if rep.exists():
        shutil.copy2(rep, VAULT / "وثائق" / "تقرير_التغطية.md")

    # ---- الخريطة الرئيسة
    n = len(bank["items"])
    body = ["# 🗺️ خريطة مشروع TIMSS 2027 — رياضيات الصف الثامن", "",
            f"**بنود التدريب:** {n} من 360 · **مهام PSI:** {len(bank.get('psi', []))} · **مفاهيم خاطئة موثقة:** {len(by_mis)}", "",
            "## المجالات"] + [f"- [[{v['ar']}]]" for v in domains.values()] + ["", "## المستويات المعرفية"] + \
           [f"- [[{v['ar']}]]" for v in cogs.values()] + ["", "## المستويات الدولية"] + [f"- [[{v['ar']}]]" for v in bms.values()] + \
           ["", "## أنواع البنود"] + [f"- [[{v['ar']}]]" for v in fmts.values()] + ["", "## الوثائق"] + \
           [f"- [[{p.stem}]]" for p in docs] + ["- [[تقرير_التغطية]]", ""]
    if (VAULT / "شيفرة").exists():
        body += ["## غراف الشيفرة (graphify)", "", "المجلد `شيفرة/` يحوي غراف السكربتات وشيفرة المنصة الذي ولّده graphify."]
    write(VAULT / "00_الخريطة.md", {"tags": ["خريطة"]}, "\n".join(body))

    # ---- إعدادات Obsidian (اتجاه RTL + ألوان الغراف) — تُكتب مرة واحدة فقط
    obs = VAULT / ".obsidian"
    obs.mkdir(exist_ok=True)
    if not (obs / "app.json").exists():
        (obs / "app.json").write_text(json.dumps({"rightToLeft": True, "showFrontmatter": False}, indent=2), encoding="utf-8")
    if not (obs / "graph.json").exists():
        rgb = lambda h: int(h.lstrip("#"), 16)
        groups = [("tag:#number", "#1B365D"), ("tag:#algebra", "#8A1538"), ("tag:#geometry", "#C2A649"), ("tag:#data", "#2A7F8F"),
                  ("path:مفاهيم_خاطئة", "#C62828"), ("path:شيفرة", "#7A8699")]
        cfg = {"colorGroups": [{"query": q, "color": {"a": 1, "rgb": rgb(c)}} for q, c in groups], "showTags": False, "showAttachments": False}
        (obs / "graph.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Obsidian vault: {VAULT} | بنود: {len(items)} | موضوعات: {len(topics)} | مفاهيم خاطئة: {len(by_mis)} | وثائق: {len(docs)}")


if __name__ == "__main__":
    main()
