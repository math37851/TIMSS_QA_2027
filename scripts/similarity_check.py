# -*- coding: utf-8 -*-
"""similarity_check.py — يكشف بنود الاختبارات المحمية القريبة جداً من بنود البنك أو من بعضها.
  python similarity_check.py mock_X3_B1.yaml [--min 0.6]"""
import argparse, difflib, pathlib, re, sys
import yaml
BANK = pathlib.Path(__file__).resolve().parents[1] / "02_بنك_الأسئلة"
sq = lambda s: re.sub(r"\s+", " ", str(s or "")).strip()
def sig(i):  # المتن + البدائل: يكشف تطابق البدائل حتى لو اختلفت الصياغة
    return sq(i.get("stem")) + " | " + " ".join(sq(o) for o in (i.get("options") or []) if isinstance(o, str))
def mock_items(p):
    d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return [i for b in d.get("blocks", []) for i in b.get("items", [])]
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("files", nargs="+"); ap.add_argument("--min", type=float, default=0.6)
    a = ap.parse_args()
    bank = [i for p in sorted((BANK / "items").glob("*.yaml")) for i in (yaml.safe_load(p.read_text(encoding="utf-8")) or [])]
    bank += [i for p in sorted((BANK / "psi").glob("*.yaml")) for i in (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("items", [])]
    targets = {f: mock_items(BANK / "secure" / f) for f in a.files}
    others = [i for p in sorted((BANK / "secure").glob("mock_*.yaml")) if p.name not in targets for i in mock_items(p)]
    found = 0
    for f, its in targets.items():
        for m in its:
            pool = [x for x in bank + others if x.get("topic") == m.get("topic")]
            best = max(((difflib.SequenceMatcher(None, sig(m), sig(x)).ratio(), x["id"]) for x in pool), default=(0, ""))
            if best[0] >= a.min:
                found += 1
                print(f"{best[0]:.2f}  {m['id']} ≈ {best[1]}  | {sq(m.get('stem'))[:90]}")
    print(f"قريبة (≥ {a.min}): {found}")
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8"); main()
