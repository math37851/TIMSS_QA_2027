---
name: timss-g8-math-item-generator
description: >
  Author original Arabic TIMSS 2027 grade-8 MATH items for the Qatar question bank in D:\TIMSS 2027
  (YAML in 02_بنك_الأسئلة/items/), matching the project's blueprint, notation rules and schema, then
  validate with scripts/build_bank.py. Use for any request to write/add/fix bank items, PSI tasks,
  mock-test items, or batches B2–B6 ("اكتب بنود الجبر", "أكمل دفعة الهندسة", "add items for A5").
---

# مولّد بنود TIMSS 2027 — رياضيات الصف الثامن (قطر)

## 1. سير العمل (التزم به حرفياً)
1. اقرأ فقط: هذا الملف + `02_بنك_الأسئلة/blueprint.yaml` (عند الحاجة) + ملف الموضوع الهدف في `items/`.
   لا تقرأ ملفات البنود الأخرى كاملة؛ استعمل `grep -n "id: M8-A5" ...` لمعرفة المعرّفات الموجودة.
2. اكتب البنود الجديدة **بإلحاقها** في ملف الموضوع (لا تعدّل البنود الموجودة إلا إذا طُلب).
3. تحقق **معزول** من ملفك فقط (آمن مع العمل المتوازي):
   `export PYTHONIOENCODING=utf-8; cd "/d/TIMSS 2027/scripts" && python build_bank.py --only A1.yaml`
   أصلح **كل** الأخطاء والتحذيرات حتى يصبح الناتج: أخطاء 0 · تحذيرات 0 · تحقق آلي = عدد البنود. السطر الثاني من الناتج يعرض توزيعك (معرفي/صعوبة/أنواع/مفاتيح mc) فطابقه مع التكليف.
4. أبلغ باختصار: المعرّفات المضافة، وتوزيعها (معرفي/صعوبة/نوع/سياق)، وأي بند احتاج حكماً تربوياً.

ملفات البنود في `02_بنك_الأسئلة/items/`: الأعداد مكتملة في `number_integers` (N1,N2) · `number_fractions_decimals` (N3,N4) · `number_ratios_percents` (N5,N6).
بقية الموضوعات: **ملف لكل موضوع** `A1.yaml … A6.yaml` · `G1.yaml … G4.yaml` · `D1.yaml … D4.yaml` (ابدأ البنود بعد سطور التعليق في رأس الملف).
مهام PSI: **ملف لكل مهمة** `psi/PSI1.yaml` … `psi/PSI6.yaml` (معرّفات البنود `M8-PSI1-01` …)، والاختبارات المحمية: **ملف لكل كتلة** `secure/mock_X1_B1.yaml` و`secure/mock_X1_B2.yaml` (يُدمجان آلياً بالـ `id: X1`؛ معرّفات البنود `M8-X1-01` … `M8-X1-16` للكتلة الأولى و`M8-X1-17` … `M8-X1-32` للثانية). التحقق المعزول بالأمر نفسه: `--only PSI1.yaml` أو `--only mock_X1_B1.yaml`.

### منهج قطر للصف الثامن (للحقل `qatar_link` والتوقيت) — من الخطتين الفصليتين 2026/2027
- ف1: **الوحدة 1** الأعداد الحقيقية (1-1 النسبية كعشرية · 1-2 غير النسبية · 1-3 مقارنة وترتيب · 1-4 الجذور التربيعية والتكعيبية · 1-5 حل معادلات بالجذور · 1-6/1-7 خواص الأسس الصحيحة · 1-9 الصيغة العلمية) ·
  **الوحدة 2** المعادلات الخطية (2-1 تجميع الحدود المتشابهة · 2-2 متغيرات في الطرفين · 2-3 متعددة الخطوات · 2-4 لا حل أو حلول لا نهائية · 2-6 التناسب وميل المستقيم · 2-7 $y = mx$ · 2-8 المقطع $y$ · 2-9 $y = mx + b$) ·
  **الوحدة 3** الدوال (3-1 العلاقات والدوال · 3-5 فترات التزايد والتناقص).
- ف2 (يناير–مارس، قبل الاختبار): **الوحدة 4** أنظمة المعادلات (4-1 عدد الحلول · 4-2 بيانياً · 4-3 بالتعويض · 4-4 بالحذف) ·
  **الوحدة 5** التطابق والتشابه (5-1 **الإزاحة** · 5-2 الانعكاس · 5-3 الدوران · 5-4 تركيب التحويلات · 5-5 المتطابقة · 5-6 التمدد · 5-7 المتشابهة · 5-8 الزوايا والمستقيمات والقواطع · 5-9 زوايا المثلث الداخلية والخارجية).
