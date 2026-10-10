# -*- coding: utf-8 -*-
"""
gemini_lessons.py — خطط الدروس الجسرية الست (القسم 5.3 من تحليل الفجوات) بنموذج Gemini عبر agy.

كل درس يحيل إلى بنود تدريب حقيقية من البنك بمعرّفاتها؛ ويُتحقق آلياً من المعرّفات وخلو النص من LaTeX
والكسور بالشرطة. المخرج: 01_المصادر_والإطار/08_خطط_الدروس_الجسرية.md (دليل للمعلم في المنصة).
"""
import concurrent.futures as cf
import pathlib
import re
import subprocess
import sys
import tempfile

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gemini_review import AGY, MODEL  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
BANK = ROOT / "02_بنك_الأسئلة"
OUT = ROOT / "01_المصادر_والإطار" / "08_خطط_الدروس_الجسرية.md"
RAW = ROOT / "05_الاعتماد" / "04_مطابقة_منهج_قطر" / "خطط_الدروس_الجسرية_raw"
DIFF_AR = {"foundation": "تأسيسي", "easy": "سهل", "medium": "متوسط", "hard": "صعب"}
RANK = {"foundation": 0, "easy": 1, "medium": 2, "hard": 3}

LESSONS = [
    dict(n=1, title="الدوال والأنماط غير الخطية", replaces="الدرس 3-3 المحذوف (مقارنة الدوال الخطية وغير الخطية)", sessions=2, when="يناير",
         topics=["A6", "A5"], kw=None,
         focus="التمييز بين العلاقات الخطية وغير الخطية من الجداول (الفروق المتتالية) والرسوم والمعادلات، والأنماط التربيعية والتضاعفية، وقراءة المنحنيات وفترات التزايد والتناقص"),
    dict(n=2, title="نظرية فيثاغورس وتطبيقاتها والمسافة في المستوى الإحداثي", replaces="الدرسان 6-3 و6-4 المحذوفان، ووقوع الوحدة 6 في نافذة الاختبار", sessions=3, when="مارس",
         topics=["G2", "G1"], kw="فيثاغورس|الوتر|المائل|قائم الزاوية|قائمة|المسافة|القطر|سلم|سلّم|ممر",
         focus="إيجاد الوتر وضلع القائمة، وعكس النظرية، والتطبيقات الحياتية، والمسافة بين نقطتين في المستوى الإحداثي"),
    dict(n=3, title="حجم الأسطوانة والمخروط والكرة والمساحة السطحية", replaces="وقوع الوحدة 7 بعد موعد الاختبار غالباً", sessions=3, when="مارس",
         topics=["G4"], kw=None,
         focus="حجم المنشور والأسطوانة والمخروط والكرة، والمساحة السطحية من الشبكة، وأثر مضاعفة الأبعاد، والتحويل بين الوحدات"),
    dict(n=4, title="مخطط الانتشار والترابط والتنبؤ والجداول التكرارية المزدوجة", replaces="الدرسان 8-4 و8-5 المحذوفان، ووقوع الوحدة 8 بعد الاختبار", sessions=2, when="مارس",
         topics=["D1", "D2"], kw="انتشار|ترابط|الاتجاه|مزدوج|التنبؤ|تنبأ",
         focus="تمثيل البيانات ذات المتغيرين بمخطط الانتشار، ووصف الترابط، والتنبؤ بخط الاتجاه وحدوده، وقراءة الجداول التكرارية المزدوجة"),
    dict(n=5, title="الأعمدة المجمّعة والمكدّسة والإنفوجرافيك", replaces="تمثيلات يقيسها TIMSS ولا يغطيها المنهج صراحة", sessions=1, when="ديسمبر",
         topics=["D1", "D2"], kw="مجمّع|مجمع|مكدّس|مكدس|إنفوجرافيك|الأعمدة|القطاعات|الرسمين|رسمان",
         focus="قراءة الأعمدة المجمّعة والمكدّسة والقطاعات الدائرية والإنفوجرافيك، والدمج بين تمثيلين، ونقد الرسوم المضللة"),
    dict(n=6, title="مراجعة الإحصاء والاحتمال من الصفين السادس والسابع", replaces="البعد الزمني عن دراسة هذه الموضوعات", sessions=2, when="نوفمبر وديسمبر",
         topics=["D3", "D4"], kw=None,
         focus="المتوسط الحسابي والوسيط والمنوال والمدى وأثر القيم المتطرفة، والاحتمال النظري والتجريبي وفضاء العينة"),
]

