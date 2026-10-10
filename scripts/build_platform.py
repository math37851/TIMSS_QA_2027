# -*- coding: utf-8 -*-
"""
build_platform.py — يبني المنصة في ملف HTML واحد مستقل يعمل دون إنترنت.

يدمج: القالب + التنسيق + KaTeX (بخطوطه مضمّنة) + marked + بيانات البنك + الوثائق + الاختبارات المشفّرة.
الاختبارات التجريبية تُشفَّر بـ AES-256-GCM بمفتاح مشتق من رمز الدخول (PBKDF2-SHA256)،
ورموزها تُحفظ في 02_بنك_الأسئلة/secure/access_codes.yaml (ملف المعلم — لا يوزَّع).

الاستعمال:
  python build_platform.py                # يشغّل build_bank.py ثم يبني الملف الواحد
  python build_platform.py --no-bank      # يبني من build/bank.json الحالي دون إعادة بناء البنك
  python build_platform.py --preview      # نسخة معاينة بلا اختبارات محمية (للمشاركة)
"""

import argparse
import base64
import datetime as dt
import json
import os
import pathlib
import re
import secrets
import subprocess
import sys

import yaml
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
BANK = ROOT / "02_بنك_الأسئلة"
BUILD = BANK / "build"
PLAT = ROOT / "03_منصة_التدريب_eTIMSS"
SRC = PLAT / "src"
DOCS_DIR = ROOT / "01_المصادر_والإطار"
INPUTS = ROOT / "00_المدخلات"
OUT = PLAT / "منصة_TIMSS_رياضيات_الصف_الثامن.html"
OUT_PREVIEW = BUILD / "preview_platform.html"
CODES = BANK / "secure" / "access_codes.yaml"
ITER = 150_000

# الوثائق المضمّنة في المنصة: (الملف، المعرّف، الجمهور، الوصف)
DOCS = [
    ("05_دليل_الطالب_للاستعداد.md", "student-guide", "student", "كيف تستعد لاختبار TIMSS"),
    ("06_دليل_تشغيل_المنصة_للمعلم.md", "teacher-guide", "teacher", "طريقة استعمال المنصة وإدارة الاختبارات"),
    ("03_الإطار_التدريبي_والبرنامج_الزمني.md", "framework", "teacher", "الأطر المبنية على الأدلة والبرنامج الزمني"),
    ("02_تحليل_نتائج_قطر_وفجوات_المنهج.md", "analysis", "teacher", "أداء قطر في 2023 وفجوات المنهج"),
    ("01_مكتبة_المصادر.md", "sources", "teacher", "المصادر الرسمية والمفتوحة وبنوك الأسئلة"),
    ("04_مواصفات_كتابة_أسئلة_TIMSS.md", "spec", "teacher", "دليل كتابة بنود على نمط TIMSS"),
    ("08_خطط_الدروس_الجسرية.md", "bridging", "teacher", "ست خطط لدروس جسرية قبل الاختبار"),
]


def read(p):
    return pathlib.Path(p).read_text(encoding="utf-8")


def js_safe(obj):
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s.replace("</", "<\\/").replace("<!--", "<\\!--").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def inline_katex_css():
    kdir = SRC / "vendor" / "katex"
    css = read(kdir / "katex.min.css")

    def repl(m):
        name = m.group(1)
        f = kdir / "fonts" / f"{name}.woff2"
        if not f.exists():
            return m.group(0)
        b64 = base64.b64encode(f.read_bytes()).decode()
        return f'src:url(data:font/woff2;base64,{b64}) format("woff2")'

    css2 = re.sub(r'src:url\(fonts/(KaTeX_[A-Za-z0-9_-]+)\.woff2\) format\("woff2"\)(?:,url\([^)]*\) format\("[^"]*"\))*', repl, css)
    return css2


def load_codes(form_ids):
    codes = {}
    if CODES.exists():
        codes = yaml.safe_load(read(CODES)) or {}
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # بلا حروف ملتبسة (0/O، 1/I)
    changed = False
    for fid in form_ids:
        if not codes.get(fid):
            codes[fid] = "".join(secrets.choice(alphabet) for _ in range(6))
            changed = True
    if changed:
        CODES.parent.mkdir(parents=True, exist_ok=True)
        body = "\n".join(f"{k}: {v}" for k, v in codes.items())
        CODES.write_text(
            "# رموز دخول الاختبارات التجريبية — ملف المعلم فقط، لا يوزَّع على الطلاب\n"
            "# لتغيير رمز: عدّله هنا ثم أعد البناء بالأمر: python scripts/build_platform.py\n" + body + "\n",
            encoding="utf-8",
        )
    return codes


