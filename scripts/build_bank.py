# -*- coding: utf-8 -*-
"""
build_bank.py — بناء بنك أسئلة TIMSS 2027 (رياضيات الصف الثامن) والتحقق منه.

الخطوات:
  1) قراءة المخطط (blueprint.yaml) والقاموس (glossary.yaml) وملفات البنود YAML.
  2) التحقق من مخطط كل بند (الحقول الإلزامية حسب النوع والقيم المسموح بها).
  3) التدقيق اللغوي/الرمزي: أرقام 0–9 فقط، بدائل A–D، الرياضيات داخل $…$، لا حروف عربية داخل الرياضيات.
  4) التحقق الآلي من الإجابات بـ sympy عبر الحقل verify.
  5) توليد الرسوم SVG من مواصفاتها (figures.py).
  6) تقرير التغطية مقابل المخطط + ملفات المنصة (build/bank.json و build/secure.json) + bank.csv.

الاستعمال:
  python build_bank.py            # بناء مع تقرير (الأخطاء تُطبع ويُعاد رمز خروج 1)
  python build_bank.py --strict   # يعامل التحذيرات الحرجة (بنود بلا تحقق آلي في أنواع رقمية) كأخطاء
"""

import argparse
import csv
import datetime as dt
import json
import math
import pathlib
import re
import statistics
import sys
from collections import Counter, defaultdict

import sympy as sp
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import figures  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
BANK = ROOT / "02_بنك_الأسئلة"
ITEMS_DIR = BANK / "items"
BUILD = BANK / "build"
REPORTS = BANK / "reports"

AR_LETTER = re.compile(r"[\u0621-\u064A\u0660-\u0669\u066E-\u06D3\u06FA-\u06FF]")
LETTERS = "ABCD"