PROMPT = """You are an expert mathematics teacher educator in Qatar. Write a complete BRIDGING LESSON PLAN in Arabic
(Markdown) for Grade 8 mathematics teachers preparing students for TIMSS 2027. Do not use any tools or files.
The lesson fills a curriculum gap: {replaces}.
Lesson {n}: {title}. Sessions: {sessions} x 45 minutes. Suggested timing: {when}. TIMSS topics: {topics}.
Focus: {focus}.

Use exactly this structure:
## الدرس {n}: {title}
**يعوّض:** ... · **عدد الحصص:** {sessions} · **التوقيت المقترح:** {when} · **موضوعات TIMSS:** {topics}
### الأهداف
(3 to 5 measurable objectives)
### المتطلبات السابقة
### الحصة 1 (45 دقيقة)
(repeat for each session) with these parts, each with its minutes:
- **تمهيد استرجاع:** 2-3 quick questions with their answers.
- **العرض المباشر:** one fully worked example, step by step.
- **التدريب الموجّه:** what the teacher and students do together.
- **التدريب المستقل:** 3-5 items from the ITEM LIST below, cited by their exact IDs (e.g. M8-G2-005), with one line on why each.
- **بطاقة الخروج:** 2-3 short questions with their answers.
### دعم الطلاب دون المستوى المنخفض والتوسع للمتقدمين
### مفاهيم خاطئة شائعة وطريقة معالجتها
### الواجب عبر المنصة

Rules:
- Arabic fusha, direct and concise; at most about 1100 words.
- Western digits 0-9 only. Write mathematics as plain text, never LaTeX and never the $ sign:
  for example a² + b² = c², √49 = 7, V = π × r² × h, 2 × 3 + 4.
- NEVER write a fraction with a slash: write it in words (ثلاثة أخماس) or as a decimal.
- Use Qatar textbook terms: الإزاحة، مخطط الانتشار، المقطع y، المتوسط الحسابي، الوسيط، الحسم، نظرية فيثاغورس، المساحة السطحية.
- Cite ONLY item IDs from the list below.
- Return only the Markdown, without code fences.

ITEM LIST (practice items in the bank: ID | difficulty | format | stem):
{items}
"""


def pick_items(lesson, items):
    rx = re.compile(lesson["kw"]) if lesson["kw"] else None
    sel = [it for it in items if it["topic"] in lesson["topics"] and (rx is None or rx.search(it["stem"]))]
    sel.sort(key=lambda i: (RANK[i["difficulty"]], i["id"]))
    return sel[:18]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if OUT.exists() and "--force" not in sys.argv:
        # الملف المجمّع روجع رياضياً وصُحّح يدوياً بعد التوليد؛ إعادة التجميع من المسودات الخام تمحو التصحيحات
        print("الخطط موجودة ومراجَعة:", OUT, "\nلإعادة التجميع من المسودات الخام (تضيع التصحيحات): --force")
        return
    items =[it for p in sorted((BANK / "items").glob("*.yaml")) for it in (yaml.safe_load(p.read_text(encoding="utf-8")) or [])]
    RAW.mkdir(parents=True, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix="agy_ws_")

    def one(lesson):
        sel = pick_items(lesson, items)
        lst = "\n".join(f"{i['id']} | {DIFF_AR[i['difficulty']]} | {i['format']} | {re.sub(chr(10), ' ', i['stem'])[:140]}" for i in sel)
        prompt = PROMPT.format(items=lst, topics="، ".join(lesson["topics"]), **{k: v for k, v in lesson.items() if k != "topics"})
        raw = RAW / f"lesson_{lesson['n']}.md"
        if not raw.exists():
            r = subprocess.run([str(AGY), "-p", prompt, "--model", MODEL, "--output-format", "text", "--print-timeout", "900s"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1000, cwd=workdir)
            txt = re.sub(r"^```(?:markdown|md)?\s*|\s*```\s*$", "", r.stdout.strip())
            raw.write_text(txt, encoding="utf-8")
        txt = raw.read_text(encoding="utf-8")
        ids = set(re.findall(r"M8-[A-Z]\d-\d{3}", txt))
        allowed = {i["id"] for i in sel}
        problems = []
        if ids - allowed:
            problems.append("معرّفات خارج القائمة: " + ", ".join(sorted(ids - allowed)))
        if "$" in txt or "\\" in txt:
            problems.append("رموز LaTeX")
        if re.search(r"(?<![\d.])\d{1,3}\s*/\s*\d{1,3}(?![\d.])", txt):
            problems.append("كسر بالشرطة")
        return lesson, txt, len(ids & allowed), problems

    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        results = list(ex.map(one, LESSONS))
    head = ["# خطط الدروس الجسرية قبل اختبار TIMSS 2027", "",
            "تسد هذه الدروس الست فجوات توقيت منهج الصف الثامن والدروس المحذوفة من الخطة الفصلية، كما في القسم 5.3 من «تحليل نتائج قطر وفجوات المنهج». "
            "كل درس يحيل إلى بنود تدريب من البنك بمعرّفاتها، فيفتحها المعلم من «تصفح البنك» في وضع المعلم، ويتدرب عليها الطلاب من «التدريب حسب الموضوع».", "",
            "| الدرس | يعوّض | الحصص | التوقيت |", "|---|---|---|---|"]
    head += [f"| {l['n']}. {l['title']} | {l['replaces']} | {l['sessions']} | {l['when']} |" for l in LESSONS]
    head += ["", "> مسودات أعدّها نموذج Gemini 3.1 Pro وتحقق منها النظام آلياً (معرّفات البنود، والترميز)، وتحتاج اعتماد رئيس قسم الرياضيات (المهمة 04-03).", ""]
    body = []
    for lesson, txt, n_ids, problems in results:
        body += [txt.strip(), ""]
        print(f"الدرس {lesson['n']}: {len(txt.split())} كلمة | بنود مستشهد بها: {n_ids} | مشكلات: {problems or 'لا'}", flush=True)
    OUT.write_text("\n".join(head + body) + "\n", encoding="utf-8")
    print("كُتب:", OUT)


if __name__ == "__main__":
    main()