def encrypt_form(form, code):
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(code.strip().upper().encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, json.dumps(form, ensure_ascii=False).encode("utf-8"), None)
    n = sum(len(b["items"]) for b in form["blocks"])
    return {"id": form["id"], "title": form.get("title", form["id"]), "minutes": form.get("minutes", 45), "n": n,
            "iter": ITER, "salt": base64.b64encode(salt).decode(), "iv": base64.b64encode(iv).decode(), "ct": base64.b64encode(ct).decode()}


def brand_info():
    info = {}
    card = INPUTS / "00_بطاقة_المعلومات.md"
    if card.exists():
        m = re.search(r"اسم المدرسة أو الجهة كما سيظهر في المنصة:\*\*\s*(.+)", read(card))
        if m and m.group(1).strip() not in ("...", "…", ""):
            info["school"] = m.group(1).strip()
    logos = sorted((INPUTS / "07_الهوية").glob("*.png")) + sorted((INPUTS / "07_الهوية").glob("*.jpg"))
    if logos:
        p = logos[0]
        if p.stat().st_size <= 600_000:
            mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
            info["logo"] = f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-bank", action="store_true")
    ap.add_argument("--preview", action="store_true", help="نسخة بلا اختبارات محمية")
    args = ap.parse_args()

    if not args.no_bank:
        r = subprocess.run([sys.executable, str(SCRIPTS / "build_bank.py"), "--quiet"], cwd=str(SCRIPTS))
        if r.returncode != 0:
            print("❌ فشل build_bank.py — أصلح الأخطاء أولاً (شغّله دون --quiet لعرضها).")
            sys.exit(1)

    bank = json.loads(read(BUILD / "bank.json"))
    secure = json.loads(read(BUILD / "secure.json")) if (BUILD / "secure.json").exists() else {"forms": []}

    enc_forms = []
    if not args.preview and secure["forms"]:
        codes = load_codes([f["id"] for f in secure["forms"]])
        enc_forms = [encrypt_form(f, codes[f["id"]]) for f in secure["forms"]]

    docs = []
    for fname, did, aud, desc in DOCS:
        p = DOCS_DIR / fname
        if p.exists():
            md = read(p)
            m = re.search(r"^#\s+(.+)$", md, re.M)
            title = re.sub(r"[#*`]", "", m.group(1)).strip() if m else did
            docs.append({"id": did, "title": title, "audience": aud, "desc": desc, "md": md})

    build_info = {"built": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "brand": brand_info(), "preview": bool(args.preview)}

    tpl = read(SRC / "index.html")
    style = read(SRC / "styles.css")
    kcss = inline_katex_css()
    vendor = read(SRC / "vendor" / "katex" / "katex.min.js") + "\n" + read(SRC / "vendor" / "marked" / "marked.min.js")
    app = "\n".join(read(p) for p in sorted((SRC / "js").glob("*.js")))
    data = (f"window.BANK={js_safe(bank)};\n"
            f"window.SECURE={js_safe({'forms': enc_forms})};\n"
            f"window.DOCS={js_safe(docs)};\n"
            f"window.BUILD_INFO={js_safe(build_info)};")

    html = (tpl.replace("/*{{KATEX_CSS}}*/", kcss)
               .replace("/*{{STYLE}}*/", style)
               .replace("/*{{VENDOR}}*/", vendor.replace("</script", "<\\/script"))
               .replace("/*{{DATA}}*/", data)
               .replace("/*{{APP}}*/", app.replace("</script", "<\\/script")))
    out = OUT_PREVIEW if args.preview else OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    mb = out.stat().st_size / 1e6
    print(f"✅ {out.name} — {mb:.2f} MB | بنود: {len(bank['items'])} | PSI: {len(bank['psi'])} | اختبارات مشفّرة: {len(enc_forms)} | وثائق: {len(docs)}")
    if enc_forms:
        print(f"🔑 رموز الاختبارات في: {CODES.relative_to(ROOT)} (لا توزّع هذا الملف)")


if __name__ == "__main__":
    main()
