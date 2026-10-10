# -*- coding: utf-8 -*-
"""
review_items.py — عرض مضغوط للبنود لمراجعتها بأقل توكنز (بلا الحل والاقتراح العلاجي افتراضياً).

  python review_items.py A1.yaml            # كل بنود الملف
  python review_items.py A1.yaml --full     # مع الحل
  python review_items.py A1.yaml --ids M8-A1-003 M8-A1-007
"""
import argparse
import pathlib
import re
import sys

import yaml

ITEMS = pathlib.Path(__file__).resolve().parents[1] / "02_بنك_الأسئلة" / "items"
LET = "ABCD"


def sq(s, n=400):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[:n] + "…"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--ids", nargs="*")
    a = ap.parse_args()
    data = yaml.safe_load((ITEMS / a.file).read_text(encoding="utf-8")) or []
    for it in data:
        if a.ids and it["id"] not in a.ids:
            continue
        f = it["format"]
        print(f"■ {it['id']} | {it['cognitive'][:4]}/{it['area']} | {it['difficulty']} | {it['benchmark']} | {f} | {it['context']}")
        print("  Q:", sq(it["stem"]))
        if it.get("table"):
            t = it["table"]
            print("  T:", " | ".join(t.get("headers", [])), "//", " // ".join(" | ".join(map(str, r)) for r in t.get("rows", [])))
        if it.get("figure"):
            fig = it["figure"]
            figs = fig if isinstance(fig, list) else [fig]
            print("  F:", "; ".join(sq({k: v for k, v in g.items() if k not in ("alt",)}, 220) for g in figs))
        if it.get("options"):
            print("  O:", " · ".join(f"{LET[i]}) {sq(o if isinstance(o, str) else '[fig] ' + str(o.get('figure', {}))[:120], 90)}" for i, o in enumerate(it["options"])), "| key:", it.get("key"))
        if f == "numeric":
            print("  ANS:", it["answer"])
        elif f == "multi_numeric":
            print("  ANS:", [(x["label"], x["value"]) for x in it["fields"]], it.get("scoring"))
        elif f.startswith("dragdrop"):
            print("  CARDS:", [c if isinstance(c, str) else c.get("text") for c in it["cards"]])
            if it.get("template"):
                print("  TPL:", it["template"])
            if it.get("categories"):
                print("  CATS:", it["categories"])
            print("  KEY:", it.get("key"), "| check:", it.get("check"))
        elif f == "grid_plot":
            print("  GRID:", it["grid"], "given:", sq(it.get("given"), 200), "| mode:", it.get("mode"), "| key:", it["key"])
        elif f in ("select_explain", "cr_explain"):
            rb = it.get("rubric", {})
            print("  RUBRIC:", sq(rb.get("full") or [c.get("desc") for c in rb.get("codes", [])], 300))
        if it.get("verify"):
            print("  V:", sq(it["verify"], 200))
        if a.full:
            print("  SOL:", sq(it.get("solution"), 600))
        print()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