- ف2 (أبريل–مايو، **غالباً بعد موعد الاختبار** → بنود جسرية): **الوحدة 6** فيثاغورس وعكسها · **الوحدة 7** المساحة السطحية، حجم الأسطوانة والمخروط والكرة · **الوحدة 8** مخططات الانتشار، الترابط الخطي، النماذج الخطية.
- دروس **محذوفة** من الخطة (فجوات TIMSS): 3-3 مقارنة الدوال الخطية وغير الخطية (A6) · 3-2/3-4 تمثيلات الدوال ونمذجتها · 6-3/6-4 تطبيق فيثاغورس والمسافة في المستوى · 8-4/8-5 الجداول التكرارية المزدوجة.
- الصف السابع: الأعداد الصحيحة والنسبية (و1)، علاقات التناسب (و2)، النسب المئوية (و3)، ثم في ف2 المقادير والمعادلات والمتباينات والاحتمال والهندسة (الزوايا، الدائرة، المساحة والحجم). الصف السادس: الإحصاء (المتوسط، الوسيط، مخطط النقاط، المدرج التكراري).

## 2. الأهداف العددية
- كل موضوع N/A = 16 بنداً: معرفة 5 · تطبيق 6 · استدلال 5 | تأسيسي 2 · سهل 5 · متوسط 5 · صعب 4.
- كل موضوع G/D = 21 بنداً: معرفة 6 · تطبيق 9 · استدلال 6 | تأسيسي 2 · سهل 6 · متوسط 8 · صعب 5.
- الأنواع على مستوى البنك: mc 45% · رقمي 20% · سحب 12% · رسم شبكة 8% (أغلبه في G1، G3، A5، A6، D1) · تبرير/مفتوح 15%. في كل موضوع: بندان مفتوحان على الأقل و5 بنود غير mc على الأقل.
- السياق: ≈85% في سياق (نصفه قطري)، ≈15% مجرد. الوسوم المسموحة: `context: qatar | real | pure`.
- المستويات المعرفية الفرعية (`area`): knowing → recall/identify/order/compute · applying → formulate/implement/represent · reasoning → analyze/integrate/generalize/justify.
- `difficulty: foundation|easy|medium|hard` (نسب صواب مستهدفة 80/70/55/40%) · `benchmark: low|intermediate|high|advanced`.
- المعرّف: `M8-<topic>-<NNN>` مثل `M8-A5-007` (تسلسل بعد آخر رقم موجود).

## 3. قواعد اللغة والرموز (يرفض المدقق المخالفات)
- عربية فصحى موجزة بحمل قرائي منخفض. أسماء عربية للشخصيات.
- **كل** تعبير رياضي، وكل عدد سالب، وكل متغير لاتيني داخل `$…$`: `$-6$` · `$x + 3 = 7$` · `$y = 2x - 1$`.
- الأرقام 0–9 فقط (ممنوع ٠١٢٣ و٪ و٫). البدائل A, B, C, D (ممنوع أ/ب/ج/د).
- **لا حروف عربية داخل `$…$` إطلاقاً** (حتى داخل `\text{}`). الوحدات: `$5\,\text{cm}$` ، `$12\,\text{m}^2$` ، `$22\,^\circ\text{C}$` ، `$25\%$` ، `$80\,\text{km/h}$`.
- العملة كلمة عربية خارج الرياضيات: «120 ريالاً». الأعداد الموجبة المفردة يجوز كتابتها خارج `$` («3 كتب»).
- مصطلحات كتب قطر المؤكدة: الأعداد النسبية/غير النسبية/الحقيقية، معدل الوحدة، النسب المتكافئة، ثابت التناسب، التمثيل البياني، التغير المئوي، هامش الربح، **الحسم** (لا الخصم)، الفائدة البسيطة، **استعمال**، الصيغة العلمية، تجميع الحدود المتشابهة، **ميل المستقيم**، **المقطع $y$** (لا «المقطع الصادي»)، **$y = mx + b$** (لا $c$)، أنظمة المعادلات (بيانياً/بالتعويض/بالحذف)، العلاقات والدوال، فترات التزايد والتناقص، **الإزاحة** (لا «الانسحاب»)، الانعكاس، الدوران، تركيب التحويلات، التمدد، الأشكال المتطابقة/المتشابهة، الزوايا والمستقيمات والقواطع، نظرية فيثاغورس، المساحة السطحية، الأسطوانة، المخروط، الكرة، **مخطط الانتشار**، الترابط الخطي. مؤقت: المتوسط الحسابي، الوسيط، المدرج التكراري، مخطط النقاط. القاموس الكامل: `02_بنك_الأسئلة/glossary.yaml`.
- سياقات قطرية مقترحة: مترو الدوحة، لوسيل، سوق واقف، الوكرة، الخور، كورنيش الدوحة، أسباير، كتارا، متحف قطر الوطني، الذخيرة وأشجار القرم، الكشتة، اليوم الوطني (18 ديسمبر)، رمضان والإفطار، التمور، مطار حمد، تحلية المياه، الطاقة الشمسية (الخرسعة)، كرة القدم المدرسية. اكتب «(بيانات افتراضية)» إذا كانت الأرقام غير حقيقية.

