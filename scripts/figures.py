# -*- coding: utf-8 -*-
"""
figures.py — مكتبة رسوم SVG موحّدة الهوية لبنك أسئلة TIMSS 2027 (رياضيات الصف الثامن).

كل دالة تستقبل مواصفة (dict) وتعيد نص SVG قابلاً للتضمين داخل HTML.
- النص يبقى نصاً داخل SVG ليعرض المتصفح العربية صحيحة (لا تحويل إلى مسارات).
- الأرقام والرموز بالإنجليزية (0–9، x، y)، وعلامة السالب هي الرمز الرياضي − (U+2212).
- المحاور العددية تحافظ على الاتجاه الرياضي القياسي (x يزداد نحو اليمين).

نقطة الدخول: render(spec) حيث spec["type"] أحد الأنواع في RENDERERS.
"""

import html
import itertools
import math
import re

_AR = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")

# ------------------------------------------------------------------ الهوية
INK = "#1F2A3C"        # خطوط ونصوص
NAVY = "#1B365D"
MAROON = "#8A1538"
GOLD = "#C2A649"
TEAL = "#2A7F8F"
GREEN = "#4E8A3E"
SLATE = "#7A8699"
GRID = "#D5DAE3"
AXIS = "#39465A"
FILL_SOFT = "#E8EDF5"
SERIES = [NAVY, GOLD, MAROON, TEAL, GREEN, SLATE, "#B5651D", "#6A4C93"]
FONT = "'Lusail+','Segoe UI',Tahoma,Arial,sans-serif"

_uid = itertools.count(1)


LRM = chr(0x200E)  # علامة اتجاه من اليسار إلى اليمين (غير مرئية)


def esc(s):
    return html.escape(str(s), quote=True)


def fmt(v):
    """تنسيق عدد للعرض: بلا أصفار زائدة، وسالب بالرمز الرياضي −."""
    if isinstance(v, str):
        return v.replace("-", "−") if v.startswith("-") else v
    if abs(v - round(v)) < 1e-9:
        s = str(int(round(v)))
    else:
        s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s.replace("-", "−")


def nice_step(span, target=6, integer=False):
    raw = span / max(target, 1)
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for m in ((1, 2, 5, 10) if integer else (1, 2, 2.5, 5, 10)):
        if raw <= m * mag:
            step = m * mag
            return max(1, round(step)) if integer else step
    return 10 * mag


def _all_int(vals):
    return all(abs(v - round(v)) < 1e-9 for v in vals)


