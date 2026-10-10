# -*- coding: utf-8 -*-
"""
build_forms.py — يختار بنود الاختبار التشخيصي (32 بنداً) من بنك التدريب اختياراً حتمياً متوازناً،
ويكتبها في 02_بنك_الأسئلة/forms.yaml بترتيب كتلتين (كل كتلة تبدأ بالأسهل كما في TIMSS).

القيود:
  - المجالات وفق مخطط TIMSS (blueprint.forms.mock.content): الأعداد 10 · الجبر 10 · الهندسة 6 · البيانات 6.
  - كل موضوع من الموضوعات العشرين ممثَّل ببند واحد على الأقل وبندين على الأكثر.
  - المستويات المعرفية وفق blueprint.forms.mock.cognitive (11 / 13 / 8).
  - الصعوبة: تأسيسي 4 · سهل 10 · متوسط 11 · صعب 7 (نطاق قطر الحالي حول 450).
  - بنود مصحَّحة آلياً فقط (بلا select_explain / cr_explain) لتظهر النتيجة فوراً.

  python build_forms.py            # يكتب forms.yaml ويطبع ملخصاً
  python build_forms.py --check    # يطبع الملخص دون كتابة
"""
import argparse
import pathlib
import random
import sys
from collections import Counter

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
BANK = ROOT / "02_بنك_الأسئلة"
SEED = 2027
DIFF_TARGET = {"foundation": 4, "easy": 10, "medium": 11, "hard": 7}
RANK = {"foundation": 0, "easy": 1, "medium": 2, "hard": 3}
MANUAL = {"select_explain", "cr_explain"}


def load_items(bp):
    items = []
    for p in sorted((BANK / "items").glob("*.yaml")):
        for it in yaml.safe_load(p.read_text(encoding="utf-8")) or []:
            if it.get("format") in MANUAL:
                continue
            it["domain"] = bp["topics"][it["topic"]]["domain"]
            items.append(it)
    return items


def topic_quota(bp, content):
    """عدد البنود لكل موضوع: بند لكل موضوع، والباقي يوزَّع دورياً على موضوعات المجال."""
    quota = {}
    for dom, need in content.items():
        tops = [t for t, v in bp["topics"].items() if v["domain"] == dom]
        for t in tops:
            quota[t] = 1
        extra = need - len(tops)
        for k in range(extra):
            quota[tops[k % len(tops)]] += 1
    return quota


def penalty(sel, cog_target):
    cog = Counter(i["cognitive"] for i in sel)
    dif = Counter(i["difficulty"] for i in sel)
    fmt = Counter(i["format"] for i in sel)
    p = sum(abs(cog[c] - n) for c, n in cog_target.items()) * 3
    p += sum(abs(dif[d] - n) for d, n in DIFF_TARGET.items()) * 2
    p += max(0, fmt["mc"] - 20)                 # تنويع الأنواع: لا يطغى الاختيار من متعدد
    p += 2 * (fmt["grid_plot"] == 0) + 2 * (sum(v for f, v in fmt.items() if f.startswith("dragdrop")) == 0)
    return p


def choose(items, quota, cog_target, tries=40000):
    rnd = random.Random(SEED)
    by_topic = {}
    for it in items:
        by_topic.setdefault(it["topic"], []).append(it)
    missing = [t for t, n in quota.items() if len(by_topic.get(t, [])) < n]
    if missing:
        sys.exit(f"بنود غير كافية في الموضوعات: {missing}")
    best, best_p = None, None
    for _ in range(tries):
        sel = []
        for t, n in quota.items():
            sel += rnd.sample(by_topic[t], n)
        p = penalty(sel, cog_target)
        if best_p is None or p < best_p:
            best, best_p = sel, p
            if p == 0:
                break
    return best, best_p


def order_blocks(sel):
    """كتلتان متوازنتان في المجالات، وكل كتلة مرتبة من الأسهل إلى الأصعب."""
    rnd = random.Random(SEED + 1)
    b1, b2 = [], []
    by_dom = {}
    for it in sel:
        by_dom.setdefault(it["domain"], []).append(it)
    turn = 0
    for dom in ("number", "algebra", "geometry_measurement", "data_probability"):
        group = sorted(by_dom.get(dom, []), key=lambda i: (RANK[i["difficulty"]], i["id"]))
        for it in group:
            (b1 if turn % 2 == 0 else b2).append(it)
            turn += 1
    for b in (b1, b2):
        rnd.shuffle(b)
        b.sort(key=lambda i: RANK[i["difficulty"]])
    return b1, b2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    bp = yaml.safe_load((BANK / "blueprint.yaml").read_text(encoding="utf-8"))
    fm = bp["forms"]["mock"]
    items = load_items(bp)
    quota = topic_quota(bp, fm["content"])
    sel, p = choose(items, quota, fm["cognitive"])
    b1, b2 = order_blocks(sel)
    ids = [i["id"] for i in b1 + b2]
    print(f"التشخيصي: {len(ids)} بنداً (عقوبة الانحراف عن الأهداف = {p})")
    print("  المجالات:", dict(Counter(i["domain"] for i in sel)))
    print("  المعرفي:", dict(Counter(i["cognitive"] for i in sel)), "| الهدف:", fm["cognitive"])
    print("  الصعوبة:", dict(Counter(i["difficulty"] for i in sel)), "| الهدف:", DIFF_TARGET)
    print("  الأنواع:", dict(Counter(i["format"] for i in sel)))
    if a.check:
        return
    head = (
        "# ============================================================================\n"
        "# الاختبار التشخيصي — يولّده scripts/build_forms.py (لا تعدّله يدوياً؛ أعد التوليد)\n"
        "# 32 بنداً من بنك التدريب: كتلتان × 16، كل كتلة من الأسهل إلى الأصعب.\n"
        "# تُحجب هذه البنود عن تدريب الطالب ومحاكاته حتى يُنهي التشخيصي.\n"
        "# ============================================================================\n"
    )
    body = yaml.safe_dump({"diagnostic": {"items": ids}}, allow_unicode=True, sort_keys=False, default_flow_style=False)
    (BANK / "forms.yaml").write_text(head + body, encoding="utf-8")
    print("كُتب:", BANK / "forms.yaml")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