## 4. YAML — قواعد الكتابة
- النصوص الطويلة بكتلة `|`. أي نص فيه `\` داخل سطر واحد: **علامات تنصيص مفردة** `'...'` (لا مزدوجة). لتضمين `'` داخل مفردة اكتبها `''`.
- حقول إلزامية: `id, topic, cognitive, area, difficulty, benchmark, format, context, time (ثوانٍ 15–900), stem, solution`.
- موصى بها دائماً: `remediation`, `misconceptions` (قائمة)، `qatar_link`, `verify`، و`hint` اختياري.
- اختياري: `table: {headers: [...], rows: [[...]], row_headers: true}` ، `figure: {type: ...}` (أو قائمة رسوم).

### الأنواع (`format`) وحقولها
```yaml
# اختيار من متعدد — 4 بدائل، كل مشتّت = مفهوم خاطئ موثّق في rationale
format: mc
options: ['$16$', '$28$', '$-28$', '$-16$']      # أو - figure: {...} لبدائل مرسومة
option_values: [16, 28, -28, -16]                 # للتحقق الرقمي (أو "3/4"، "2**7"، "sqrt(34)")
key: B
verify: "22 - (-6)"                               # يجب أن يساوي option_values[key] ولا يساوي غيره
rationale: {A: "...", C: "...", D: "..."}
# إذا كانت البدائل غير رقمية: verify شرط منطقي يعيد True (مثل "Rational(2,3) > Rational(5,8)")

# إدخال رقمي
format: numeric
answer: {value: 90, unit: "ريال", tol: 0.01, allow_fraction: true, accept: ["3/8"]}   # tol/allow_fraction/accept اختيارية
verify: "120 * (1 - Rational(25, 100))"

# عدة خانات
format: multi_numeric
fields: [{label: '$x$', value: 7}, {label: '$y$', value: 3}]
scoring: {mode: all}          # all | each | partial (partial = 2 للكل و1 لـ partial_min)
verify: "[solve([Eq(x + y, 10), Eq(x - y, 4)], [x, y])[s] for s in (x, y)]"

# سحب إلى خانات (القالب بالـ LTR افتراضياً؛ template_dir: rtl للجمل العربية)
format: dragdrop_slots
cards: ['2', '3', '4', '5', '6']                  # أو {id, text, value} عند الحاجة
template: '[[1]] $\times$ [[2]] $=$ [[3]] $\times$ [[4]]'
key: {1: '2', 2: '6', 3: '3', 4: '4'}
check: "s1 * s2 == s3 * s4"                       # لقبول حلول بديلة (JS/Python مشترك: + - * / < > == && || ())
# بدون check: verify شرط على s1..sn مثل "s1 + s2 == s3 and s1 == -2"

# ترتيب
format: dragdrop_order
cards: ['$0.45$', '$\frac{3}{5}$', '$0.5$', '$\frac{2}{5}$']
key: ['$\frac{2}{5}$', '$0.45$', '$0.5$', '$\frac{3}{5}$']
direction: asc                                    # asc|desc ؛ order_labels: ["الأبرد", "الأدفأ"] اختياري
# للبطاقات النصية: cards: [{id: doha, text: 'الدوحة', value: 14}, ...] و key بالمعرّفات

# تصنيف
format: dragdrop_categorize
categories: ['يكافئ $\frac{3}{4}$', 'لا يكافئ $\frac{3}{4}$']
cards: [...]
key: {'$0.75$': 'يكافئ $\frac{3}{4}$', ...}       # كل بطاقة ← فئة
verify: "شرط منطقي يثبت صحة التصنيف"

# رسم على المستوى الإحداثي
format: grid_plot
grid: {xmin: -5, xmax: 5, ymin: -4, ymax: 5}
given: {polygons: [{points: [[-4, 1], [-1, 1], [-4, 4]], labels: ['A', 'B', 'C']}]}   # و/أو points، segments
mode: polygon               # points | polygon | segment
count: 3
key: [[0, -1], [3, -1], [0, 2]]                   # ترتيب غير مهم
verify: "sorted(P) == sorted([(0, -1), (3, -1), (0, 2)])"

# اختر وبرّر (تصحيح بشري، درجة واحدة عادةً)
format: select_explain
options: ["نعم، على صواب", "لا، ليس على صواب"]
key: B
points: 1
rubric: {full: '...', zero: '...', examples: {correct: ['...'], incorrect: ['...']}}

# إجابة مفتوحة (أكواد TIMSS: 20/10 صحيح/جزئي، 70–79 خطأ)
format: cr_explain
points: 2
rubric:
  codes:
    - {code: 20, points: 2, desc: '...'}
    - {code: 10, points: 1, desc: '...'}
    - {code: 70, points: 0, desc: '...'}
  examples: {correct: ['...'], incorrect: ['...']}
model_answer: '...'
```