class SVG:
    def __init__(self, w, h, alt=""):
        self.w, self.h, self.alt = w, h, alt
        self.id = f"f{next(_uid)}"
        self.parts, self.defs = [], []

    # -- أدوات أولية
    def add(self, s):
        self.parts.append(s)

    def line(self, x1, y1, x2, y2, stroke=INK, sw=2.0, dash=None, marker_end=False, marker_start=False, cap="round", opacity=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        me = f' marker-end="url(#{self.arrow()})"' if marker_end else ""
        ms = f' marker-start="url(#{self.arrow(start=True)})"' if marker_start else ""
        op = f' opacity="{opacity}"' if opacity is not None else ""
        self.add(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="{cap}"{d}{me}{ms}{op}/>')

    def rect(self, x, y, w, h, fill="none", stroke=INK, sw=1.5, rx=0, opacity=None):
        op = f' fill-opacity="{opacity}"' if opacity is not None else ""
        self.add(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{op}/>')

    def circle(self, cx, cy, r, fill="none", stroke=INK, sw=1.5, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def polygon(self, pts, fill="none", stroke=INK, sw=2.0, opacity=None, dash=None):
        p = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        op = f' fill-opacity="{opacity}"' if opacity is not None else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"{op}{d}/>')

    def path(self, d, fill="none", stroke=INK, sw=2.0, dash=None, marker_end=False, opacity=None):
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        me = f' marker-end="url(#{self.arrow()})"' if marker_end else ""
        op = f' fill-opacity="{opacity}"' if opacity is not None else ""
        self.add(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"{ds}{me}{op}/>')

    def text(self, x, y, s, size=15, anchor="middle", fill=INK, weight="normal", baseline="central", rotate=None, italic=False):
        """anchor بالمعنى البصري: start = الحافة اليسرى عند x، end = الحافة اليمنى عند x.
        يُحدَّد اتجاه كل نص تلقائياً: عربي ← rtl، غير ذلك ← ltr (فيبقى «8 cm» و«−4» صحيحين
        حتى داخل صفحة RTL)."""
        s = str(s)
        rtl = bool(_AR.search(s))
        a = anchor
        if rtl:
            a = {"start": "end", "end": "start"}.get(anchor, anchor)
            # في سياق RTL تُعرض «°C» معكوسة («C°») لأن ° محايدة الاتجاه؛ علامة LRM قبلها تثبّت الترتيب
            s = re.sub("(?<!" + LRM + ")°(?=[ ]?[A-Za-z])", LRM + "°", s)
        tr = f' transform="rotate({rotate} {x:.2f} {y:.2f})"' if rotate else ""
        st = ' font-style="italic"' if italic else ""
        self.add(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{a}" direction="{"rtl" if rtl else "ltr"}" '
                 f'dominant-baseline="{baseline}" fill="{fill}" font-weight="{weight}"{st}{tr}>{esc(s)}</text>')

    def arrow(self, start=False, color=None):
        mid = f"{self.id}a{'s' if start else 'e'}{(color or '').strip('#')}"
        if not any(mid in d for d in self.defs):
            c = color or INK
            if start:
                self.defs.append(f'<marker id="{mid}" viewBox="0 0 10 10" refX="2" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 10 0 L 0 5 L 10 10 z" fill="{c}"/></marker>')
            else:
                self.defs.append(f'<marker id="{mid}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>')
        return mid

    def render(self):
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w:.0f} {self.h:.0f}" width="{self.w:.0f}" height="{self.h:.0f}" '
                f'class="fig" role="img" aria-label="{esc(self.alt)}" font-family="{FONT}" direction="ltr" '
                f'style="max-width:100%;height:auto;direction:ltr">{defs}{"".join(self.parts)}</svg>')


def _text_w(s, size):
    """تقدير تقريبي لعرض النص بالبكسل (لتوزيع العناوين والمفاتيح)."""
    return 0.56 * size * len(str(s))


# ================================================================== خط الأعداد
def number_line(spec):
    mn, mx = spec["min"], spec["max"]
    step = spec.get("step", 1)
    label_every = spec.get("label_every", 1)
    W = spec.get("width", 640)
    has_jumps = bool(spec.get("jumps"))
    H = spec.get("height", 120 if has_jumps else 80)
    pad = 34
    base_y = H - 38
    svg = SVG(W, H, spec.get("alt", "خط أعداد"))

    def X(v):
        return pad + (v - mn) / (mx - mn) * (W - 2 * pad)

    svg.line(pad - 18, base_y, W - pad + 18, base_y, sw=2.2, marker_end=True, marker_start=True)
    n = int(round((mx - mn) / step))
    labels = spec.get("tick_labels")  # قائمة اختيارية لتسميات مخصصة
    for i in range(n + 1):
        v = mn + i * step
        big = (i % label_every == 0)
        svg.line(X(v), base_y - (8 if big else 5), X(v), base_y + (8 if big else 5), sw=1.6)
        if spec.get("show_labels", True) and big:
            lab = labels[i] if labels and i < len(labels) else fmt(v)
            if lab not in (None, ""):
                svg.text(X(v), base_y + 22, lab, size=14)
    # أشعة المتباينات
    for r in spec.get("rays", []):
        x0 = X(r["from"])
        x1 = (W - pad + 12) if r.get("dir", "right") == "right" else (pad - 12)
        svg.line(x0, base_y, x1, base_y, stroke=MAROON, sw=5, marker_end=True)
        svg.circle(x0, base_y, 6.5, fill=(MAROON if r.get("closed") else "white"), stroke=MAROON, sw=2.5)
    for s in spec.get("segments", []):
        svg.line(X(s["from"]), base_y, X(s["to"]), base_y, stroke=MAROON, sw=5)
        for end in ("from", "to"):
            closed = s.get("closed", True) if isinstance(s.get("closed", True), bool) else s["closed"][0 if end == "from" else 1]
            svg.circle(X(s[end]), base_y, 6, fill=(MAROON if closed else "white"), stroke=MAROON, sw=2.5)
    # قفزات (أقواس) لتمثيل الجمع والطرح
    for j in spec.get("jumps", []):
        a, b = X(j["from"]), X(j["to"])
        top = base_y - 14 - min(60, abs(b - a) * 0.45)
        svg.path(f"M {a:.1f} {base_y-6:.1f} Q {(a+b)/2:.1f} {top:.1f} {b:.1f} {base_y-6:.1f}", stroke=j.get("color", NAVY), sw=2.2, marker_end=True)
        if j.get("label"):
            svg.text((a + b) / 2, top + (base_y - 6 - top) * 0.5 - 12, j["label"], size=14, fill=j.get("color", NAVY), weight="bold")
    for p in spec.get("points", []):
        svg.circle(X(p["x"]), base_y, 6, fill=p.get("color", MAROON), stroke=p.get("color", MAROON))
        if p.get("label"):
            svg.text(X(p["x"]), base_y - 20, p["label"], size=15, weight="bold", fill=p.get("color", MAROON))
    return svg.render()


# ================================================================== المستوى الإحداثي
def coord(spec):
    xmin, xmax = spec.get("xmin", -5), spec.get("xmax", 5)
    ymin, ymax = spec.get("ymin", -5), spec.get("ymax", 5)
    u = spec.get("unit", 34)
    lstep = spec.get("label_step", 1)
    gstep = spec.get("grid_step", 1)
    pad = 30
    W = (xmax - xmin) * u + 2 * pad
    H = (ymax - ymin) * u + 2 * pad
    svg = SVG(W, H, spec.get("alt", "مستوى إحداثي"))

    def X(x):
        return pad + (x - xmin) * u

    def Y(y):
        return pad + (ymax - y) * u

    if spec.get("grid", True):
        k = xmin
        while k <= xmax + 1e-9:
            svg.line(X(k), Y(ymin), X(k), Y(ymax), stroke=GRID, sw=1)
            k += gstep
        k = ymin
        while k <= ymax + 1e-9:
            svg.line(X(xmin), Y(k), X(xmax), Y(k), stroke=GRID, sw=1)
            k += gstep
    # المحاور
    ax_y = 0 if ymin <= 0 <= ymax else ymin
    ax_x = 0 if xmin <= 0 <= xmax else xmin
    svg.line(X(xmin) - 6, Y(ax_y), X(xmax) + 14, Y(ax_y), stroke=AXIS, sw=2, marker_end=True)
    svg.line(X(ax_x), Y(ymin) + 6, X(ax_x), Y(ymax) - 14, stroke=AXIS, sw=2, marker_end=True)
    svg.text(X(xmax) + 16, Y(ax_y) - 12, spec.get("x_name", "x"), size=16, italic=True)
    svg.text(X(ax_x) + 13, Y(ymax) - 16, spec.get("y_name", "y"), size=16, italic=True)
    if spec.get("numbers", True):
        k = xmin
        while k <= xmax + 1e-9:
            if abs(k) > 1e-9 and abs((k / lstep) - round(k / lstep)) < 1e-9:
                svg.text(X(k), Y(ax_y) + 14, fmt(k), size=12, fill=AXIS)
            k += gstep
        k = ymin
        while k <= ymax + 1e-9:
            if abs(k) > 1e-9 and abs((k / lstep) - round(k / lstep)) < 1e-9:
                svg.text(X(ax_x) - 10, Y(k), fmt(k), size=12, anchor="end", fill=AXIS)
            k += gstep
        if xmin <= 0 <= xmax and ymin <= 0 <= ymax:
            svg.text(X(0) - 9, Y(0) + 13, "0", size=12, anchor="end", fill=AXIS)

    def clip_line(x1, y1, x2, y2):
        # امتداد مستقيم يمر بنقطتين حتى حدود الشبكة
        pts = []
        if abs(x2 - x1) < 1e-12:
            return (x1, ymin), (x1, ymax)
        m = (y2 - y1) / (x2 - x1)
        b = y1 - m * x1
        for xx in (xmin, xmax):
            yy = m * xx + b
            if ymin - 1e-9 <= yy <= ymax + 1e-9:
                pts.append((xx, yy))
        if abs(m) > 1e-12:
            for yy in (ymin, ymax):
                xx = (yy - b) / m
                if xmin - 1e-9 <= xx <= xmax + 1e-9:
                    pts.append((xx, yy))
        pts = sorted(set((round(a, 9), round(c, 9)) for a, c in pts))
        return pts[0], pts[-1]

    for ln in spec.get("lines", []):
        if "m" in ln:
            p1, p2 = (0, ln.get("b", 0)), (1, ln["m"] + ln.get("b", 0))
        else:
            p1, p2 = ln["through"]
        a, b = clip_line(p1[0], p1[1], p2[0], p2[1])
        col = ln.get("color", NAVY)
        svg.line(X(a[0]), Y(a[1]), X(b[0]), Y(b[1]), stroke=col, sw=2.4, dash=ln.get("dash"))
        if ln.get("label"):
            lx, ly = ln.get("label_at", [a[0] + 0.82 * (b[0] - a[0]), a[1] + 0.82 * (b[1] - a[1])])
            svg.text(X(lx) + 8, Y(ly) - 12, ln["label"], size=14, fill=col, weight="bold", anchor="start")
    for cv in spec.get("curves", []):
        f = eval("lambda x: " + cv["expr"], {"__builtins__": {}}, {"sqrt": math.sqrt, "abs": abs})
        lo, hi = cv.get("from", xmin), cv.get("to", xmax)
        steps = 240
        seg, segs = [], []
        for i in range(steps + 1):
            x = lo + (hi - lo) * i / steps
            try:
                y = f(x)
            except Exception:
                y = None
            if y is None or y < ymin - 1e-9 or y > ymax + 1e-9:
                if len(seg) > 1:
                    segs.append(seg)
                seg = []
            else:
                seg.append((X(x), Y(y)))
        if len(seg) > 1:
            segs.append(seg)
        for sg in segs:
            d = "M " + " L ".join(f"{a:.1f} {b:.1f}" for a, b in sg)
            svg.path(d, stroke=cv.get("color", MAROON), sw=2.4)
    for pg in spec.get("polygons", []):
        pts = [(X(x), Y(y)) for x, y in pg["points"]]
        svg.polygon(pts, fill=pg.get("fill", NAVY), opacity=pg.get("opacity", 0.14), stroke=pg.get("color", NAVY), sw=2.4, dash=pg.get("dash"))
        labs = pg.get("labels")
        if labs:
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            for (px, py), lab in zip(pts, labs):
                dx, dy = px - cx, py - cy
                d = math.hypot(dx, dy) or 1
                svg.text(px + dx / d * 16, py + dy / d * 16, lab, size=15, weight="bold", fill=pg.get("color", NAVY))
    for sg in spec.get("segments", []):
        (x1, y1), (x2, y2) = sg["points"]
        svg.line(X(x1), Y(y1), X(x2), Y(y2), stroke=sg.get("color", NAVY), sw=2.4, dash=sg.get("dash"))
    for p in spec.get("points", []):
        col = p.get("color", MAROON)
        svg.circle(X(p["x"]), Y(p["y"]), 5, fill=col, stroke=col)
        if p.get("label"):
            dx, dy = {"ne": (9, -12), "nw": (-9, -12), "se": (9, 13), "sw": (-9, 13),
                      "n": (0, -15), "s": (0, 16), "e": (10, 0), "w": (-10, 0)}[p.get("pos", "ne")]
            anchor = "start" if dx > 0 else ("end" if dx < 0 else "middle")
            svg.text(X(p["x"]) + dx, Y(p["y"]) + dy, p["label"], size=14, weight="bold", fill=col, anchor=anchor)
    return svg.render()


# ================================================================== هندسة حرّة (إحداثيات بوحدات، y للأعلى)
def geo(spec):
    """
    مواصفة مرنة للرسوم الهندسية. العناصر في spec['items']:
      {seg: [P,Q], dash?, color?, width?}      قطعة مستقيمة
      {ray: [P,Q]}                             شعاع من P مروراً بـ Q حتى الحافة
      {line: [P,Q]}                            مستقيم ممتد في الاتجاهين
      {poly: [P1,P2,...], fill?, opacity?}     مضلع
      {circle: [C, r], fill?, dash?}           دائرة
      {angle: [P,V,Q], label?, r?, right?}     علامة زاوية عند V بين VP و VQ (right=True مربع قائم)
      {ticks: [P,Q], n: 1|2|3}                 علامات تساوي الأضلاع
      {arrows: [P,Q], n: 1|2}                  علامات التوازي
      {label_seg: [P,Q], text, offset?}        تسمية ضلع (offset موجب = يسار اتجاه P→Q)
      {pt: P, label?, pos?, dot?}              نقطة مسماة
      {text: P, s, size?, color?, anchor?}     نص حر
    """
    items = spec["items"]
    unit = spec.get("unit", 40)
    xs, ys = [], []

    def collect(v):
        if isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(t, (int, float)) for t in v):
            xs.append(v[0]); ys.append(v[1])
        elif isinstance(v, (list, tuple)):
            for t in v:
                collect(t)

    for it in items:
        for k in ("seg", "ray", "line", "poly", "angle", "ticks", "arrows", "label_seg", "pt", "text"):
            if k in it:
                collect(it[k])
        if "circle" in it:
            (cx, cy), r = it["circle"]
            xs += [cx - r, cx + r]; ys += [cy - r, cy + r]
    if "bounds" in spec:
        x0, y0, x1, y1 = spec["bounds"]
    else:
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
    pad = spec.get("pad", 46)
    # تسمية ضلع رأسي تمتد أفقياً خارج الشكل بمقدار الإزاحة وعرض النص: وسّع الهامش حتى لا تُقص عند الحافة
    for it in items:
        if "label_seg" in it and it.get("text"):
            (p_, q_) = it["label_seg"]
            vert = abs(q_[1] - p_[1]) / (math.hypot(q_[0] - p_[0], q_[1] - p_[1]) or 1)
            n_ = len(str(it["text"]))
            extra_ = 0.28 * 14 * n_ * vert if n_ > 2 else 0
            pad = max(pad, abs(it.get("offset") or 16) + extra_ + 0.32 * it.get("size", 15) * n_ * vert + 6)
    W = (x1 - x0) * unit + 2 * pad
    H = (y1 - y0) * unit + 2 * pad
    svg = SVG(W, H, spec.get("alt", "شكل هندسي"))

    def P(v):
        return (pad + (v[0] - x0) * unit, pad + (y1 - v[1]) * unit)

    # مركز الشكل لتوجيه التسميات نحو الخارج
    cxm = sum(xs) / len(xs) if xs else 0
    cym = sum(ys) / len(ys) if ys else 0

    def extend(p, q, both=False):
        (ax, ay), (bx, by) = P(p), P(q)
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy) or 1
        dx, dy = dx / L, dy / L
        far = W + H
        end = (ax + dx * far, ay + dy * far)
        start = (ax - dx * far, ay - dy * far) if both else (ax, ay)
        return start, end

    svg.add(f'<clipPath id="{svg.id}clip"><rect x="0" y="0" width="{W:.1f}" height="{H:.1f}"/></clipPath>')
    for it in items:
        col = it.get("color", INK)
        sw = it.get("width", 2.2)
        if "poly" in it:
            svg.polygon([P(v) for v in it["poly"]], fill=it.get("fill", "none"), opacity=it.get("opacity"), stroke=col, sw=sw, dash=it.get("dash"))
        elif "seg" in it:
            a, b = P(it["seg"][0]), P(it["seg"][1])
            svg.line(a[0], a[1], b[0], b[1], stroke=col, sw=sw, dash=it.get("dash"), marker_end=it.get("arrow", False))
        elif "ray" in it or "line" in it:
            key = "ray" if "ray" in it else "line"
            (sx, sy), (ex, ey) = extend(it[key][0], it[key][1], both=(key == "line"))
            svg.add(f'<g clip-path="url(#{svg.id}clip)">')
            svg.line(sx, sy, ex, ey, stroke=col, sw=sw, dash=it.get("dash"))
            svg.add("</g>")
        elif "circle" in it:
            (c, r) = it["circle"]
            cx, cy = P(c)
            svg.circle(cx, cy, r * unit, fill=it.get("fill", "none"), stroke=col, sw=sw, dash=it.get("dash"))
        elif "angle" in it:
            p, v, q = it["angle"]
            V = P(v); A = P(p); B = P(q)
            a1 = math.atan2(-(A[1] - V[1]), A[0] - V[0])
            a2 = math.atan2(-(B[1] - V[1]), B[0] - V[0])
            r = it.get("r", 24)
            diff = (a2 - a1) % (2 * math.pi)
            if diff > math.pi:
                a1, a2 = a2, a1
                diff = 2 * math.pi - diff
            mid = a1 + diff / 2
            if it.get("right"):
                s = it.get("r", 13)
                u1 = (math.cos(a1), -math.sin(a1)); u2 = (math.cos(a2), -math.sin(a2))
                p1 = (V[0] + u1[0] * s, V[1] + u1[1] * s)
                p2 = (V[0] + u1[0] * s + u2[0] * s, V[1] + u1[1] * s + u2[1] * s)
                p3 = (V[0] + u2[0] * s, V[1] + u2[1] * s)
                svg.path(f"M {p1[0]:.1f} {p1[1]:.1f} L {p2[0]:.1f} {p2[1]:.1f} L {p3[0]:.1f} {p3[1]:.1f}", stroke=it.get("color", INK), sw=1.6)
            else:
                sx, sy = V[0] + r * math.cos(a1), V[1] - r * math.sin(a1)
                ex, ey = V[0] + r * math.cos(a2), V[1] - r * math.sin(a2)
                svg.path(f"M {sx:.1f} {sy:.1f} A {r} {r} 0 0 0 {ex:.1f} {ey:.1f}", stroke=it.get("color", MAROON), sw=1.8)
                if it.get("double"):
                    r2 = r + 5
                    sx, sy = V[0] + r2 * math.cos(a1), V[1] - r2 * math.sin(a1)
                    ex, ey = V[0] + r2 * math.cos(a2), V[1] - r2 * math.sin(a2)
                    svg.path(f"M {sx:.1f} {sy:.1f} A {r2} {r2} 0 0 0 {ex:.1f} {ey:.1f}", stroke=it.get("color", MAROON), sw=1.8)
            if it.get("label"):
                lr = it.get("label_r", (r if not it.get("right") else 14) + 16 + (0.55 * 14 * len(it["label"]) / 2 if len(it["label"]) > 3 else 0))
                svg.text(V[0] + lr * math.cos(mid), V[1] - lr * math.sin(mid), it["label"], size=it.get("size", 15), fill=it.get("color", MAROON), weight="bold")
        elif "ticks" in it:
            a, b = P(it["ticks"][0]), P(it["ticks"][1])
            mx_, my_ = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1
            ux, uy = dx / L, dy / L
            nx, ny = -uy, ux
            n = it.get("n", 1)
            for k in range(n):
                off = (k - (n - 1) / 2) * 6
                cx_, cy_ = mx_ + ux * off, my_ + uy * off
                svg.line(cx_ - nx * 7, cy_ - ny * 7, cx_ + nx * 7, cy_ + ny * 7, stroke=col, sw=1.8)
        elif "arrows" in it:
            a, b = P(it["arrows"][0]), P(it["arrows"][1])
            mx_, my_ = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1
            ux, uy = dx / L, dy / L
            nx, ny = -uy, ux
            for k in range(it.get("n", 1)):
                off = k * 7
                tx, ty = mx_ + ux * off, my_ + uy * off
                svg.path(f"M {tx - ux*7 + nx*6:.1f} {ty - uy*7 + ny*6:.1f} L {tx:.1f} {ty:.1f} L {tx - ux*7 - nx*6:.1f} {ty - uy*7 - ny*6:.1f}", stroke=col, sw=1.8)
        elif "label_seg" in it:
            a, b = P(it["label_seg"][0]), P(it["label_seg"][1])
            mx_, my_ = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1
            nx, ny = dy / L, -dx / L       # يسار الاتجاه في إحداثيات الشاشة
            off = it.get("offset")
            if off is None:              # تلقائياً: بعيداً عن مركز الشكل
                cxs, cys = P((cxm, cym))
                off = 16 if (nx * (mx_ - cxs) + ny * (my_ - cys)) >= 0 else -16
            s = it["text"]
            extra = 0.28 * 14 * len(s) * abs(nx) if len(s) > 2 else 0
            sign = 1 if off >= 0 else -1
            svg.text(mx_ + nx * (off + sign * extra), my_ + ny * (off + sign * extra), s, size=it.get("size", 15), fill=it.get("color", NAVY), weight="bold")
        elif "pt" in it:
            px, py = P(it["pt"])
            if it.get("dot", True):
                svg.circle(px, py, 3.6, fill=it.get("color", INK), stroke=it.get("color", INK))
            if it.get("label"):
                pos = it.get("pos", "auto")
                if pos == "auto":
                    cxs, cys = P((cxm, cym))
                    dx, dy = px - cxs, py - cys
                    d = math.hypot(dx, dy) or 1
                    lx, ly = px + dx / d * 17, py + dy / d * 17
                else:
                    dx, dy = {"n": (0, -17), "s": (0, 18), "e": (15, 0), "w": (-15, 0), "ne": (12, -13), "nw": (-12, -13), "se": (12, 14), "sw": (-12, 14)}[pos]
                    lx, ly = px + dx, py + dy
                svg.text(lx, ly, it["label"], size=it.get("size", 16), weight="bold", fill=it.get("color", INK))
        elif "text" in it:
            px, py = P(it["text"])
            svg.text(px, py, it["s"], size=it.get("size", 15), fill=it.get("color", INK), anchor=it.get("anchor", "middle"), weight=it.get("weight", "normal"))
    return svg.render()


def polygon_fig(spec):
    """مضلع بمواصفة مختصرة تُحوَّل إلى geo."""
    pts = spec["points"]
    n = len(pts)
    items = [{"poly": pts, "fill": spec.get("fill", FILL_SOFT), "opacity": spec.get("opacity", 1), "color": spec.get("color", NAVY)}]
    for i, lab in enumerate(spec.get("vertex_labels", []) or []):
        if lab:
            items.append({"pt": pts[i], "label": lab, "dot": False})
    for i, lab in enumerate(spec.get("side_labels", []) or []):
        if lab:
            items.append({"label_seg": [pts[i], pts[(i + 1) % n]], "text": lab})
    for i in spec.get("right_angles", []) or []:
        items.append({"angle": [pts[(i - 1) % n], pts[i], pts[(i + 1) % n]], "right": True})
    for i, lab in (spec.get("angle_labels", {}) or {}).items():
        i = int(i)
        items.append({"angle": [pts[(i - 1) % n], pts[i], pts[(i + 1) % n]], "label": lab})
    for i, k in (spec.get("ticks", {}) or {}).items():
        i = int(i)
        items.append({"ticks": [pts[i], pts[(i + 1) % n]], "n": k})
    items += spec.get("extra", [])
    return geo({"items": items, "unit": spec.get("unit", 40), "alt": spec.get("alt", "مضلع"), "pad": spec.get("pad", 46)})


# ================================================================== المجسمات (إسقاط مائل)
def _dim_label(svg, a, b, s, off=16, color=NAVY):
    mx_, my_ = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1
    nx, ny = dy / L, -dx / L
    extra = 0.25 * 14 * len(s) * abs(nx)
    svg.text(mx_ + nx * (off + extra), my_ + ny * (off + extra), s, size=15, fill=color, weight="bold")


def cylinder(spec):
    W, H = spec.get("width", 260), spec.get("height", 260)
    cx, rx, ry = W / 2 - 10, W * 0.30, W * 0.09
    # تسمية الارتفاع تقع يمين الأسطوانة: وسّع عرض الرسم بقدر طولها حتى لا تُقص (مثل «4.5 cm»)
    hl = spec.get("h_label")
    need = cx + rx + 24 + 0.62 * 15 * len(str(hl)) + 6 if hl else 0
    svg = SVG(max(W, need), H, spec.get("alt", "أسطوانة"))
    top, bot = 40, H - 45
    svg.add(f'<ellipse cx="{cx}" cy="{bot}" rx="{rx}" ry="{ry}" fill="{FILL_SOFT}" stroke="none"/>')
    svg.rect(cx - rx, top, 2 * rx, bot - top, fill=FILL_SOFT, stroke="none")
    svg.path(f"M {cx-rx} {bot} A {rx} {ry} 0 0 0 {cx+rx} {bot}", stroke=NAVY, sw=2.2)
    svg.path(f"M {cx-rx} {bot} A {rx} {ry} 0 0 1 {cx+rx} {bot}", stroke=NAVY, sw=1.6, dash="6 5")
    svg.line(cx - rx, top, cx - rx, bot, stroke=NAVY, sw=2.2)
    svg.line(cx + rx, top, cx + rx, bot, stroke=NAVY, sw=2.2)
    svg.add(f'<ellipse cx="{cx}" cy="{top}" rx="{rx}" ry="{ry}" fill="#F6F8FB" stroke="{NAVY}" stroke-width="2.2"/>')
    if spec.get("r_label"):
        svg.line(cx, top, cx + rx, top, stroke=MAROON, sw=2)
        svg.circle(cx, top, 3, fill=MAROON, stroke=MAROON)
        svg.text(cx + rx / 2, top - ry - 10, spec["r_label"], size=15, fill=MAROON, weight="bold")
    if spec.get("d_label"):
        svg.line(cx - rx, top, cx + rx, top, stroke=MAROON, sw=2)
        svg.text(cx, top - ry - 10, spec["d_label"], size=15, fill=MAROON, weight="bold")
    if spec.get("h_label"):
        x = cx + rx + 16
        svg.line(x, top, x, bot, stroke=MAROON, sw=1.6, marker_end=True, marker_start=True)
        svg.text(x + 8, (top + bot) / 2, spec["h_label"], size=15, fill=MAROON, weight="bold", anchor="start")
    return svg.render()


def cuboid(spec):
    """متوازي مستطيلات (أو مكعب) بإسقاط مائل. l=الطول (أفقي)، h=الارتفاع، w=العمق."""
    l, h, w = spec.get("l", 4), spec.get("h", 3), spec.get("w", 2)
    u = spec.get("unit", 38)
    ang = math.radians(35)
    dx, dy = w * u * 0.55 * math.cos(ang), -w * u * 0.55 * math.sin(ang)
    pad = 44
    W = l * u + abs(dx) + 2 * pad + 40
    H = h * u + abs(dy) + 2 * pad
    svg = SVG(W, H, spec.get("alt", "متوازي مستطيلات"))
    x0, y0 = pad, H - pad
    A = (x0, y0); B = (x0 + l * u, y0); C = (x0 + l * u, y0 - h * u); D = (x0, y0 - h * u)
    E = (A[0] + dx, A[1] + dy); F = (B[0] + dx, B[1] + dy); G = (C[0] + dx, C[1] + dy); Hh = (D[0] + dx, D[1] + dy)
    svg.polygon([D, C, G, Hh], fill="#F6F8FB", stroke=NAVY, sw=2.2)
    svg.polygon([B, F, G, C], fill="#E1E7F0", stroke=NAVY, sw=2.2)
    svg.polygon([A, B, C, D], fill=FILL_SOFT, stroke=NAVY, sw=2.2)
    svg.line(*A, *E, stroke=NAVY, sw=1.5, dash="6 5")
    svg.line(*E, *F, stroke=NAVY, sw=1.5, dash="6 5")
    svg.line(*E, *Hh, stroke=NAVY, sw=1.5, dash="6 5")
    if spec.get("unit_cubes"):
        for i in range(1, int(l)):
            svg.line(A[0] + i * u, A[1], D[0] + i * u, D[1], stroke=NAVY, sw=1)
            svg.line(D[0] + i * u, D[1], D[0] + i * u + dx, D[1] + dy, stroke=NAVY, sw=1)
        for j in range(1, int(h)):
            svg.line(A[0], A[1] - j * u, B[0], B[1] - j * u, stroke=NAVY, sw=1)
            svg.line(B[0], B[1] - j * u, B[0] + dx, B[1] - j * u + dy, stroke=NAVY, sw=1)
        for k in range(1, int(w)):
            t = k / w
            svg.line(D[0] + dx * t, D[1] + dy * t, C[0] + dx * t, C[1] + dy * t, stroke=NAVY, sw=1)
            svg.line(B[0] + dx * t, B[1] + dy * t, C[0] + dx * t, C[1] + dy * t, stroke=NAVY, sw=1)
    if spec.get("l_label"):
        svg.text((A[0] + B[0]) / 2, A[1] + 20, spec["l_label"], size=15, fill=MAROON, weight="bold")
    if spec.get("h_label"):
        svg.text(A[0] - 10, (A[1] + D[1]) / 2, spec["h_label"], size=15, fill=MAROON, weight="bold", anchor="end")
    if spec.get("w_label"):
        svg.text((B[0] + F[0]) / 2 + 12, (B[1] + F[1]) / 2 + 8, spec["w_label"], size=15, fill=MAROON, weight="bold", anchor="start")
    return svg.render()


def cone(spec):
    W, H = spec.get("width", 240), spec.get("height", 260)
    svg = SVG(W, H, spec.get("alt", "مخروط"))
    cx, rx, ry = W / 2 - 10, W * 0.30, W * 0.09
    apex, bot = (cx, 30), H - 45
    svg.polygon([apex, (cx - rx, bot), (cx + rx, bot)], fill=FILL_SOFT, stroke="none")
    svg.add(f'<ellipse cx="{cx}" cy="{bot}" rx="{rx}" ry="{ry}" fill="{FILL_SOFT}" stroke="none"/>')
    svg.path(f"M {cx-rx} {bot} A {rx} {ry} 0 0 0 {cx+rx} {bot}", stroke=NAVY, sw=2.2)
    svg.path(f"M {cx-rx} {bot} A {rx} {ry} 0 0 1 {cx+rx} {bot}", stroke=NAVY, sw=1.6, dash="6 5")
    svg.line(apex[0], apex[1], cx - rx, bot, stroke=NAVY, sw=2.2)
    svg.line(apex[0], apex[1], cx + rx, bot, stroke=NAVY, sw=2.2)
    if spec.get("h_label"):
        svg.line(cx, apex[1], cx, bot, stroke=MAROON, sw=1.6, dash="5 4")
        svg.text(cx - 8, (apex[1] + bot) / 2, spec["h_label"], size=15, fill=MAROON, weight="bold", anchor="end")
    if spec.get("r_label"):
        svg.line(cx, bot, cx + rx, bot, stroke=MAROON, sw=2)
        svg.text(cx + rx / 2, bot + ry + 14, spec["r_label"], size=15, fill=MAROON, weight="bold")
    if spec.get("s_label"):
        svg.text((apex[0] + cx + rx) / 2 + 14, (apex[1] + bot) / 2 - 4, spec["s_label"], size=15, fill=NAVY, weight="bold", anchor="start")
    return svg.render()


def sphere(spec):
    W = H = spec.get("size", 220)
    svg = SVG(W, H, spec.get("alt", "كرة"))
    c, r = W / 2, W * 0.38
    svg.circle(c, c, r, fill=FILL_SOFT, stroke=NAVY, sw=2.2)
    svg.path(f"M {c-r} {c} A {r} {r*0.28} 0 0 0 {c+r} {c}", stroke=NAVY, sw=1.6)
    svg.path(f"M {c-r} {c} A {r} {r*0.28} 0 0 1 {c+r} {c}", stroke=NAVY, sw=1.4, dash="6 5")
    if spec.get("r_label"):
        svg.line(c, c, c + r, c, stroke=MAROON, sw=2)
        svg.circle(c, c, 3, fill=MAROON, stroke=MAROON)
        svg.text(c + r / 2, c - 14, spec["r_label"], size=15, fill=MAROON, weight="bold")
    return svg.render()


def pyramid(spec):
    """هرم رباعي القاعدة بإسقاط مائل."""
    W, H = spec.get("width", 260), spec.get("height", 250)
    svg = SVG(W, H, spec.get("alt", "هرم"))
    bx, by = 40, H - 50
    L, dx, dy = W * 0.55, W * 0.22, -H * 0.12
    A = (bx, by); B = (bx + L, by); C = (bx + L + dx, by + dy); D = (bx + dx, by + dy)
    apex = (bx + (L + dx) / 2, 28)
    svg.polygon([A, B, apex], fill=FILL_SOFT, stroke=NAVY, sw=2.2)
    svg.polygon([B, C, apex], fill="#E1E7F0", stroke=NAVY, sw=2.2)
    svg.line(*A, *D, stroke=NAVY, sw=1.5, dash="6 5")
    svg.line(*D, *C, stroke=NAVY, sw=1.5, dash="6 5")
    svg.line(*D, *apex, stroke=NAVY, sw=1.5, dash="6 5")
    if spec.get("h_label"):
        ctr = ((A[0] + C[0]) / 2, (A[1] + C[1]) / 2)
        svg.line(apex[0], apex[1], ctr[0], ctr[1], stroke=MAROON, sw=1.6, dash="5 4")
        svg.text(apex[0] + 10, (apex[1] + ctr[1]) / 2, spec["h_label"], size=15, fill=MAROON, weight="bold", anchor="start")
    if spec.get("base_label"):
        svg.text((A[0] + B[0]) / 2, A[1] + 20, spec["base_label"], size=15, fill=MAROON, weight="bold")
    return svg.render()


def tri_prism(spec):
    """منشور ثلاثي بإسقاط مائل. المثلث الأمامي: قاعدة b وارتفاع h، والعمق l."""
    b, h, l = spec.get("b", 4), spec.get("h", 3), spec.get("l", 5)
    u = spec.get("unit", 34)
    ang = math.radians(30)
    dx, dy = l * u * 0.6 * math.cos(ang), -l * u * 0.6 * math.sin(ang)
    pad = 46
    W = b * u + dx + 2 * pad + 30
    H = h * u - dy + 2 * pad
    svg = SVG(W, H, spec.get("alt", "منشور ثلاثي"))
    A = (pad, H - pad); B = (pad + b * u, H - pad)
    apex_x = pad + spec.get("apex_at", 0.0) * b * u
    C = (apex_x, H - pad - h * u)
    A2, B2, C2 = (A[0] + dx, A[1] + dy), (B[0] + dx, B[1] + dy), (C[0] + dx, C[1] + dy)
    svg.polygon([C, C2, B2, B], fill="#E1E7F0", stroke=NAVY, sw=2.2)
    svg.polygon([A, B, C], fill=FILL_SOFT, stroke=NAVY, sw=2.2)
    svg.line(*A, *A2, stroke=NAVY, sw=1.5, dash="6 5")
    svg.line(*A2, *B2, stroke=NAVY, sw=1.5, dash="6 5")
    svg.line(*A2, *C2, stroke=NAVY, sw=1.5, dash="6 5")
    if spec.get("right_angle", True) and abs(spec.get("apex_at", 0.0)) < 1e-9:
        svg.path(f"M {A[0]+12} {A[1]} L {A[0]+12} {A[1]-12} L {A[0]} {A[1]-12}", stroke=INK, sw=1.4)
    if spec.get("b_label"):
        svg.text((A[0] + B[0]) / 2, A[1] + 20, spec["b_label"], size=15, fill=MAROON, weight="bold")
    if spec.get("h_label"):
        svg.text(A[0] - 10, (A[1] + C[1]) / 2, spec["h_label"], size=15, fill=MAROON, weight="bold", anchor="end")
    if spec.get("l_label"):
        svg.text((B[0] + B2[0]) / 2 + 14, (B[1] + B2[1]) / 2 + 6, spec["l_label"], size=15, fill=MAROON, weight="bold", anchor="start")
    return svg.render()


def cube_stack(spec):
    """مكعبات وحدة مكدّسة (إسقاط متساوي القياس). heights: مصفوفة صفوف×أعمدة لأعداد المكعبات."""
    Hm = spec["heights"]           # Hm[row][col] ؛ الصف 0 هو الأبعد
    s = spec.get("size", 30)
    cx, cy = s * 0.866, s * 0.5
    rows, cols = len(Hm), len(Hm[0])
    maxh = max(max(r) for r in Hm)
    W = (rows + cols) * cx + 60
    H = (rows + cols) * cy + maxh * s + 60
    svg = SVG(W, H, spec.get("alt", "مكعبات مكدسة"))
    ox, oy = 30 + rows * cx, 30 + maxh * s

    def iso(x, y, z):
        return (ox + (x - y) * cx, oy + (x + y) * cy - z * s)

    cubes = [(c, r, z) for r in range(rows) for c in range(cols) for z in range(Hm[r][c])]
    cubes.sort(key=lambda t: (t[0] + t[1], t[2]))
    for (x, y, z) in cubes:
        top = [iso(x, y, z + 1), iso(x + 1, y, z + 1), iso(x + 1, y + 1, z + 1), iso(x, y + 1, z + 1)]
        left = [iso(x, y + 1, z), iso(x + 1, y + 1, z), iso(x + 1, y + 1, z + 1), iso(x, y + 1, z + 1)]
        right = [iso(x + 1, y, z), iso(x + 1, y + 1, z), iso(x + 1, y + 1, z + 1), iso(x + 1, y, z + 1)]
        svg.polygon(top, fill="#F6F8FB", stroke=NAVY, sw=1.4)
        svg.polygon(left, fill=FILL_SOFT, stroke=NAVY, sw=1.4)
        svg.polygon(right, fill="#C9D3E3", stroke=NAVY, sw=1.4)
    return svg.render()


# ================================================================== الرسوم البيانية
def _axes_frame(svg, x0, y0, x1, y1, ymin, ymax, ystep, y_label=None, grid=True, xlab_rotate=False):
    """يرسم المحور الرأسي بتدريجاته وخطوط الشبكة الأفقية. يعيد دالة تحويل y."""
    def Y(v):
        return y1 - (v - ymin) / (ymax - ymin) * (y1 - y0)

    v = ymin
    while v <= ymax + 1e-9:
        if grid:
            svg.line(x0, Y(v), x1, Y(v), stroke=GRID, sw=1)
        svg.line(x0 - 5, Y(v), x0, Y(v), stroke=AXIS, sw=1.4)
        svg.text(x0 - 9, Y(v), fmt(round(v, 6)), size=13, anchor="end", fill=AXIS)
        v += ystep
    svg.line(x0, y1, x0, y0 - 6, stroke=AXIS, sw=2)
    svg.line(x0, y1, x1 + 4, y1, stroke=AXIS, sw=2)
    if y_label:
        svg.text(x0 - 46, (y0 + y1) / 2, y_label, size=14, rotate=-90, fill=INK, weight="bold")
    return Y


def _legend(svg, items, x, y, size=13):
    """مفتاح أفقي: items=[(label,color)]، يبدأ من اليمين (قراءة عربية)."""
    cur = x
    for lab, col in items:
        wlab = _text_w(lab, size) + 30
        svg.rect(cur - 14, y - 7, 14, 14, fill=col, stroke="none", rx=2)
        svg.text(cur - 20, y, lab, size=size, anchor="end", fill=INK)
        cur -= wlab + 10


def _title(svg, spec, W):
    if spec.get("title"):
        svg.text(W / 2, 20, spec["title"], size=16, weight="bold", fill=NAVY)


def bar_chart(spec):
    cats = spec["categories"]
    series = spec.get("series") or [{"name": spec.get("name", ""), "values": spec["values"]}]
    stacked = spec.get("stacked", False)
    n, m = len(cats), len(series)
    W = spec.get("width", max(420, 90 * n + 120))
    H = spec.get("height", 320)
    top = 44 if (spec.get("title") or m > 1) else 24
    if spec.get("title") and m > 1:
        top = 64
    x0, y0, x1, y1 = 78, top, W - 20, H - 58
    svg = SVG(W, H, spec.get("alt", "تمثيل بالأعمدة"))
    _title(svg, spec, W)
    totals = [sum(s["values"][i] for s in series) for i in range(n)] if stacked else [max(s["values"][i] for s in series) for i in range(n)]
    ymax = spec.get("y_max") or (max(totals) * 1.12 if max(totals) > 0 else 1)
    ystep = spec.get("y_step") or nice_step(ymax, 6, integer=_all_int([v for s in series for v in s["values"]]))
    ymax = math.ceil(ymax / ystep - 1e-9) * ystep
    Y = _axes_frame(svg, x0, y0, x1, y1, 0, ymax, ystep, spec.get("y_label"))
    slot = (x1 - x0) / n
    bw = slot * (0.62 if stacked or m == 1 else 0.8)
    for i, c in enumerate(cats):
        sx = x0 + slot * i + (slot - bw) / 2
        if stacked:
            acc = 0
            for k, s in enumerate(series):
                v = s["values"][i]
                svg.rect(sx, Y(acc + v), bw, Y(acc) - Y(acc + v), fill=s.get("color", SERIES[k % len(SERIES)]), stroke="white", sw=1)
                acc += v
        else:
            w1 = bw / m
            for k, s in enumerate(series):
                v = s["values"][i]
                svg.rect(sx + k * w1, Y(v), w1 - 2, y1 - Y(v), fill=s.get("color", SERIES[k % len(SERIES)]), stroke="none")
                if spec.get("value_labels"):
                    svg.text(sx + k * w1 + (w1 - 2) / 2, Y(v) - 10, fmt(v), size=12, fill=INK)
        svg.text(x0 + slot * i + slot / 2, y1 + 18, c, size=13, fill=INK)
    if spec.get("x_label"):
        svg.text((x0 + x1) / 2, H - 14, spec["x_label"], size=14, weight="bold")
    if m > 1:
        _legend(svg, [(s["name"], s.get("color", SERIES[k % len(SERIES)])) for k, s in enumerate(series)], W - 24, top - 22)
    return svg.render()


def line_chart(spec):
    xs = spec["x"]                   # تسميات فئوية (سنوات، أشهر…)
    series = spec.get("series") or [{"name": spec.get("name", ""), "values": spec["values"]}]
    n, m = len(xs), len(series)
    W = spec.get("width", max(440, 64 * n + 120))
    H = spec.get("height", 320)
    top = 64 if (spec.get("title") and m > 1) else (44 if (spec.get("title") or m > 1) else 24)
    x0, y0, x1, y1 = 78, top, W - 26, H - 58
    svg = SVG(W, H, spec.get("alt", "تمثيل بالخطوط"))
    _title(svg, spec, W)
    allv = [v for s in series for v in s["values"] if v is not None]
    ymin = spec.get("y_min", 0)
    ymax = spec.get("y_max") or max(allv) * 1.12
    ystep = spec.get("y_step") or nice_step(ymax - ymin, 6, integer=_all_int(allv))
    ymax = ymin + math.ceil((ymax - ymin) / ystep - 1e-9) * ystep
    Y = _axes_frame(svg, x0, y0, x1, y1, ymin, ymax, ystep, spec.get("y_label"))
    step = (x1 - x0) / (n - 1 if n > 1 else 1)
    inset = step * 0.35 if spec.get("inset", True) else 0
    step = (x1 - x0 - 2 * inset) / (n - 1 if n > 1 else 1)
    for i, lab in enumerate(xs):
        X = x0 + inset + i * step
        svg.line(X, y1, X, y1 + 5, stroke=AXIS, sw=1.4)
        svg.text(X, y1 + 18, lab, size=13)
    for k, s in enumerate(series):
        col = s.get("color", SERIES[k % len(SERIES)])
        pts = [(x0 + inset + i * step, Y(v)) for i, v in enumerate(s["values"]) if v is not None]
        svg.path("M " + " L ".join(f"{a:.1f} {b:.1f}" for a, b in pts), stroke=col, sw=2.6, dash=s.get("dash"))
        for a, b in pts:
            svg.circle(a, b, 4.2, fill=col, stroke="white", sw=1.2)
    if spec.get("x_label"):
        svg.text((x0 + x1) / 2, H - 14, spec["x_label"], size=14, weight="bold")
    if m > 1:
        _legend(svg, [(s["name"], s.get("color", SERIES[k % len(SERIES)])) for k, s in enumerate(series)], W - 24, top - 22)
    return svg.render()


def histogram(spec):
    edges, freqs = spec["edges"], spec["freqs"]      # len(edges) = len(freqs)+1
    W = spec.get("width", 480)
    H = spec.get("height", 320)
    top = 44 if spec.get("title") else 24
    x0, y0, x1, y1 = 78, top, W - 24, H - 58
    svg = SVG(W, H, spec.get("alt", "مدرج تكراري"))
    _title(svg, spec, W)
    ymax = spec.get("y_max") or max(freqs) * 1.15
    ystep = spec.get("y_step") or nice_step(ymax, 6, integer=_all_int(freqs))
    ymax = math.ceil(ymax / ystep - 1e-9) * ystep
    Y = _axes_frame(svg, x0, y0, x1, y1, 0, ymax, ystep, spec.get("y_label"))
    lo, hi = edges[0], edges[-1]
    inset = (x1 - x0) * 0.04

    def X(v):
        return x0 + inset + (v - lo) / (hi - lo) * (x1 - x0 - 2 * inset)

    for i, f in enumerate(freqs):
        svg.rect(X(edges[i]), Y(f), X(edges[i + 1]) - X(edges[i]), y1 - Y(f), fill=spec.get("color", NAVY), stroke="white", sw=1.5, opacity=0.9)
    for e in edges:
        svg.line(X(e), y1, X(e), y1 + 5, stroke=AXIS, sw=1.4)
        svg.text(X(e), y1 + 18, fmt(e), size=13)
    if spec.get("x_label"):
        svg.text((x0 + x1) / 2, H - 14, spec["x_label"], size=14, weight="bold")
    return svg.render()


def dot_plot(spec):
    """counts: {قيمة: عدد النقاط}. min/max/step لخط الأعداد."""
    mn, mx = spec["min"], spec["max"]
    step = spec.get("step", 1)
    counts = {float(k): v for k, v in spec["counts"].items()}
    maxc = max(counts.values()) if counts else 1
    W = spec.get("width", 520)
    r = spec.get("r", 8)
    top = 40 if spec.get("title") else 18
    H = top + maxc * (2 * r + 3) + 76
    svg = SVG(W, H, spec.get("alt", "مخطط النقاط"))
    _title(svg, spec, W)
    pad = 40
    base = H - 52

    def X(v):
        return pad + (v - mn) / (mx - mn) * (W - 2 * pad)

    svg.line(pad - 14, base, W - pad + 14, base, stroke=AXIS, sw=2)
    v = mn
    while v <= mx + 1e-9:
        svg.line(X(v), base - 5, X(v), base + 5, stroke=AXIS, sw=1.4)
        svg.text(X(v), base + 18, fmt(round(v, 6)), size=13)
        v += step
    for val, c in counts.items():
        for k in range(c):
            svg.circle(X(val), base - r - 4 - k * (2 * r + 3), r, fill=spec.get("color", NAVY), stroke="white", sw=1)
    if spec.get("x_label"):
        svg.text(W / 2, H - 12, spec["x_label"], size=14, weight="bold")
    return svg.render()


def scatter(spec):
    pts = spec["points"]
    xmin, xmax = spec.get("x_min", 0), spec["x_max"]
    ymin, ymax = spec.get("y_min", 0), spec["y_max"]
    xstep = spec.get("x_step") or nice_step(xmax - xmin, 6)
    ystep = spec.get("y_step") or nice_step(ymax - ymin, 6)
    W, H = spec.get("width", 460), spec.get("height", 360)
    top = 44 if spec.get("title") else 24
    x0, y0, x1, y1 = 78, top, W - 24, H - 58
    svg = SVG(W, H, spec.get("alt", "شكل الانتشار"))
    _title(svg, spec, W)
    Y = _axes_frame(svg, x0, y0, x1, y1, ymin, ymax, ystep, spec.get("y_label"))

    def X(v):
        return x0 + (v - xmin) / (xmax - xmin) * (x1 - x0)

    v = xmin
    while v <= xmax + 1e-9:
        svg.line(X(v), y0, X(v), y1, stroke=GRID, sw=1)
        svg.line(X(v), y1, X(v), y1 + 5, stroke=AXIS, sw=1.4)
        svg.text(X(v), y1 + 18, fmt(round(v, 6)), size=13)
        v += xstep
    for p in pts:
        svg.circle(X(p[0]), Y(p[1]), 5, fill=spec.get("color", MAROON), stroke="white", sw=1.2)
    if spec.get("trend"):
        m, b = spec["trend"]["m"], spec["trend"]["b"]
        xa, xb = xmin, xmax
        ya, yb = m * xa + b, m * xb + b
        # قص الخط داخل الإطار
        def clamp_x(yv):
            return (yv - b) / m if m else xa
        if ya < ymin: xa, ya = clamp_x(ymin), ymin
        if ya > ymax: xa, ya = clamp_x(ymax), ymax
        if yb < ymin: xb, yb = clamp_x(ymin), ymin
        if yb > ymax: xb, yb = clamp_x(ymax), ymax
        svg.line(X(xa), Y(ya), X(xb), Y(yb), stroke=NAVY, sw=2.2, dash="7 5")
    if spec.get("x_label"):
        svg.text((x0 + x1) / 2, H - 14, spec["x_label"], size=14, weight="bold")
    return svg.render()


def pie(spec):
    sectors = spec["sectors"]                # [{label, value, color?}]
    total = sum(s["value"] for s in sectors)
    W, H = spec.get("width", 460), spec.get("height", 300)
    svg = SVG(W, H, spec.get("alt", "تمثيل بالقطاعات الدائرية"))
    _title(svg, spec, W)
    cx, cy, r = W * 0.34, H / 2 + (10 if spec.get("title") else 0), min(W, H) * 0.36
    ang = -math.pi / 2
    for k, s in enumerate(sectors):
        frac = s["value"] / total
        a2 = ang + frac * 2 * math.pi
        large = 1 if frac > 0.5 else 0
        x1_, y1_ = cx + r * math.cos(ang), cy + r * math.sin(ang)
        x2_, y2_ = cx + r * math.cos(a2), cy + r * math.sin(a2)
        col = s.get("color", SERIES[k % len(SERIES)])
        if frac >= 0.9999:
            svg.circle(cx, cy, r, fill=col, stroke="white", sw=2)
        else:
            svg.path(f"M {cx:.1f} {cy:.1f} L {x1_:.1f} {y1_:.1f} A {r:.1f} {r:.1f} 0 {large} 1 {x2_:.1f} {y2_:.1f} Z", fill=col, stroke="white", sw=2)
        if spec.get("show_pct", True):
            mid = (ang + a2) / 2
            txt = s.get("inner", f"{fmt(round(frac*100, 1))}%")
            svg.text(cx + r * 0.62 * math.cos(mid), cy + r * 0.62 * math.sin(mid), txt, size=13, fill="white", weight="bold")
        ang = a2
    # المفتاح عمودياً على اليمين
    lx, ly = W - 24, cy - (len(sectors) - 1) * 13
    for k, s in enumerate(sectors):
        col = s.get("color", SERIES[k % len(SERIES)])
        svg.rect(lx - 14, ly + k * 26 - 7, 14, 14, fill=col, stroke="none", rx=2)
        svg.text(lx - 20, ly + k * 26, s["label"], size=13, anchor="end")
    return svg.render()


def pictograph(spec):
    rows = spec["rows"]                       # [{label, count}]  count بعدد الرموز (يسمح بنصف رمز)
    key = spec.get("key_value", 1)
    s = spec.get("icon_size", 26)
    maxc = max(math.ceil(r["count"]) for r in rows)
    lab_w = max(_text_w(r["label"], 14) for r in rows) + 24
    W = spec.get("width", max(360, lab_w + maxc * (s + 6) + 40))
    H = 30 + len(rows) * (s + 14) + 50 + (26 if spec.get("title") else 0)
    svg = SVG(W, H, spec.get("alt", "تمثيل بالصور"))
    _title(svg, spec, W)
    y = 30 + (26 if spec.get("title") else 0)
    for r in rows:
        svg.text(W - 12, y + s / 2, r["label"], size=14, anchor="end", weight="bold")
        x = W - lab_w - s
        c = r["count"]
        k = 0
        while c > 1e-9:
            part = min(1, c)
            svg.add(_icon(x, y, s, part, spec.get("icon", "circle")))
            x -= s + 6
            c -= part
            k += 1
        svg.line(12, y + s + 7, W - 12, y + s + 7, stroke=GRID, sw=1)
        y += s + 14
    svg.add(_icon(W - 40, y + 6, s * 0.8, 1, spec.get("icon", "circle")))
    svg.text(W - 50, y + 6 + s * 0.4, f"= {fmt(key)} {spec.get('key_unit', '')}".strip(), size=14, anchor="end")
    return svg.render()


def _icon(x, y, s, part, kind):
    col = NAVY
    clip = f'<clipPath id="ic{int(x)}_{int(y)}"><rect x="{x + s*(1-part):.1f}" y="{y:.1f}" width="{s*part:.1f}" height="{s:.1f}"/></clipPath>'
    if kind == "circle":
        shape = f'<circle cx="{x+s/2:.1f}" cy="{y+s/2:.1f}" r="{s/2-1:.1f}" fill="{col}"/>'
    else:  # square
        shape = f'<rect x="{x:.1f}" y="{y:.1f}" width="{s:.1f}" height="{s:.1f}" rx="4" fill="{col}"/>'
    return f'{clip}<g clip-path="url(#ic{int(x)}_{int(y)})">{shape}</g>'


# ================================================================== الاحتمالات
def spinner(spec):
    sectors = spec["sectors"]                 # [{label, weight, color?}]
    tot = sum(s.get("weight", 1) for s in sectors)
    S = spec.get("size", 240)
    svg = SVG(S, S, spec.get("alt", "قرص دوّار"))
    c, r = S / 2, S * 0.42
    ang = -math.pi / 2
    for k, s in enumerate(sectors):
        frac = s.get("weight", 1) / tot
        a2 = ang + frac * 2 * math.pi
        large = 1 if frac > 0.5 else 0
        col = s.get("color", SERIES[k % len(SERIES)])
        svg.path(f"M {c:.1f} {c:.1f} L {c + r*math.cos(ang):.1f} {c + r*math.sin(ang):.1f} A {r:.1f} {r:.1f} 0 {large} 1 {c + r*math.cos(a2):.1f} {c + r*math.sin(a2):.1f} Z", fill=col, stroke="white", sw=2.5, opacity=0.95)
        mid = (ang + a2) / 2
        svg.text(c + r * 0.64 * math.cos(mid), c + r * 0.64 * math.sin(mid), s.get("label", ""), size=spec.get("font", 15), fill=s.get("text_color", "white"), weight="bold")
        ang = a2
    svg.circle(c, c, r, stroke=INK, sw=2.2)
    if spec.get("pointer", True):
        a = math.radians(spec.get("pointer_deg", -60))
        # سهم قصير ينتهي قبل حلقة التسميات (عند 0.64 من نصف القطر) فلا يحجب اسم القطاع
        ln = spec.get("pointer_len", 0.42)
        svg.line(c, c, c + r * ln * math.cos(a), c + r * ln * math.sin(a), stroke=INK, sw=3.5, marker_end=True)
        svg.circle(c, c, 6, fill=INK, stroke=INK)
    return svg.render()


COLOR_NAMES = {"أحمر": "#C0392B", "أزرق": "#1F5FAD", "أخضر": "#3C8D40", "أصفر": "#E6B422", "أسود": "#222222", "أبيض": "#FFFFFF", "برتقالي": "#E67E22", "بنفسجي": "#7D3C98"}


def bag(spec):
    """كيس كرات: counts = {اسم اللون: العدد}."""
    counts = spec["counts"]
    balls = [name for name, n in counts.items() for _ in range(n)]
    per_row = spec.get("per_row", 6)
    rows = math.ceil(len(balls) / per_row)
    rb = spec.get("r", 14)
    W = per_row * (2 * rb + 8) + 80
    H = rows * (2 * rb + 8) + 90
    svg = SVG(W, H, spec.get("alt", "كيس كرات"))
    svg.path(f"M 30 40 Q 26 {H-20} 60 {H-14} L {W-60} {H-14} Q {W-26} {H-20} {W-30} 40 Q {W/2} 56 30 40 Z", fill="#F3EFE6", stroke="#8C7A5B", sw=2.5)
    svg.path(f"M {W/2-26} 34 Q {W/2} 22 {W/2+26} 34", stroke="#8C7A5B", sw=3)
    # ترتيب حتمي متداخل (دوري بين الألوان) ليبدو طبيعياً ويبقى ثابتاً في كل بناء
    groups = [[name] * n for name, n in counts.items()]
    ordr = []
    while any(groups):
        for g in groups:
            if g:
                ordr.append(g.pop())
    for i, name in enumerate(ordr):
        rr, cc = divmod(i, per_row)
        x = 40 + rb + cc * (2 * rb + 8) + (rb if rr % 2 else 0) * 0.5
        y = 64 + rb + rr * (2 * rb + 8)
        col = COLOR_NAMES.get(name, name)
        svg.circle(x, y, rb, fill=col, stroke="#333", sw=1.2)
        if spec.get("labels_on_balls"):
            svg.text(x, y, name[0], size=11, fill="white" if col not in ("#FFFFFF", "#E6B422") else "#222")
    return svg.render()


def grid_model(spec):
    """نموذج مساحة (كسور/نسب مئوية): rows×cols مع خلايا مظللة (عدد أو قائمة)."""
    R, C = spec.get("rows", 10), spec.get("cols", 10)
    s = spec.get("cell", 22)
    W, H = C * s + 20, R * s + 20
    svg = SVG(W, H, spec.get("alt", "نموذج شبكي"))
    shaded = spec.get("shaded", 0)
    cells = set()
    if isinstance(shaded, int):
        for k in range(shaded):
            cells.add((k // C, k % C) if spec.get("by", "row") == "row" else (k % R, k // R))
    else:
        cells = {tuple(t) for t in shaded}
    for r_ in range(R):
        for c_ in range(C):
            svg.rect(10 + c_ * s, 10 + r_ * s, s, s, fill=(MAROON if (r_, c_) in cells else "white"), stroke=SLATE, sw=1, opacity=(0.85 if (r_, c_) in cells else 1))
    svg.rect(10, 10, C * s, R * s, stroke=INK, sw=2)
    return svg.render()


def fraction_bar(spec):
    bars = spec.get("bars") or [spec]
    s_w = spec.get("width", 420)
    h = 34
    H = len(bars) * (h + 18) + 16
    svg = SVG(s_w + 110, H, spec.get("alt", "شرائط كسور"))
    for i, b in enumerate(bars):
        y = 10 + i * (h + 18)
        n, k = b["parts"], b.get("shaded", 0)
        w = s_w / n
        for j in range(n):
            svg.rect(12 + j * w, y, w, h, fill=(GOLD if j < k else "white"), stroke=INK, sw=1.6)
        if b.get("label"):
            svg.text(s_w + 24, y + h / 2, b["label"], size=15, anchor="start", weight="bold")
    return svg.render()


def thermometer(spec):
    mn, mx, step = spec["min"], spec["max"], spec.get("step", 5)
    val = spec.get("value")
    H = spec.get("height", 300)
    W = 150
    svg = SVG(W, H, spec.get("alt", "مقياس حرارة"))
    top, bot = 20, H - 50
    cx = 56

    def Y(v):
        return bot - (v - mn) / (mx - mn) * (bot - top)

    svg.rect(cx - 9, top - 6, 18, bot - top + 12, fill="white", stroke=INK, sw=2, rx=9)
    svg.circle(cx, bot + 22, 16, fill=MAROON, stroke=INK, sw=2)
    if val is not None:
        svg.rect(cx - 5, Y(val), 10, bot + 10 - Y(val), fill=MAROON, stroke="none")
    v = mn
    k = 0
    every = spec.get("label_every", 1)
    while v <= mx + 1e-9:
        major = (k % every == 0)
        svg.line(cx + 10, Y(v), cx + (22 if major else 17), Y(v), stroke=INK, sw=1.4)
        if major:
            svg.text(cx + 28, Y(v), fmt(round(v, 6)), size=13, anchor="start")
        v += step
        k += 1
    if spec.get("unit"):
        svg.text(cx + 28, top - 12, spec["unit"], size=13, anchor="start", weight="bold")
    return svg.render()


def raw(spec):
    return spec["svg"]


RENDERERS = {
    "number_line": number_line,
    "coord": coord,
    "geo": geo,
    "polygon": polygon_fig,
    "cylinder": cylinder,
    "cuboid": cuboid,
    "cone": cone,
    "sphere": sphere,
    "pyramid": pyramid,
    "tri_prism": tri_prism,
    "cube_stack": cube_stack,
    "bar": bar_chart,
    "line": line_chart,
    "histogram": histogram,
    "dot_plot": dot_plot,
    "scatter": scatter,
    "pie": pie,
    "pictograph": pictograph,
    "spinner": spinner,
    "bag": bag,
    "grid_model": grid_model,
    "fraction_bar": fraction_bar,
    "thermometer": thermometer,
    "raw": raw,
}


def render(spec):
    """نقطة الدخول: spec مفرد أو قائمة مواصفات تُعرض متجاورة."""
    if isinstance(spec, list):
        return '<div class="fig-row">' + "".join(render(s) for s in spec) + "</div>"
    t = spec.get("type")
    if t not in RENDERERS:
        raise ValueError(f"نوع رسم غير معروف: {t}")
    svg = RENDERERS[t](spec)
    cap = spec.get("caption")
    if cap:
        return f'<figure class="fig-wrap">{svg}<figcaption>{esc(cap)}</figcaption></figure>'
    return svg


if __name__ == "__main__":
    # معرض سريع لكل الأنواع (للمراجعة البصرية)
    demo = [
        {"type": "number_line", "min": -6, "max": 6, "points": [{"x": -4, "label": "A"}], "jumps": [{"from": -4, "to": 3, "label": "+7"}]},
        {"type": "coord", "xmin": -4, "xmax": 5, "ymin": -3, "ymax": 4, "polygons": [{"points": [[1, 1], [4, 1], [1, 3]], "labels": ["A", "B", "C"]}], "lines": [{"m": 0.5, "b": -1, "label": "L"}]},
        {"type": "polygon", "points": [[0, 0], [4, 0], [4, 3]], "vertex_labels": ["A", "B", "C"], "side_labels": ["8 cm", "6 cm", "?"], "right_angles": [1]},
        {"type": "geo", "items": [{"line": [[0, 0], [6, 0]]}, {"line": [[0, 2.5], [6, 2.5]]}, {"line": [[1, -0.8], [4.6, 3.3]]}, {"angle": [[6, 2.5], [3.8, 2.5], [4.6, 3.3]], "label": "65°"}, {"angle": [[0, 0], [1.7, 0], [4.6, 3.3]], "label": "x"}], "bounds": [0, -1, 6, 3.5]},
        {"type": "cylinder", "r_label": "3 m", "h_label": "5 m"},
        {"type": "cuboid", "l": 5, "h": 3, "w": 2, "l_label": "5 cm", "h_label": "3 cm", "w_label": "2 cm", "unit_cubes": True},
        {"type": "cone", "r_label": "4 cm", "h_label": "9 cm"},
        {"type": "sphere", "r_label": "6 cm"},
        {"type": "pyramid", "h_label": "8 cm", "base_label": "6 cm"},
        {"type": "tri_prism", "b": 4, "h": 3, "l": 6, "b_label": "4 cm", "h_label": "3 cm", "l_label": "10 cm"},
        {"type": "cube_stack", "heights": [[2, 1, 1], [1, 1, 0]]},
        {"type": "bar", "categories": ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء"], "values": [12, 18, 9, 15], "y_label": "عدد الطلاب", "title": "حضور نادي الرياضيات"},
        {"type": "bar", "categories": ["2022", "2023", "2024"], "series": [{"name": "بنين", "values": [30, 42, 38]}, {"name": "بنات", "values": [35, 40, 47]}], "y_label": "العدد", "stacked": True},
        {"type": "line", "x": ["يناير", "فبراير", "مارس", "أبريل", "مايو"], "values": [22, 24, 28, 33, 38], "y_label": "°C", "title": "متوسط درجة الحرارة في الدوحة"},
        {"type": "histogram", "edges": [0, 10, 20, 30, 40, 50], "freqs": [3, 7, 12, 6, 2], "x_label": "الدقائق", "y_label": "التكرار"},
        {"type": "dot_plot", "min": 0, "max": 8, "counts": {"1": 2, "2": 4, "3": 5, "4": 3, "6": 1, "8": 1}, "x_label": "عدد الكتب المقروءة"},
        {"type": "scatter", "points": [[1, 2], [2, 3.1], [3, 3.9], [4, 5.2], [5, 5.8], [6, 7.1]], "x_max": 7, "y_max": 8, "trend": {"m": 1, "b": 1}, "x_label": "ساعات المذاكرة", "y_label": "الدرجة"},
        {"type": "pie", "sectors": [{"label": "كرة القدم", "value": 45}, {"label": "السباحة", "value": 25}, {"label": "كرة السلة", "value": 20}, {"label": "أخرى", "value": 10}]},
        {"type": "pictograph", "rows": [{"label": "الصف 8A", "count": 4}, {"label": "الصف 8B", "count": 2.5}, {"label": "الصف 8C", "count": 3}], "key_value": 10, "key_unit": "طلاب"},
        {"type": "spinner", "sectors": [{"label": "1", "weight": 2}, {"label": "2", "weight": 1}, {"label": "3", "weight": 1}]},
        {"type": "bag", "counts": {"أحمر": 3, "أزرق": 5, "أخضر": 2}},
        {"type": "grid_model", "rows": 10, "cols": 10, "shaded": 35},
        {"type": "fraction_bar", "bars": [{"parts": 4, "shaded": 3, "label": "3/4"}, {"parts": 8, "shaded": 6, "label": "6/8"}]},
        {"type": "thermometer", "min": -10, "max": 40, "step": 10, "value": 25, "unit": "°C"},
    ]
    import os, sys
    out = sys.argv[1] if len(sys.argv) > 1 else "figures_gallery.html"
    body = "".join(f'<div class="cell"><div class="t">{esc(d["type"])}</div>{render(d)}</div>' for d in demo)
    page = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>Figures gallery</title>
<style>body{{font-family:{FONT};background:#fff;margin:16px}} .grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}
.cell{{border:1px solid #ddd;border-radius:8px;padding:8px}} .t{{font:12px monospace;color:#666}} svg.fig{{width:100%;height:auto;display:block;margin:auto}}</style>
</head><body><div class="grid">{body}</div></body></html>"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print("written", out, len(page))