# ============================================================ أدوات عامة
class Log:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, where, msg):
        self.errors.append(f"[{where}] {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"[{where}] {msg}")


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def num(v):
    """تحويل قيمة (عدد أو نص مثل '3/4' أو '−2.5') إلى sympy."""
    if isinstance(v, (int, float)):
        return sp.nsimplify(v, rational=True) if isinstance(v, float) else sp.Integer(v)
    s = str(v).strip().replace("−", "-").replace(" ", "")
    s = re.sub(r"\\frac\{(-?\d+)\}\{(\d+)\}", r"(\1)/(\2)", s)
    s = s.replace("$", "")
    return sp.nsimplify(sp.sympify(s, rational=True), rational=True)


def equal(a, b, tol=None):
    try:
        A, B = sp.sympify(a), sp.sympify(b)
        if tol:
            return abs(float(sp.N(A - B))) <= float(tol) + 1e-12
        return sp.simplify(A - B) == 0
    except Exception:
        try:
            return abs(float(a) - float(b)) < 1e-9
        except Exception:
            return False


def _mean(xs):
    return sum(num(v) for v in xs) / len(xs)


def _median(xs):
    v = sorted(num(t) for t in xs)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


X, Y = sp.symbols("x y")
VERIFY_NS = {
    "Rational": sp.Rational, "R": sp.Rational, "sqrt": sp.sqrt, "pi": sp.pi, "Integer": sp.Integer,
    "simplify": sp.simplify, "nsimplify": sp.nsimplify, "isprime": sp.isprime, "factorint": sp.factorint,
    "gcd": sp.gcd, "lcm": sp.lcm, "Abs": sp.Abs, "floor": sp.floor, "ceiling": sp.ceiling,
    "solve": sp.solve, "Eq": sp.Eq, "expand": sp.expand, "factor": sp.factor, "symbols": sp.symbols,
    "binomial": sp.binomial, "factorial": sp.factorial, "N": sp.N, "divisors": sp.divisors,
    "x": X, "y": Y, "mean": _mean, "median": _median, "num": num,
    "abs": abs, "min": min, "max": max, "sum": sum, "len": len, "sorted": sorted, "all": all, "any": any,
    "range": range, "list": list, "set": set, "tuple": tuple, "round": round, "statistics": statistics,
    "True": True, "False": False,
}


def run_verify(expr, extra=None):
    # الأسماء في globals (لا locals) حتى تراها المولّدات و lambda داخل التعبير
    ns = dict(VERIFY_NS)
    if extra:
        ns.update(extra)
    ns["__builtins__"] = {}
    return eval(expr, ns)


def split_math(s):
    """يعيد قائمة (is_math, text) بحسب علامات $."""
    parts = re.split(r"(?<!\\)\$", s)
    return [(i % 2 == 1, p) for i, p in enumerate(parts)]


# ============================================================ التدقيق اللغوي والرمزي
class Linter:
    def __init__(self, glossary, log):
        self.log = log
        self.forbidden = [(re.compile(p["pattern"]), p["message"]) for p in glossary.get("forbidden_patterns", [])]
        self.variants = []
        for t in glossary.get("terms", []):
            for v in t.get("variants", []) or []:
                self.variants.append((v, t["ar"], t.get("status")))

    def text(self, where, s):
        if not s:
            return
        s = str(s)
        for rx, msg in self.forbidden:
            if rx.search(s):
                self.log.err(where, f"{msg}: «{rx.search(s).group(0)}»")
        if len(re.findall(r"(?<!\\)\$", s)) % 2:
            self.log.err(where, "علامات $ غير متوازنة")
            return
        for is_math, seg in split_math(s):
            if is_math:
                if AR_LETTER.search(seg):
                    self.log.err(where, f"حروف عربية داخل تعبير رياضي: ${seg}$ (ضع النص العربي خارج $…$)")
            else:
                if re.search(r"\d\s*[+\-−×÷*/=<>≤≥^]\s*\d", seg):
                    self.log.warn(where, f"تعبير رياضي خارج $…$: «{seg.strip()[:40]}»")
                if re.search(r"(^|[\s(،,])[-−]\d", seg):
                    self.log.warn(where, f"عدد سالب خارج $…$: «{seg.strip()[:40]}»")
                if re.search(r"(?<![A-Za-z\\])(?:x|y|n)(?![A-Za-z])", seg) and AR_LETTER.search(seg):
                    self.log.warn(where, f"متغير لاتيني خارج $…$: «{seg.strip()[:40]}»")
                for v, canon, status in self.variants:
                    if v in seg:
                        self.log.warn(where, f"مصطلح غير موحّد «{v}» ← استعمل «{canon}» ({status})")


# ============================================================ التحقق من البنود
COMMON_REQUIRED = ["id", "topic", "cognitive", "area", "difficulty", "benchmark", "format", "context", "stem", "solution"]
ID_PATTERNS = {
    "practice": re.compile(r"^M8-(N[1-6]|A[1-6]|G[1-4]|D[1-4])-\d{3}$"),
    "psi": re.compile(r"^M8-PSI\d-\d{2}$"),
    "mock": re.compile(r"^M8-X\d-\d{2}$"),
}


def norm_cards(cards):
    out = []
    for i, c in enumerate(cards):
        if isinstance(c, dict):
            out.append({"id": c.get("id", f"c{i+1}"), "text": str(c["text"]), "value": c.get("value")})
        else:
            out.append({"id": f"c{i+1}", "text": str(c), "value": None})
    for c in out:
        if c["value"] is None:
            try:
                c["value"] = float(num(c["text"]))
            except Exception:
                c["value"] = None
    return out


def card_id(cards, ref, where, log):
    for c in cards:
        if ref == c["id"] or str(ref) == c["text"]:
            return c["id"]
    log.err(where, f"مرجع بطاقة غير موجود في cards: {ref}")
    return None


def js_to_py(expr):
    e = expr.replace("&&", " and ").replace("||", " or ").replace("===", "==").replace("!==", "!=")
    e = re.sub(r"!(?!=)", " not ", e)
    return e


def validate_item(it, bp, lint, log, kind="practice"):
    where = it.get("id", "?")
    chk_ = it.get("check")
    if isinstance(chk_, str) and re.search(r"(?<![A-Za-z_])(and|or|not)(?![A-Za-z_])", chk_):
        log.err(where, "check يُنفَّذ في المتصفح (JS): استعمل && و|| و! بدل and/or/not")
    # أحرف التحكم تنتج غالباً من تهريب خاطئ (مثل \times ← TAB + "imes" أو \frac ← FF + "rac")
    ctl = {"\t": "TAB", "\f": "FF", "\b": "BS", "\v": "VT", "\a": "BEL", "\r": "CR"}

    def scan(v):
        if isinstance(v, str):
            return [n for c, n in ctl.items() if c in v]
        if isinstance(v, dict):
            return [n for x in v.values() for n in scan(x)]
        if isinstance(v, list):
            return [n for x in v for n in scan(x)]
        return []
    found = sorted(set(scan({k: v for k, v in it.items() if not k.startswith("_")})))
    if found:
        log.err(where, f"أحرف تحكم في النص ({', '.join(found)}): غالباً شرطة مائلة مفقودة قبل times أو frac أو text")
    # عدد مع وحدة لاتينية خارج $…$ داخل نص عربي يُعرض معكوساً («cm 12»): يجب أن يكون داخل الرياضيات
    unit_re = re.compile(r"\d+(?:\.\d+)?\s?(?:cm|mm|km|kg|mL|m|g|L|kWh|Mbps|°C)(?![A-Za-z])")
    texts_ = [it.get(k) for k in ("stem", "solution", "remediation", "hint", "model_answer")]
    texts_ += [o for o in (it.get("options") or []) if isinstance(o, str)]
    texts_ += [c if isinstance(c, str) else c.get("text") for c in (it.get("cards") or [])]
    texts_ += list((it.get("rationale") or {}).values())
    tbl = it.get("table") or {}
    texts_ += [str(x) for x in (tbl.get("headers") or [])] + [str(x) for r in (tbl.get("rows") or []) for x in r]
    for s_ in texts_:
        if isinstance(s_, str) and re.search(r"[؀-ۿ]", s_):
            m_ = unit_re.search(re.sub(r"\$[^$]*\$", "", s_))
            if m_:
                log.err(where, f"«{m_.group(0)}» خارج $…$ يُعرض معكوساً في النص العربي: اكتبه رياضياً مثل $12\\,\\text{{cm}}$")
    # الكسر بالشرطة (3/5) غامض الاتجاه للقارئ العربي (قد يُقرأ 5/3): يُكتب مكدّساً دائماً
    frac_re = re.compile(r"(?<![\d.])\d{1,3}\s*/\s*\d{1,3}(?![\d.])")
    for s_ in texts_:
        if isinstance(s_, str) and frac_re.search(s_):
            log.err(where, f"كسر بالشرطة «{frac_re.search(s_).group(0)}» غامض الاتجاه في النص العربي: اكتبه مكدّساً مثل $\\frac{{3}}{{5}}$")
    for k in COMMON_REQUIRED:
        if k not in it or it[k] in (None, ""):
            log.err(where, f"حقل إلزامي مفقود: {k}")
    if not ID_PATTERNS[kind].match(str(it.get("id", ""))):
        log.err(where, f"نمط المعرّف غير صحيح لنوع {kind}")
    t = it.get("topic")
    if t not in bp["topics"]:
        log.err(where, f"موضوع غير معروف: {t}")
    elif kind == "practice" and not str(it.get("id", "")).startswith(f"M8-{t}-"):
        log.err(where, f"المعرّف لا يطابق الموضوع {t}")
    cog = it.get("cognitive")
    if cog not in bp["cognitive_domains"]:
        log.err(where, f"مستوى معرفي غير معروف: {cog}")
    elif it.get("area") not in bp["cognitive_domains"][cog]["areas"]:
        log.err(where, f"المجال المعرفي الفرعي {it.get('area')} لا يتبع {cog}")
    for fld, allowed in (("difficulty", bp["difficulty_levels"]), ("benchmark", bp["benchmarks"]),
                         ("format", bp["formats"]), ("context", bp["contexts"])):
        if it.get(fld) not in allowed:
            log.err(where, f"قيمة غير مسموحة للحقل {fld}: {it.get(fld)}")
    tm = it.get("time", 90)
    if not (isinstance(tm, int) and 15 <= tm <= 900):
        log.err(where, "time يجب أن يكون عدداً صحيحاً بالثواني بين 15 و900")
    if not it.get("remediation"):
        log.warn(where, "لا يوجد remediation (اقتراح علاجي)")

    fmt_ = it.get("format")
    # ---- حسب النوع
    if fmt_ == "mc":
        opts = it.get("options") or []
        if len(opts) != 4:
            log.err(where, "اختيار من متعدد يتطلب 4 بدائل بالضبط")
        texts = [o if isinstance(o, str) else json.dumps(o, ensure_ascii=False, sort_keys=True) for o in opts]
        if len(set(texts)) != len(texts):
            log.err(where, "بدائل مكررة")
        if it.get("key") not in LETTERS[:len(opts)]:
            log.err(where, f"مفتاح غير صالح: {it.get('key')}")
        rat = it.get("rationale") or {}
        for L in LETTERS[:len(opts)]:
            if L != it.get("key") and not rat.get(L):
                log.warn(where, f"لا يوجد تفسير للمشتّت {L}")
    elif fmt_ == "numeric":
        ans = it.get("answer") or {}
        if "value" not in ans:
            log.err(where, "numeric يتطلب answer.value")
    elif fmt_ == "multi_numeric":
        fl = it.get("fields") or []
        if len(fl) < 2:
            log.err(where, "multi_numeric يتطلب خانتين على الأقل")
        for f in fl:
            if "value" not in f or "label" not in f:
                log.err(where, "كل خانة تتطلب label و value")
        mode = (it.get("scoring") or {}).get("mode", "all")
        if mode not in ("all", "each", "partial"):
            log.err(where, "scoring.mode يجب أن يكون all أو each أو partial")
    elif fmt_ in ("dragdrop_slots", "dragdrop_order", "dragdrop_categorize"):
        if not it.get("cards"):
            log.err(where, "بطاقات السحب cards مفقودة")
        else:
            cards = norm_cards(it["cards"])
            if fmt_ == "dragdrop_slots":
                tpl = it.get("template", "")
                slots = re.findall(r"\[\[(\w+)\]\]", tpl)
                if not slots:
                    log.err(where, "القالب template لا يحوي خانات [[…]]")
                key = it.get("key") or {}
                for s in slots:
                    if str(s) not in {str(k) for k in key}:
                        log.err(where, f"لا مفتاح للخانة {s}")
                for s, ref in key.items():
                    card_id(cards, ref, where, log)
            elif fmt_ == "dragdrop_order":
                key = it.get("key") or []
                if len(key) != len(cards):
                    log.err(where, "مفتاح الترتيب يجب أن يشمل كل البطاقات")
                for ref in key:
                    card_id(cards, ref, where, log)
            else:
                cats = it.get("categories") or []
                if len(cats) < 2:
                    log.err(where, "التصنيف يتطلب فئتين على الأقل")
                key = it.get("key") or {}
                for ref, cat in key.items():
                    card_id(cards, ref, where, log)
                    if cat not in cats:
                        log.err(where, f"فئة غير معرفة في المفتاح: {cat}")
                if len(key) != len(cards):
                    log.err(where, "مفتاح التصنيف يجب أن يشمل كل البطاقات")
    elif fmt_ == "grid_plot":
        g = it.get("grid") or {}
        for k in ("xmin", "xmax", "ymin", "ymax"):
            if k not in g:
                log.err(where, f"grid.{k} مفقود")
        if it.get("mode") not in ("points", "polygon", "segment"):
            log.err(where, "mode يجب أن يكون points أو polygon أو segment")
        key = it.get("key") or []
        if not key:
            log.err(where, "مفتاح النقاط مفقود")
        for p in key:
            if not (g.get("xmin", -99) <= p[0] <= g.get("xmax", 99) and g.get("ymin", -99) <= p[1] <= g.get("ymax", 99)):
                log.err(where, f"نقطة المفتاح {p} خارج الشبكة")
    elif fmt_ == "select_explain":
        opts = it.get("options") or []
        if not 2 <= len(opts) <= 4:
            log.err(where, "اختر وبرّر يتطلب 2–4 بدائل")
        if it.get("key") not in LETTERS[:len(opts)]:
            log.err(where, "مفتاح الاختيار غير صالح")
        rub = it.get("rubric") or {}
        if not rub.get("full") or not rub.get("zero"):
            log.err(where, "rubric يتطلب full و zero")
    elif fmt_ == "cr_explain":
        rub = it.get("rubric") or {}
        if not (rub.get("full") or rub.get("codes")):
            log.err(where, "rubric يتطلب full أو codes")
        if not it.get("model_answer"):
            log.warn(where, "لا توجد إجابة نموذجية model_answer")

    # ---- التدقيق النصي
    lint.text(f"{where}:stem", it.get("stem"))
    for i, o in enumerate(it.get("options") or []):
        if isinstance(o, str):
            lint.text(f"{where}:option{LETTERS[i]}", o)
    for c in it.get("cards") or []:
        lint.text(f"{where}:card", c if isinstance(c, str) else c.get("text"))
    for fld in ("solution", "remediation", "hint", "template", "model_answer"):
        lint.text(f"{where}:{fld}", it.get(fld))
    for L, r in (it.get("rationale") or {}).items():
        lint.text(f"{where}:rationale{L}", r)


# ============================================================ التحقق الآلي من الإجابات
BOOL_LIST = re.compile(r"==\s*\[\s*((?:True|False)(?:\s*,\s*(?:True|False))+)\s*\]")


def key_matches_bool_list(it, expr):
    """في بنود الاختيار: إن احتوى verify قائمة [False, True, ...] بعدد البدائل وفيها True واحد،
    فيجب أن يطابق موضعه حرف المفتاح. يعيد True/False، أو None إن لم توجد قائمة كهذه."""
    opts = it.get("options") or []
    if it.get("format") not in ("mc", "select_explain") or not opts or it.get("key") not in LETTERS:
        return None
    for m in BOOL_LIST.finditer(expr):
        vals = [v.strip() == "True" for v in m.group(1).split(",")]
        if len(vals) == len(opts) and sum(vals) == 1:
            return vals.index(True) == LETTERS.index(it["key"])
    return None


def verify_item(it, log):
    """يعيد True إذا تحقق آلياً، False إذا فشل، None إذا لا يوجد تحقق."""
    where = it.get("id", "?")
    fmt_ = it.get("format")
    expr = it.get("verify")
    try:
        if fmt_ in ("dragdrop_slots",):
            cards = norm_cards(it["cards"])
            byid = {c["id"]: c for c in cards}
            key = it.get("key") or {}
            vals = {}
            for s, ref in key.items():
                cid = card_id(cards, ref, where, log)
                vals[f"s{s}"] = byid[cid]["value"] if cid else None
            chk = it.get("check")
            if chk:
                ok = bool(run_verify(js_to_py(chk), vals))
                if not ok:
                    log.err(where, "المفتاح لا يحقق شرط check")
                    return False
                return True
            if expr:
                ok = bool(run_verify(expr, vals))
                if not ok:
                    log.err(where, "المفتاح لا يحقق verify")
                return ok
            return None
        if fmt_ == "dragdrop_order":
            cards = norm_cards(it["cards"])
            byid = {c["id"]: c for c in cards}
            ids = [card_id(cards, r, where, log) for r in it.get("key", [])]
            if it.get("order_by_value", True) and all(byid[i]["value"] is not None for i in ids if i):
                vs = [byid[i]["value"] for i in ids]
                asc = it.get("direction", "asc") == "asc"
                ok = all((vs[k] < vs[k + 1]) if asc else (vs[k] > vs[k + 1]) for k in range(len(vs) - 1))
                if not ok:
                    log.err(where, f"مفتاح الترتيب لا يطابق القيم العددية: {vs}")
                    return False
                return True
            return None
        if fmt_ == "grid_plot" and expr:
            ok = bool(run_verify(expr, {"P": [tuple(p) for p in it["key"]]}))
            if not ok:
                log.err(where, "مفتاح الرسم لا يحقق verify")
            return ok
        if not expr:
            return None
        res = run_verify(expr)
        if isinstance(res, (bool, sp.logic.boolalg.BooleanAtom)) or res in (True, False):
            if not bool(res):
                log.err(where, f"verify أعاد False: {expr}")
                return False
            if key_matches_bool_list(it, expr) is False:
                log.err(where, f"موضع True في قائمة verify لا يطابق المفتاح {it.get('key')}")
                return False
            return True
        if fmt_ == "numeric":
            ans = it["answer"]
            ok = equal(res, num(ans["value"]), ans.get("tol"))
            if not ok:
                log.err(where, f"الإجابة {ans['value']} ≠ الناتج المحسوب {sp.N(res, 8)}")
            return ok
        if fmt_ == "multi_numeric":
            res = list(res)
            fl = it["fields"]
            ok = len(res) == len(fl) and all(equal(r, num(f["value"]), f.get("tol")) for r, f in zip(res, fl))
            if not ok:
                log.err(where, f"قيم الخانات {[f['value'] for f in fl]} ≠ المحسوبة {[sp.N(r, 6) for r in res]}")
            return ok
        if fmt_ == "mc":
            ov = it.get("option_values")
            if not ov:
                log.warn(where, "verify موجود لكن option_values مفقودة؛ لا يمكن مطابقة البديل")
                return None
            ki = LETTERS.index(it["key"])
            tol = it.get("tol")
            if not equal(res, num(ov[ki]), tol):
                log.err(where, f"قيمة البديل الصحيح {ov[ki]} ≠ الناتج {sp.N(res, 8)}")
                return False
            for i, v in enumerate(ov):
                if i != ki and v is not None and equal(num(v), res, tol):
                    log.err(where, f"المشتّت {LETTERS[i]} يساوي الإجابة الصحيحة!")
                    return False
            return True
        log.warn(where, "نوع لا يدعم مقارنة verify الرقمية")
        return None
    except Exception as e:
        log.err(where, f"خطأ في تنفيذ verify: {type(e).__name__}: {e}")
        return False


# ============================================================ الإخراج
def render_figures(it, log):
    where = it.get("id", "?")
    out = {}
    try:
        if it.get("figure"):
            out["figure_svg"] = figures.render(it["figure"])
        if it.get("format") in ("mc", "select_explain"):
            osvg = []
            for o in it.get("options") or []:
                osvg.append(figures.render(o["figure"]) if isinstance(o, dict) and o.get("figure") else None)
            if any(osvg):
                out["options_svg"] = osvg
        if it.get("format") == "grid_plot":
            g = dict(it["grid"])
            given = it.get("given") or {}
            base = {"type": "coord", **g, **given}
            out["print_svg"] = figures.render(base)
            key_spec = dict(base)
            kp = [list(p) for p in it["key"]]
            if it.get("mode") == "polygon":
                key_spec["polygons"] = list(given.get("polygons", [])) + [{"points": kp, "color": figures.MAROON, "fill": figures.MAROON}]
            elif it.get("mode") == "segment":
                key_spec["segments"] = list(given.get("segments", [])) + [{"points": kp, "color": figures.MAROON}]
            key_spec["points"] = list(given.get("points", [])) + [{"x": p[0], "y": p[1], "color": figures.MAROON} for p in kp]
            out["key_svg"] = figures.render(key_spec)
    except Exception as e:
        log.err(where, f"فشل توليد الرسم: {type(e).__name__}: {e}")
    return out


PUBLIC_FIELDS = ["id", "topic", "cognitive", "area", "difficulty", "benchmark", "format", "context", "time",
                 "stem", "table", "options", "key", "rationale", "answer", "fields", "scoring", "cards", "template",
                 "categories", "direction", "order_labels", "template_dir", "check", "reuse", "grid", "mode", "given", "count", "rubric", "points",
                 "model_answer", "solution", "remediation", "hint", "misconceptions", "qatar_link", "psi", "note"]


def to_public(it, bp, verified, figs):
    o = {k: it[k] for k in PUBLIC_FIELDS if k in it and it[k] is not None}
    o["domain"] = bp["topics"][it["topic"]]["domain"]
    o["time"] = it.get("time", 90)
    o["verified"] = verified
    if it.get("format") in ("dragdrop_slots", "dragdrop_order", "dragdrop_categorize"):
        cards = norm_cards(it["cards"])
        o["cards"] = cards
        L = Log()
        if it["format"] == "dragdrop_slots":
            o["key"] = {str(s): card_id(cards, r, "", L) for s, r in it["key"].items()}
        elif it["format"] == "dragdrop_order":
            o["key"] = [card_id(cards, r, "", L) for r in it["key"]]
        else:
            o["key"] = {card_id(cards, r, "", L): cat for r, cat in it["key"].items()}
    if it.get("options"):
        o["options"] = [x if isinstance(x, str) else x.get("text", "") for x in it["options"]]
    # النقاط القصوى
    f = it.get("format")
    sc = it.get("scoring") or {}
    if f == "multi_numeric":
        mode = sc.get("mode", "all")
        o["points"] = sc.get("points", len(it["fields"]) if mode == "each" else (2 if mode == "partial" else 1))
    elif f == "cr_explain":
        codes = (it.get("rubric") or {}).get("codes")
        o["points"] = max((c.get("points", 0) for c in codes), default=1) if codes else it.get("points", 1)
    else:
        o["points"] = it.get("points", sc.get("points", 1))
    o["human_scored"] = f in ("select_explain", "cr_explain")
    o.update(figs)
    return o


def plain(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


# ============================================================ التقرير
def pct(a, b):
    return 0 if not b else round(100 * a / b, 1)


def coverage_report(bp, items, psi_tasks, mocks, diag_ids, log, verified_map):
    L = []
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    T = bp["targets"]
    total_target = T["practice_total"]
    n = len(items)
    L.append("# 📊 تقرير تغطية بنك الأسئلة — TIMSS 2027 رياضيات الصف الثامن")
    L.append(f"> مولَّد آلياً بواسطة `scripts/build_bank.py` في {now}. لا تعدّل هذا الملف يدوياً.\n")
    L.append("## 1. الملخص")
    L.append("| المؤشر | القيمة |")
    L.append("|---|---|")
    L.append(f"| بنود التدريب | **{n}** من {total_target} ({pct(n, total_target)}%) |")
    L.append(f"| مهام PSI | {len(psi_tasks)} مهمة، {sum(len(t['items']) for t in psi_tasks)} بنداً |")
    L.append(f"| الاختبارات التجريبية | {len(mocks)} نموذجاً، {sum(len(b['items']) for f in mocks for b in f['blocks'])} بنداً محمياً |")
    L.append(f"| الاختبار التشخيصي | {len(diag_ids)} بنداً من البنك |")
    ver = sum(1 for v in verified_map.values() if v is True)
    unv = [k for k, v in verified_map.items() if v is None]
    L.append(f"| تحقق آلي ناجح | {ver} بنداً |")
    L.append(f"| بلا تحقق آلي (مراجعة يدوية) | {len(unv)} بنداً |")
    L.append(f"| أخطاء | {len(log.errors)} |")
    L.append(f"| تحذيرات | {len(log.warnings)} |")
    L.append("")

    # حسب الموضوع
    L.append("## 2. التغطية حسب الموضوع (مقابل المستهدف)")
    L.append("| الموضوع | المجال | معرفة | تطبيق | استدلال | تأسيسي | سهل | متوسط | صعب | المجموع | المستهدف | الحالة |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    by_topic = defaultdict(list)
    for it in items:
        by_topic[it["topic"]].append(it)
    for tid, tp in bp["topics"].items():
        lst = by_topic.get(tid, [])
        size = tp["bank_target"]
        ct = Counter(i["cognitive"] for i in lst)
        cd = Counter(i["difficulty"] for i in lst)
        tc = T["cognitive_by_topic_size"][size]
        td = T["difficulty_by_topic_size"][size]
        cell = lambda have, want: f"{have}/{want}" + ("" if have >= want else " ⚠️")
        status = "✅" if len(lst) >= size else ("🟡" if lst else "⬜")
        L.append(f"| **{tid}** {tp['area_ar']} | {bp['domains'][tp['domain']]['ar']} | "
                 f"{cell(ct['knowing'], tc['knowing'])} | {cell(ct['applying'], tc['applying'])} | {cell(ct['reasoning'], tc['reasoning'])} | "
                 f"{cell(cd['foundation'], td['foundation'])} | {cell(cd['easy'], td['easy'])} | {cell(cd['medium'], td['medium'])} | {cell(cd['hard'], td['hard'])} | "
                 f"**{len(lst)}** | {size} | {status} |")
    L.append("")

    # المجالات
    L.append("## 3. التوزيع حسب المجال والمستوى المعرفي")
    dom = Counter(bp["topics"][i["topic"]]["domain"] for i in items)
    cog = Counter(i["cognitive"] for i in items)
    L.append("| المجال | عدد البنود | نسبة البنك | وزن TIMSS | أداء قطر 2023 |")
    L.append("|---|---|---|---|---|")
    for d, info in bp["domains"].items():
        L.append(f"| {info['ar']} | {dom[d]} | {pct(dom[d], n)}% | {info['timss_pct']}% | {info['qatar_2023']} ({info['qatar_diff']:+d}) |")
    L.append("")
    L.append("| المستوى المعرفي | عدد البنود | نسبة البنك | المستهدف في البنك | وزن TIMSS |")
    L.append("|---|---|---|---|---|")
    bank_cog_target = {"knowing": 30, "applying": 40, "reasoning": 30}
    for c, info in bp["cognitive_domains"].items():
        L.append(f"| {info['ar']} | {cog[c]} | {pct(cog[c], n)}% | {bank_cog_target[c]}% | {info['timss_pct']}% |")
    L.append("")

    # الأنواع والسياق
    L.append("## 4. أنواع الأسئلة والسياقات")
    groups = Counter(bp["formats"][i["format"]]["group"] for i in items)
    L.append("| المجموعة | العدد | النسبة | المستهدف |")
    L.append("|---|---|---|---|")
    tol = T["format_tolerance_pct"]
    names = {"mc": "اختيار من متعدد", "numeric": "إدخال رقمي", "dragdrop": "سحب وإفلات", "grid": "رسم على المستوى", "explain": "اختر وبرّر / مفتوح"}
    for g, want in T["format_groups_pct"].items():
        p = pct(groups[g], n)
        flag = "" if abs(p - want) <= tol or n < 60 else " ⚠️"
        L.append(f"| {names[g]} | {groups[g]} | {p}%{flag} | {want}% |")
    ctx = Counter(i["context"] for i in items)
    contextual = ctx["qatar"] + ctx["real"]
    L.append("")
    L.append(f"- **في سياق:** {contextual} ({pct(contextual, n)}%) — منها قطري {ctx['qatar']} ({pct(ctx['qatar'], contextual)}% من السياقية)")
    L.append(f"- **رياضي مجرد:** {ctx['pure']} ({pct(ctx['pure'], n)}%)")
    bm = Counter(i["benchmark"] for i in items)
    L.append(f"- **المستويات الدولية المستهدفة:** " + "، ".join(f"{bp['benchmarks'][k]['ar']}: {bm[k]}" for k in bp["benchmarks"]))
    L.append("")

    # النماذج
    if mocks:
        L.append("## 5. الاختبارات التجريبية (مطابقة المخطط)")
        fm = bp["forms"]["mock"]
        L.append("| النموذج | البنود | الأعداد | الجبر | الهندسة | البيانات | معرفة | تطبيق | استدلال |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for f in mocks:
            its = [i for b in f["blocks"] for i in b["items"]]
            d = Counter(bp["topics"][i["topic"]]["domain"] for i in its)
            c = Counter(i["cognitive"] for i in its)
            chk = lambda have, want: f"{have}" + ("" if have == want else f" (≠{want})")
            L.append(f"| {f['id']} | {len(its)} | {chk(d['number'], fm['content']['number'])} | {chk(d['algebra'], fm['content']['algebra'])} | "
                     f"{chk(d['geometry_measurement'], fm['content']['geometry_measurement'])} | {chk(d['data_probability'], fm['content']['data_probability'])} | "
                     f"{chk(c['knowing'], fm['cognitive']['knowing'])} | {chk(c['applying'], fm['cognitive']['applying'])} | {chk(c['reasoning'], fm['cognitive']['reasoning'])} |")
        L.append("")
    if diag_ids:
        topics_cov = Counter(next((i["topic"] for i in items if i["id"] == d), "?") for d in diag_ids)
        missing = [t for t in bp["topics"] if topics_cov[t] == 0]
        L.append("## 6. الاختبار التشخيصي")
        L.append(f"- {len(diag_ids)} بنداً؛ موضوعات غير ممثلة: {', '.join(missing) if missing else 'لا يوجد ✅'}")
        L.append("")

    if unv:
        L.append("## 7. بنود بلا تحقق آلي (تُراجع بالحل المستقل)")
        L.append(", ".join(f"`{u}`" for u in sorted(unv)))
        L.append("")
    if log.errors:
        L.append("## ❌ الأخطاء")
        L += [f"- {e}" for e in log.errors]
        L.append("")
    if log.warnings:
        L.append("## ⚠️ التحذيرات")
        L += [f"- {w}" for w in log.warnings]
    return "\n".join(L) + "\n"


# ============================================================ البرنامج الرئيسي
PSI_DIR = BANK / "psi"
SECURE_DIR = BANK / "secure"
SECURE_SKIP = {"access_codes.yaml"}


def psi_files():
    """psi.yaml (قائمة tasks) + psi/*.yaml (مهمة واحدة لكل ملف)."""
    out = [BANK / "psi.yaml"] if (BANK / "psi.yaml").exists() else []
    return out + (sorted(PSI_DIR.glob("*.yaml")) if PSI_DIR.exists() else [])


def mock_files():
    """secure/mocks.yaml (قائمة forms) + secure/mock_*.yaml (نموذج واحد لكل ملف)."""
    if not SECURE_DIR.exists():
        return []
    return [p for p in sorted(SECURE_DIR.glob("*.yaml")) if p.name not in SECURE_SKIP]


def merge_forms(forms):
    """يدمج أجزاء النموذج الواحد (مثل mock_X1_B1.yaml وmock_X1_B2.yaml) حسب id، وترتَّب الكتل بمعرّفاتها."""
    by = {}
    for f in forms:
        fid = f.get("id")
        if fid in by:
            by[fid]["blocks"] = by[fid].get("blocks", []) + (f.get("blocks", []) or [])
            for k in ("title", "minutes"):
                by[fid].setdefault(k, f.get(k))
        else:
            by[fid] = dict(f)
            by[fid]["blocks"] = list(f.get("blocks", []) or [])
    out = sorted(by.values(), key=lambda f: str(f.get("id")))
    for f in out:
        f["blocks"].sort(key=lambda b: str(b.get("id")))
    return out


def load_tasks(path, log):
    try:
        data = load_yaml(path) or {}
    except yaml.YAMLError as e:
        log.err(path.name, f"خطأ في صياغة YAML: {e}")
        return []
    tasks = data.get("tasks", []) if isinstance(data, dict) and "tasks" in data else ([data] if data else [])
    for t in tasks:
        for it in t.get("items", []) or []:
            it["psi"] = t.get("id")
            it["_file"] = path.name
    return tasks


def load_forms(path, log):
    try:
        data = load_yaml(path) or {}
    except yaml.YAMLError as e:
        log.err(path.name, f"خطأ في صياغة YAML: {e}")
        return []
    if not isinstance(data, dict):
        return []
    forms = data.get("forms", []) if "forms" in data else ([data] if data.get("blocks") else [])
    for f in forms:
        for b in f.get("blocks", []) or []:
            for it in b.get("items", []) or []:
                it["_file"] = path.name
    return forms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="اعتبار البنود الرقمية بلا verify أخطاء")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--only", help="تحقق معزول من ملف بنود واحد (مثل A1.yaml) دون كتابة أي مخرجات — للعمل المتوازي")
    args = ap.parse_args()

    log = Log()
    bp = load_yaml(BANK / "blueprint.yaml")
    gl = load_yaml(BANK / "glossary.yaml")
    lint = Linter(gl, log)

    # --- بنود التدريب
    items = []
    only_kind = "practice"
    if args.only:
        files = sorted(ITEMS_DIR.glob(args.only))
        if not files and PSI_DIR.exists() and sorted(PSI_DIR.glob(args.only)):
            files, only_kind = sorted(PSI_DIR.glob(args.only)), "psi"
        elif not files and SECURE_DIR.exists() and [q for q in SECURE_DIR.glob(args.only) if q.name not in SECURE_SKIP]:
            files, only_kind = [q for q in sorted(SECURE_DIR.glob(args.only)) if q.name not in SECURE_SKIP], "mock"
        if not files:
            print(f"❌ لا يوجد ملف يطابق {args.only} في items/ أو psi/ أو secure/")
            sys.exit(1)
    else:
        files = sorted(ITEMS_DIR.glob("*.yaml"))
    if only_kind != "practice":
        files_special, files = files, []
    for p in files:
        try:
            data = load_yaml(p) or []
        except yaml.YAMLError as e:
            log.err(p.name, f"خطأ في صياغة YAML: {e}")
            continue
        if isinstance(data, dict):
            data = data.get("items", [])
        for it in data:
            it["_file"] = p.name
            items.append(it)
    if args.only:
        # وضع معزول: تحقق فقط من الملف المطلوب، بلا مخرجات
        extra_line = ""
        if only_kind == "psi":
            tasks = [t for p in files_special for t in load_tasks(p, log)]
            for t in tasks:
                lint.text(f"{t.get('id')}:intro", t.get("intro"))
                for k in ("id", "title", "intro"):
                    if not t.get(k):
                        log.err(str(t.get("id")), f"حقل المهمة مفقود: {k}")
                if t.get("figure"):
                    try:
                        figures.render(t["figure"])
                    except Exception as e:  # noqa: BLE001
                        log.err(f"{t.get('id')}:figure", f"تعذّر رسم الشكل: {e}")
                items += t.get("items", []) or []
            extra_line = f"  مهام: {len(tasks)} | بنود لكل مهمة: {[len(t.get('items', []) or []) for t in tasks]}"
        elif only_kind == "mock":
            forms = [f for p in files_special for f in load_forms(p, log)]
            fmb = bp["forms"]["mock"]
            for f in forms:
                its = [i for b in f.get("blocks", []) for i in b.get("items", [])]
                items += its
                dom = Counter(bp["topics"].get(i.get("topic"), {}).get("domain") for i in its)
                extra_line += (f"  نموذج {f.get('id')}: كتل {[len(b.get('items', [])) for b in f.get('blocks', [])]} | مجالات {dict(dom)}"
                               f" (هدف النموذج الكامل {fmb['content']}) | معرفي {dict(Counter(i.get('cognitive') for i in its))} (هدف النموذج الكامل {fmb['cognitive']})" + chr(10))
            extra_line = extra_line.rstrip(chr(10))
        seen = {}
        nver = 0
        for it in items:
            validate_item(it, bp, lint, log, only_kind)
            if it.get("id") in seen:
                log.err(it.get("id"), "معرّف مكرر")
            seen[it.get("id")] = 1
            v = verify_item(it, log)
            nver += v is True
            if v is None and it.get("format") in ("numeric", "multi_numeric"):
                log.warn(it.get("id"), "بند رقمي بلا verify")
            render_figures(it, log)
        c = Counter((i.get("topic"), i.get("cognitive"), i.get("difficulty")) for i in items)
        cog = Counter(i.get("cognitive") for i in items)
        dif = Counter(i.get("difficulty") for i in items)
        fm = Counter(bp["formats"].get(i.get("format"), {}).get("group") for i in items)
        keys = Counter(i.get("key") for i in items if i.get("format") == "mc")
        print(f"[{args.only}] بنود: {len(items)} | تحقق آلي: {nver} | أخطاء: {len(log.errors)} | تحذيرات: {len(log.warnings)}")
        print(f"  معرفي: {dict(cog)} | صعوبة: {dict(dif)} | أنواع: {dict(fm)} | مفاتيح mc: {dict(keys)}")
        if extra_line:
            print(extra_line)
        for e in log.errors:
            print("  ❌", e)
        for w_ in log.warnings:
            print("  ⚠️", w_)
        sys.exit(1 if log.errors else 0)
    # --- مهام PSI
    psi_tasks = [t for p in psi_files() for t in load_tasks(p, log)]
    anchors_path = BANK / "anchors.json"
    anchors = json.loads(anchors_path.read_text(encoding="utf-8")) if anchors_path.exists() else {}
    # --- الاختبارات المحمية
    mocks = merge_forms([f for p in mock_files() for f in load_forms(p, log)])
    # --- النماذج (التشخيصي)
    forms_path = BANK / "forms.yaml"
    diag_ids = []
    if forms_path.exists():
        fdata = load_yaml(forms_path) or {}
        diag_ids = (fdata.get("diagnostic") or {}).get("items", []) or []

    # --- التحقق
    seen = {}
    verified_map = {}
    public_items, public_psi, secure_forms = [], [], []

    def process(it, kind):
        validate_item(it, bp, lint, log, kind)
        iid = it.get("id")
        if iid in seen:
            log.err(iid, f"معرّف مكرر (أيضاً في {seen[iid]})")
        seen[iid] = it.get("_file", kind)
        v = verify_item(it, log)
        verified_map[iid] = v
        if v is None and it.get("format") in ("numeric", "multi_numeric") and args.strict:
            log.err(iid, "بند رقمي بلا verify (وضع strict)")
        figs = render_figures(it, log)
        pub = to_public(it, bp, v, figs)
        if anchors.get(iid):
            # نماذج إجابات للتدريب على التصحيح (gemini_anchors.py): تُفحص نصوصها بالمدقق اللغوي نفسه
            for k, a in enumerate(anchors[iid], 1):
                lint.text(f"{iid}:anchor{k}", a.get("text"))
                lint.text(f"{iid}:anchor{k}:reason", a.get("reason"))
                lint.text(f"{iid}:anchor{k}:note", a.get("note"))
            pub["anchors"] = [{x: a.get(x) for x in ("level", "text", "code", "reason", "note") if a.get(x)} for a in anchors[iid]]
        return pub

    for it in items:
        public_items.append(process(it, "practice"))
    for t in psi_tasks:
        lint.text(f"{t['id']}:intro", t.get("intro"))
        pt = {k: t[k] for k in ("id", "title", "intro", "context", "table") if k in t}
        if t.get("figure"):
            pt["figure_svg"] = figures.render(t["figure"])
        pt["items"] = [process(it, "psi") for it in t.get("items", [])]
        public_psi.append(pt)
    for f in mocks:
        sf = {"id": f["id"], "title": f.get("title", f["id"]), "minutes": f.get("minutes", 45), "blocks": []}
        for b in f["blocks"]:
            sf["blocks"].append({"id": b["id"], "items": [process(it, "mock") for it in b["items"]]})
        secure_forms.append(sf)
    ids = {i["id"] for i in public_items}
    for d in diag_ids:
        if d not in ids:
            log.err("forms.yaml", f"بند التشخيصي غير موجود في البنك: {d}")

    # --- الإخراج
    BUILD.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    meta = {
        "title": bp["meta"]["title_ar"], "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "counts": {"practice": len(public_items), "psi_tasks": len(public_psi), "mock_forms": len(secure_forms)},
    }
    bank_json = {
        "meta": meta, "domains": bp["domains"], "cognitive_domains": bp["cognitive_domains"],
        "benchmarks": bp["benchmarks"], "difficulty_levels": bp["difficulty_levels"], "formats": bp["formats"],
        "contexts": bp["contexts"], "topics": bp["topics"], "forms": {"diagnostic": {**bp["forms"]["diagnostic"], "count": bp["forms"]["diagnostic"].get("items"), "items": diag_ids}, "mock": bp["forms"]["mock"]},
        "items": public_items, "psi": public_psi,
    }
    (BUILD / "bank.json").write_text(json.dumps(bank_json, ensure_ascii=False), encoding="utf-8")
    (BUILD / "secure.json").write_text(json.dumps({"forms": secure_forms}, ensure_ascii=False), encoding="utf-8")

    with open(BANK / "bank.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "topic", "domain", "cognitive", "area", "difficulty", "benchmark", "format", "context", "time_sec", "points", "verified", "psi", "stem", "key"])
        for o in public_items + [i for t in public_psi for i in t["items"]]:
            key = o.get("key")
            if o["format"] == "numeric":
                key = o.get("answer", {}).get("value")
            elif o["format"] == "multi_numeric":
                key = "; ".join(f"{plain(x['label'])}={x['value']}" for x in o.get("fields", []))
            elif isinstance(key, (dict, list)):
                key = json.dumps(key, ensure_ascii=False)
            w.writerow([o["id"], o["topic"], o["domain"], o["cognitive"], o["area"], o["difficulty"], o["benchmark"], o["format"],
                        o["context"], o["time"], o["points"], o["verified"], o.get("psi", ""), plain(o["stem"]), key])

    rep = coverage_report(bp, [i for i in items], psi_tasks, mocks, diag_ids, log, verified_map)
    (REPORTS / "coverage_report.md").write_text(rep, encoding="utf-8")

    if not args.quiet:
        print(f"بنود التدريب: {len(public_items)} | PSI: {len(public_psi)} مهمة | نماذج محمية: {len(secure_forms)} | تشخيصي: {len(diag_ids)}")
        print(f"تحقق آلي ناجح: {sum(1 for v in verified_map.values() if v is True)} | بلا تحقق: {sum(1 for v in verified_map.values() if v is None)}")
        print(f"أخطاء: {len(log.errors)} | تحذيرات: {len(log.warnings)}")
        for e in log.errors:
            print("  ❌", e)
        for w_ in log.warnings[:60]:
            print("  ⚠️", w_)
        if len(log.warnings) > 60:
            print(f"  … و{len(log.warnings) - 60} تحذيراً آخر (انظر reports/coverage_report.md)")
    sys.exit(1 if log.errors else 0)


if __name__ == "__main__":
    main()