### مهمة PSI (ملف `psi/PSI1.yaml`) ونموذج محمي (ملف `secure/mock_X1.yaml`)
```yaml
# مهمة PSI: موقف واحد مشترك تُبنى عليه 5 بنود متدرجة (من التنفيذ إلى الاستدلال)، والبنود بالمخطط نفسه أعلاه
id: PSI1
title: 'رحلة إلى متحف قطر الوطني'
context: qatar
intro: |
  نص السياق المشترك (قصير، 3–5 أسطر)، والبيانات المشتركة في table أو figure.
table: {headers: [...], rows: [[...]]}          # اختياري
figure: {type: ...}                             # اختياري
items:
  - id: M8-PSI1-01
    topic: N5
    ...                                         # كل حقول البند المعتادة

# نموذج محمي: كتلتان × 16 بنداً، 45 دقيقة؛ البنود بالمخطط نفسه، ومعرّفاتها M8-X1-01 … M8-X1-32
id: X1
title: 'الاختبار التجريبي 1'
minutes: 45
blocks:
  - id: B1
    items: [ ... 16 بنداً ... ]
  - id: B2
    items: [ ... 16 بنداً ... ]
```
كل نموذج يطابق مخطط TIMSS: الأعداد 10 · الجبر 10 · الهندسة 6 · البيانات 6 | معرفة 11 · تطبيق 13 · استدلال 8، وكل كتلة متوازنة وتبدأ بالأسهل.

### `verify` (يُنفَّذ بـ sympy)
- متاح: `Rational, R, sqrt, pi, Integer, simplify, nsimplify, isprime, factorint, gcd, lcm, Abs, floor, ceiling, solve, Eq, expand, factor, symbols, binomial, factorial, N, divisors, x, y, mean, median, num, abs, min, max, sum, len, sorted, all, any, range, list, set, tuple, round`.
- `num('0.75')` يحوّل نصاً إلى عدد نسبي دقيق. استعمل `Rational` بدل الكسور العشرية العائمة.
- ممنوع `zip`/`enumerate`/`import`. الشرط المنطقي يجب أن يعيد True، والقيمة الرقمية تطابق المفتاح.

### الرسوم (`figure.type`) — تولّدها `scripts/figures.py`
`number_line{min,max,step,label_every,tick_labels,points[{x,label}],jumps[{from,to,label}],rays,segments}` ·
`coord{xmin..ymax,unit,points[{x,y,label,pos}],polygons[{points,labels}],lines[{m,b}|{through}],curves[{expr,from,to}],segments}` ·
`polygon{points,vertex_labels,side_labels,right_angles,angle_labels{i:"40°"},ticks{i:n},extra}` ·
`geo{items:[{seg},{line},{ray},{poly},{circle:[C,r]},{angle:[P,V,Q],label,right},{ticks},{arrows},{label_seg},{pt,label},{text,s}]}` ·
`cylinder{r_label,h_label}` · `cuboid{l,h,w,l_label,h_label,w_label,unit_cubes}` · `cone` · `sphere` · `pyramid` · `tri_prism` · `cube_stack{heights}` ·
`bar{categories,values|series,stacked,y_label,x_label,title}` · `line{x,values|series,y_max,y_step,inset}` · `histogram{edges,freqs}` ·
`dot_plot{min,max,counts}` · `scatter{points,x_max,y_max,trend{m,b}}` · `pie{sectors}` · `pictograph{rows,key_value,key_unit}` ·
`spinner{sectors[{label,weight}]}` · `bag{counts{"أحمر":3}}` · `grid_model{rows,cols,shaded}` · `fraction_bar{parts,shaded}` · `thermometer{min,max,step,value,label_every}`.
النصوص داخل الرسوم: أرقام لاتينية؛ السالب يُكتب بالعدد مباشرة (`-3`).

## 5. المفاهيم الخاطئة — أعد استعمال الرموز الموجودة
أعد استعمال رمز موجود كلما انطبق (يربط البنود في غراف Obsidian). أكثرها تكراراً:
`ignore-negative-sign, additive-ratio-reasoning, multiplication-makes-bigger, add-numerators-denominators, digits-to-decimal, examples-prove-general, longer-decimal-is-larger, unit-conversion-error, additive-scaling, percent-wrong-base, area-perimeter-confusion, operation-confusion, sign-error-elimination, distribute-first-term-only, multiply-exponents, pythagoras-add-instead-of-subtract, circumference-instead-of-area, highest-value-vs-largest-increase, mean-always-best, equiprobability-bias, wrong-event, proportional-not-through-origin, rate-inverted, translate-wrong-direction, count-intervals-wrong`.
رمز جديد عند الضرورة فقط: إنجليزي kebab-case يصف الخطأ (مثل `slope-rise-run-inverted`).

## 6. قائمة التحقق لكل بند
- يقيس موضوعاً واحداً ومستوى معرفياً واحداً كما في إطار TIMSS 2027 (نص الموضوع في blueprint.yaml).
- إجابة صحيحة واحدة فقط، ولا غموض؛ المشتّتات معقولة ومتجانسة وموقع المفتاح يتنوع (A/B/C/D).
- الأرقام نظيفة، والحاسبة لا تمنح ميزة غير عادلة، والزمن واقعي (30–150 ثانية عادة).
- الحل خطوة بخطوة، والاقتراح العلاجي عملي، و`qatar_link` يشير إلى الصف/الوحدة.
- لا نسخ ولا ترجمة لبنود IEA الرسمية — كل البنود أصلية.

## 7. دروس مستفادة يفرضها المدقق والاختبارات (لا تكررها)
- **العدد مع الوحدة داخل الرياضيات دائماً**، في المتن والبدائل والبطاقات والجداول والحلول والمبررات: `$12\,\text{cm}$`. الصيغة «12 cm» خارج `$` تُعرض «cm 12» في النص العربي، ويرفضها المدقق.
- **الكسور مكدّسة دائماً:** `$\frac{3}{5}$` لا `3/5` ولا `$3/5$`؛ فالكسر بالشرطة قد يقرؤه الطالب العربي «5/3» (يرفضه المدقق). لإرشاد إدخال الكسر في الخانة الرقمية اكتب: «لإدخال كسر مثل $\frac{3}{5}$ اضغط 3 ثم / ثم 5».
- **`check` في بنود السحب يُنفَّذ في المتصفح:** استعمل `&&` و`||` لا `and` و`or` (يرفضه المدقق).
- **لا `verify: "True"` أبداً.** في البدائل المفاهيمية اكتب قائمة `[...] == [False, True, False, False]` بعدد البدائل، ويطابق المدقق موضع True مع حرف المفتاح.
- **grid_plot بحل وحيد:** المنصة تصحّح بمطابقة المفتاح فقط.
- **لا تكتب بالشيفرة عبر heredoc في Bash** أي نص فيه شرطة مائلة (`\times` يصير TAB + imes)؛ استعمل أداة Write/Edit. المدقق يرفض أحرف التحكم.
- **الاتجاه تتولاه المنصة:** البدائل والبطاقات وخانات الترتيب تُعرض من اليسار (A أولاً) آلياً، والأعداد اللاتينية في الأدلة تُعزل آلياً، والرسوم تتقلص وتتسع لتسمياتها. لا تضف علامات اتجاه يدوياً.
- **الاختبارات المحمية:** شغّل `python similarity_check.py mock_X?_B?.yaml` على كل كتلة، وتجنّب الصيغ الشائعة جداً («أي الأعداد الآتية عدد أولي؟»).
- **قبل التسليم:** `build_bank.py --strict` صفر أخطاء، ثم `build_platform.py` و`test_platform.py --codes` كلها ناجحة (32 اختباراً).
