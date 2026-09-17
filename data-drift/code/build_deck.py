"""Seminar deck: concept drift. White background, black text, formulae."""
import re
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.text import PP_ALIGN

BLACK = RGBColor(0x00, 0x00, 0x00)
RULE  = RGBColor(0xBF, 0xBF, 0xBF)      # chart gridlines only; never text
FONT  = "Calibri"
MATH  = "Cambria Math"

W, H = 13.333, 7.5
M     = 0.7

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(W), Inches(H)
BLANK = prs.slide_layouts[6]

SUB, SUP = "-25000", "30000"
_TOK = re.compile(r"([_^])\{([^}]*)\}|([_^])(\S)")


def _emit(p, text, size, bold=False, italic=False, font=FONT):
    """Render `text`, honouring _{...} and ^{...} as true sub/superscripts."""
    pos, out = 0, []
    for m in _TOK.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], None))
        mark = m.group(1) or m.group(3)
        body = m.group(2) if m.group(2) is not None else m.group(4)
        out.append((body, SUB if mark == "_" else SUP))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], None))
    for chunk, base in out:
        if chunk == "":
            continue
        r = p.add_run(); r.text = chunk
        r.font.size = Pt(size * (0.72 if base else 1.0))
        r.font.bold, r.font.italic = bold, italic
        r.font.color.rgb = BLACK
        r.font.name = font
        if base:
            r.font._rPr.set("baseline", base)
    return p


def slide(title=None, subtitle=None):
    s = prs.slides.add_slide(BLANK)
    if title:
        tb = s.shapes.add_textbox(Inches(M), Inches(0.40), Inches(W-2*M), Inches(0.8))
        tf = tb.text_frame; tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_bottom = 0
        _emit(tf.paragraphs[0], title, 32, bold=True)
    if subtitle:
        tb = s.shapes.add_textbox(Inches(M), Inches(1.20), Inches(W-2*M), Inches(0.45))
        tf = tb.text_frame; tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_bottom = 0
        _emit(tf.paragraphs[0], subtitle, 17)
    return s


def bullets(s, items, top=1.9, left=M, width=None, size=17, gap=10):
    width = width or (W - 2*M)
    tb = s.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(H-top-0.5))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_bottom = 0
    for i, (text, bold, lvl) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.level, p.space_after = lvl, Pt(gap)
        _emit(p, text, size - 1*lvl, bold=bold)
    return tb


def eq(s, text, top, left=M, size=24, width=None):
    """A display formula, set in a math face."""
    tb = s.shapes.add_textbox(Inches(left), Inches(top),
                              Inches(width or (W-2*M)), Inches(0.62))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_bottom = 0
    _emit(tf.paragraphs[0], text, size, italic=True, font=MATH)
    return tb


def table(s, rows, left, top, width, height, col_w=None, size=16,
          header=True, align=None):
    nr, nc = len(rows), len(rows[0])
    tbl = s.shapes.add_table(nr, nc, Inches(left), Inches(top),
                             Inches(width), Inches(height)).table
    tbl.first_row = header
    if col_w:
        tot = sum(col_w)
        for j, cw in enumerate(col_w):
            tbl.columns[j].width = Emu(int(Inches(width) * cw / tot))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = tbl.cell(i, j)
            c.text = ""
            c.margin_left = c.margin_right = Inches(0.08)
            c.margin_top = c.margin_bottom = Inches(0.03)
            c.fill.solid(); c.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            p = c.text_frame.paragraphs[0]
            a = align[j] if align else ("l" if j == 0 else "r")
            p.alignment = PP_ALIGN.LEFT if a == "l" else PP_ALIGN.RIGHT
            _emit(p, str(val), size, bold=(i == 0 and header))
    return tbl


def style_chart(chart, legend=True, num_fmt="0.0"):
    chart.font.size = Pt(14); chart.font.name = FONT; chart.font.color.rgb = BLACK
    chart.has_title = False
    if legend:
        chart.has_legend = True
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(14); chart.legend.font.color.rgb = BLACK
    else:
        chart.has_legend = False
    va = chart.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = RULE
    va.major_gridlines.format.line.width = Pt(0.75)
    va.tick_labels.font.size = Pt(13); va.tick_labels.font.color.rgb = BLACK
    va.format.line.color.rgb = RULE
    ca = chart.category_axis
    ca.has_major_gridlines = False
    ca.tick_labels.font.size = Pt(13); ca.tick_labels.font.color.rgb = BLACK
    ca.format.line.color.rgb = BLACK
    pl = chart.plots[0]
    pl.has_data_labels = True
    dl = pl.data_labels
    dl.font.size = Pt(12); dl.font.color.rgb = BLACK; dl.font.name = FONT
    dl.number_format = num_fmt; dl.number_format_is_linked = False
    for i, ser in enumerate(chart.series):
        col = BLACK if i == 0 else RGBColor(0x8C, 0x8C, 0x8C)
        ser.format.fill.solid(); ser.format.fill.fore_color.rgb = col
        ser.format.line.color.rgb = col


def section(label, line):
    s = prs.slides.add_slide(BLANK)
    tb = s.shapes.add_textbox(Inches(M), Inches(2.7), Inches(W-2*M), Inches(1.0))
    tf = tb.text_frame; tf.margin_left = 0; tf.word_wrap = True
    tf.paragraphs[0].alignment = PP_ALIGN.LEFT
    _emit(tf.paragraphs[0], label, 36, bold=True)
    bullets(s, [(line, False, 0)], top=3.9, size=18)
    return s


# 1. Title -----------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
tb = s.shapes.add_textbox(Inches(M), Inches(2.4), Inches(W-2*M), Inches(1.5))
tf = tb.text_frame; tf.word_wrap = True; tf.margin_left = 0
_emit(tf.paragraphs[0], "Concept Drift in Data Streams", 42, bold=True)
_emit(tf.add_paragraph(), "Formulation, methods, and a reproduction of Read (2018)", 22)
bullets(s, [("Seminar presentation", False, 0)], top=4.7, size=17)

# 2. Outline ---------------------------------------------------------------
s = slide("Outline")
table(s, [
    ["1", "Formulation", "definition, taxonomy, and which factor of the joint moves"],
    ["2", "Methods", "drift detection, and the three adaptation mechanisms"],
    ["3", "Read (2018)", "the argument that a drifting stream is a time series"],
    ["4", "Reproduction", "Table 2's methods rebuilt; results and discrepancies"],
    ["5", "Subsequent work", "normalisation, online ensembles, proactive adaptation"],
    ["6", "Open problems", "unresolved questions and proposed experiments"],
], left=M, top=1.7, width=W-2*M, height=3.9, col_w=[0.4,2.6,8.4], size=18,
   align=["l","l","l"], header=False)

# 3. Section 1 -------------------------------------------------------------
section("1.  Formulation",
        "The target distribution is a function of time, not a fixed object.")

# 4. Definition ------------------------------------------------------------
s = slide("The problem", "supervised learning assumes a distribution that streams do not provide")
bullets(s, [
    ("Batch learning assumes a fixed joint distribution p(x, y): a model fitted to a", False, 0),
    ("sample generalises because the sample and the deployment share that law.", False, 0),
    ("In a data stream the law itself evolves.", True, 0),
], top=1.85, size=18, gap=8)
eq(s, "p_{t}(y | x)  ≠  p_{t+k}(y | x)", top=3.45, size=28)
bullets(s, [
    ("The mapping from input to label is time-dependent, so a deployed model is not", False, 0),
    ("stale but misspecified: it estimates a target that no longer exists.", False, 0),
    ("Two consequences constrain every method that follows:", True, 0),
    ("degradation is silent — no failure is raised, the error rate simply rises", False, 1),
    ("retraining from scratch is unavailable — the stream is unbounded, labels are late", False, 1),
], top=4.35, size=17, gap=8)

# 5. Taxonomy --------------------------------------------------------------
s = slide("Taxonomy", "Gama et al. (2014); Read (2018) §3.1–3.4")
table(s, [
    ["type", "behaviour", "intermediate states"],
    ["Sudden", "one concept replaces another at a change point", "none"],
    ["Incremental", "the concept advances through a sequence of states", "genuine concepts"],
    ["Gradual", "two concepts alternate, mixing weight shifting", "no new concepts"],
    ["Recurring", "concepts return, frequently with a period", "previously seen"],
], left=M, top=1.85, width=W-2*M, height=2.8, col_w=[1.8,5.6,3.4], size=17,
   align=["l","l","l"])
bullets(s, [
    ("The third column governs method design. Incremental drift admits a path through", False, 0),
    ("parameter space; gradual drift does not, since the concept alternates between two", False, 0),
    ("fixed points and only the mixing weight evolves smoothly.", False, 0),
], top=5.0, size=17, gap=6)

# 6. What moves ------------------------------------------------------------
s = slide("Which factor moves", "the joint admits exactly two loci of change")
eq(s, "p(x, y)  =  p(x) · p(y | x)", top=1.85, size=28)
table(s, [
    ["", "definition", "conventional name", "typical remedy"],
    ["Virtual drift", "p(x) changes, p(y | x) fixed", "covariate shift", "normalisation"],
    ["Real concept drift", "p(y | x) changes", "concept drift", "adaptation"],
], left=M, top=2.75, width=W-2*M, height=1.9, col_w=[2.8,3.8,2.8,2.6], size=16,
   align=["l","l","l","l"])
bullets(s, [
    ("Only the second displaces the decision boundary, and therefore only the second", False, 0),
    ("necessarily costs accuracy. Most recent forecasting work addresses the first:", False, 0),
    ("RevIN, Dish-TS and SAN normalise shifting marginals and leave p(y | x) untouched.", False, 0),
    ("An unlabelled detector observes only p(x), and so cannot distinguish the two cases.", True, 0),
], top=4.95, size=17, gap=7)

# 7. Context drift ---------------------------------------------------------
s = slide("Three referents of “context drift”", "the term is used for distinct phenomena with opposed remedies")
table(s, [
    ["sense", "what changes", "implied response"],
    ["Concept drift", "p(y | x) changes with t", "track or reset the model"],
    ["Context-driven shift", "p(y | x, c) fixed; c omitted from the model", "condition on c"],
    ["Context-window drift", "the inference window leaves the pretraining law", "adapt at inference"],
], left=M, top=1.85, width=W-2*M, height=2.5, col_w=[2.8,5.6,3.4], size=17,
   align=["l","l","l"])
bullets(s, [
    ("The first two present the same symptom — error correlated with time — and require", True, 0),
    ("opposite responses. Where a periodic context accounts for the change, adaptation is", True, 0),
    ("wasted and will be reversed on the following cycle.", True, 0),
    ("SOLID (KDD'24) scores the second directly, by mutual information between prediction", False, 0),
    ("residuals and the candidate context:", False, 0),
], top=4.6, size=17, gap=6)
eq(s, "I(E_{t} ; c_{t})", top=6.35, size=26)

# 8. Section 2 -------------------------------------------------------------
section("2.  Methods",
        "Detecting that drift occurred, and adapting the model once it has.")

# 9. Detection -------------------------------------------------------------
s = slide("Drift detection", "detectors observe the error sequence, not the data")
table(s, [
    ["detector", "test statistic", "guarantee"],
    ["DDM (2004)", "error rate exceeds a running minimum by kσ", "heuristic thresholds"],
    ["EDDM (2006)", "distance between consecutive errors contracts", "improved on gradual drift"],
    ["ADWIN (2007)", "window split; cut when the two halves differ", "false positives bounded by δ"],
], left=M, top=1.85, width=W-2*M, height=2.5, col_w=[2,5.6,3.8], size=17,
   align=["l","l","l"])
bullets(s, [
    ("ADWIN maintains an exponential histogram, giving O(log W) memory, and the surviving", False, 0),
    ("window length is itself an estimate of the current concept's extent.", False, 0),
    ("A detector reads E_{t} over time and decides whether that sequence has changed.", True, 0),
    ("Every drift detector is therefore already a time-series method.", True, 0),
], top=4.65, size=17, gap=8)

# 10. Evaluation -----------------------------------------------------------
s = slide("Limitations of the evaluation protocol")
bullets(s, [
    ("Synthetic benchmarks predominate.", True, 0),
    ("Streams switch between predefined concepts at fixed times; transfer to real", False, 1),
    ("data is unestablished.", False, 1),
    ("Proxy evaluation conflates two quantities.", True, 0),
    ("Assessing a detector by whether retraining improves accuracy confounds detector", False, 1),
    ("quality with model adaptability, and measures neither accuracy nor latency.", False, 1),
    ("Verification latency invalidates the classical detectors.", True, 0),
    ("DDM, EDDM and ADWIN assume immediate labels. In fraud detection ground truth", False, 1),
    ("arrives after 30–180 days, so they are inapplicable in their original form.", False, 1),
    ("Where the error signal is unobservable for months, so is any method depending on it.", False, 0),
], top=1.6, size=17, gap=6)

# 11. Mechanisms -----------------------------------------------------------
s = slide("Three adaptation mechanisms", "the model's representation determines what adaptation can mean")
table(s, [
    ["mechanism", "representation", "adapts by", "in Θ?", "admits Δθ?"],
    ["Forgetting — kNN, SAMkNN", "stored data", "replacing data", "no", "no"],
    ["Detect and reset — HT, RF-HT", "a structure", "rebuilding it", "no", "no"],
    ["Continuous — SGD", "a vector", "displacing it", "yes", "yes"],
], left=M, top=1.9, width=W-2*M, height=2.4, col_w=[3.4,2.2,2.2,1.2,1.6], size=17,
   align=["l","l","l","l","l"])
bullets(s, [
    ("A tree admits no Δθ. Its parameters form a discrete structure, so no small", True, 0),
    ("displacement exists; it can only be grown or destroyed. A buffer is equivalent: the", False, 0),
    ("model is the stored data, and adaptation means replacing it.", False, 0),
    ("Only a model whose parameters occupy a continuous space can be displaced slightly,", False, 0),
    ("which is the premise of the argument in §3.", False, 0),
], top=4.6, size=17, gap=7)

# 12. Section 3 ------------------------------------------------------------
section("3.  Read (2018)",
        "arXiv:1810.02266 — Concept-drifting Data Streams are Time Series")

# 13. Lemma 1 --------------------------------------------------------------
s = slide("The contradiction", "Lemma 1, and the failure of the asymptotic objection")
bullets(s, [
    ("The literature assumes instances are i.i.d. within a concept and treats drift as an", False, 0),
    ("event to detect, so that an i.i.d. model may be reset and redeployed.", False, 0),
    ("Lemma 1.  A stream exhibiting concept drift exhibits temporal dependence.", True, 0),
    ("Independence would require P(C_{t}) = P(C_{t} | C_{t−1}). Measured on a 20-step stream", False, 0),
    ("with change point τ = 10:", False, 0),
], top=1.8, size=17, gap=6)
eq(s, "P(C_{t} = 0) = 0.450          P(C_{t} = 0 | C_{t−1} = 1) = 0.000", top=4.2, size=24)
bullets(s, [
    ("The objection is that the concept indicator becomes constant as t grows.", False, 0),
    ("The reply is that τ is not observed. Knowledge of τ would permit partitioning the", True, 0),
    ("stream and treating each side as i.i.d.; absent it, an instantaneous change appears", False, 0),
    ("as dependence in the error signal over many instances.", False, 0),
], top=5.05, size=17, gap=6)

# 14. Trajectory -----------------------------------------------------------
s = slide("Drift as a trajectory", "a concept is a point θ ∈ Θ; drift is a path through Θ")
table(s, [
    ["type", "trajectory", "path to follow?"],
    ["Sudden", "θ resampled from the prior at τ", "no — a discontinuity"],
    ["Incremental", "θ_{t} = A^{⊤}θ_{t−1}, a rotation of 0.01 rad", "yes"],
    ["Gradual", "θ alternates between two fixed points", "no — α_{t} evolves, not θ"],
    ["Recurring", "a cycle through a finite set of concepts", "yes, and it repeats"],
], left=M, top=1.85, width=W-2*M, height=2.6, col_w=[1.8,5.4,3.6], size=17,
   align=["l","l","l"])
bullets(s, [
    ("A trajectory is in principle predictable, which restates the problem: solving concept", False, 0),
    ("drift is equivalent to forecasting θ_{t}. The prescription follows —", False, 0),
], top=4.7, size=17, gap=6)
eq(s, "θ_{t+1}  ←  θ_{t} + λ ∇E", top=5.5, size=28)
bullets(s, [
    ("— with no detector and no reset, subject to one condition: λ must not decay to zero.", False, 0),
], top=6.35, size=17)

# 15. Section 4 ------------------------------------------------------------
section("4.  Reproduction",
        "All six methods of Table 2 rebuilt in the Python standard library.")

# 16. Setup ----------------------------------------------------------------
s = slide("Experimental setup")
bullets(s, [
    ("Data, obtained from the repository the paper cites:", True, 0),
    ("Electricity, 45,312 instances; CoverType, 581,012 — both counts exact", False, 1),
    ("Methods, all six of Table 2, reimplemented rather than substituted:", True, 0),
    ("kNN · hinge-loss SGD · Hoeffding Tree with naive Bayes leaves", False, 1),
    ("SAMkNN · PBF-SGD, degree-3 basis · RF-HT, 100 trees over ADWIN2", False, 1),
    ("ADWIN2 validated independently: detection 55 instances after a true change,", False, 1),
    ("and no false alarms across 4,000 stationary instances", False, 1),
    ("Streams at Table 1 parameters: T = 10K, τ_{0} = 1K, τ_{1} = 5K, τ_{2} = 6K.", True, 0),
    ("Prequential evaluation; accuracy recorded over τ_{0} … T.", False, 1),
], top=1.6, size=17, gap=6)

# 17. Results --------------------------------------------------------------
s = slide("Results: Table 3", "reproduced / reported")
table(s, [
    ["stream", "SAMkNN", "PBF-SGD", "RF-HT"],
    ["Electricity, 45,312", "78.0 / 79.8", "80.7 / 85.9", "84.5 / 86.2"],
    ["RTG, 10K", "71.1 / 78.8", "82.8 / 81.8", "72.5 / 77.9"],
    ["Synthetic, 10K", "81.1 / 96.0", "88.5 / 95.1", "86.7 / 93.6"],
    ["CoverType, 10K — not comparable", "91.2 / 93.3", "91.0 / 92.6", "90.5 / 93.9"],
], left=M, top=1.85, width=W-2*M, height=2.7, col_w=[3.6,2,2,2], size=17)
bullets(s, [
    ("Electricity reproduces: SAMkNN within 1.8 points, RF-HT within 1.7 at 100 trees.", False, 0),
    ("On RTG, PBF-SGD exceeds the reported value and the reported ranking is preserved.", False, 0),
    ("Two systematic deviations, both attributable:", True, 0),
    ("PBF-SGD on Electricity (−5.2), attributable to the polynomial degree, not to λ", False, 1),
    ("SAMkNN deviates in order (−1.8, −7.7, −14.9), tracking the load on its long-term", False, 1),
    ("memory, which the reimplementation compresses more crudely", False, 1),
], top=4.75, size=17, gap=5)

# 18. lambda ---------------------------------------------------------------
s = slide("The condition on λ", "accuracy lost under the schedule λ_{t} = λ_{0} / √t")
cd = CategoryChartData()
cd.categories = ["stationary", "sudden", "incremental", "gradual", "sustained"]
cd.add_series("Penalty", (0.9, 18.6, 5.2, 14.9, 0.8))
style_chart(s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(M), Inches(1.95),
                               Inches(7.2), Inches(4.4), cd).chart, legend=False)
bullets(s, [
    ("Read states that decay causes SGD to", False, 0),
    ("react progressively more slowly, and", False, 0),
    ("reports no experiment isolating it.", False, 0),
    ("The penalty is largest after sudden", True, 0),
    ("drift and negligible under sustained", True, 0),
    ("drift.", True, 0),
    ("Under sustained rotation a constant λ", False, 0),
    ("attains only 88.1, so decay forfeits", False, 0),
    ("little. After a resampled concept a", False, 0),
    ("live λ relearns; a frozen one cannot.", False, 0),
    ("The condition concerns", True, 0),
    ("recovery from discontinuities.", True, 0),
], top=1.95, left=8.3, width=4.5, size=15, gap=2)

# 19. kNN ------------------------------------------------------------------
s = slide("Buffer methods", "capacity and insensitivity are the same property")
cd = CategoryChartData()
cd.categories = ["stationary", "sudden", "incremental", "gradual", "sustained"]
cd.add_series("SGD", (97.3, 94.1, 96.1, 94.0, 88.1))
cd.add_series("kNN", (73.3, 73.1, 73.2, 72.8, 72.7))
ch = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(M), Inches(1.95),
                        Inches(7.2), Inches(4.4), cd).chart
style_chart(ch)
ch.value_axis.minimum_scale = 65; ch.value_axis.maximum_scale = 100
bullets(s, [
    ("kNN is inferior in all five regimes", True, 0),
    ("and invariant across them: a spread", True, 0),
    ("of 0.6 points against SGD's 9.2.", True, 0),
    ("Drift costs a buffer almost nothing,", False, 0),
    ("because a buffer accumulates nothing", False, 0),
    ("for drift to invalidate.", False, 0),
    ("Read records two separate", False, 0),
    ("observations — that buffer capacity", False, 0),
    ("bounds accuracy, and that kNN shows", False, 0),
    ("no upward trend when stationary.", False, 0),
    ("They are one property.", True, 0),
], top=2.1, left=8.3, width=4.5, size=15, gap=2)

# 20. Unstated -------------------------------------------------------------
s = slide("Unstated parameters", "each alters the reported figures more than any method does")
table(s, [
    ["parameter", "measured effect"],
    ["Synthetic input dimension", "SGD attains 57.7 / 74.5 / 83.1 / 92.2 at d = 2 / 5 / 10 / 20"],
    ["PBF-SGD polynomial degree", "the specified degree 3 is 3.3 points below degree 2"],
    ["Electricity attribute count", "stated as 6; the data file declares 8"],
    ["L2 strength for SGD", "unstated; scikit-multiflow default assumed"],
], left=M, top=1.85, width=W-2*M, height=2.7, col_w=[3.4,8], size=17, align=["l","l"])
bullets(s, [
    ("The dimension is decisive. The reported Synthetic row, 93.6–96.0, is attainable only", False, 0),
    ("at the upper end, and not at the d = 2 of the paper's Figure 4.", False, 0),
    ("A related observation: on the Synthetic stream SGD attains 92.2 and PBF-SGD 88.5.", True, 0),
    ("That concept is a hyperplane θ^{⊤}x = 0, linear by construction, so a degree-3 basis", False, 0),
    ("contributes 1,770 parameters of variance and no expressive power.", False, 0),
], top=4.75, size=17, gap=6)

# 21. Section 5 ------------------------------------------------------------
section("5.  Subsequent work",
        "The forecasting problem Read posed was formulated and solved in 2025.")

# 22. Families -------------------------------------------------------------
s = slide("Four families of response")
table(s, [
    ["family", "principle", "representative work"],
    ["Normalisation", "remove shifting marginals; leave p(y | x) alone", "RevIN, Dish-TS, SAN"],
    ["Online fast/slow", "balance adaptation against recall of prior patterns", "FSNet, OneNet"],
    ["Concept pools", "retain one model per concept; select the nearest", "CEP, for recurrence"],
    ["Proactive", "predict the parameter shift before error accrues", "Proceed, KDD'25"],
], left=M, top=1.6, width=W-2*M, height=3.0, col_w=[2.4,6.2,3.4], size=17,
   align=["l","l","l"])
bullets(s, [
    ("Only the last realises Read's proposal. Proceed estimates the drift between recent", False, 0),
    ("training data and the current test instance, then maps that estimate to a parameter", False, 0),
    ("adjustment through a learned generator:", False, 0),
], top=4.85, size=17, gap=6)
eq(s, "Δθ  =  g_{φ}(Δĉ)", top=6.25, size=26)

# 23. Foundation models ----------------------------------------------------
s = slide("Drift under foundation models", "when the parameters are not available for adaptation")
bullets(s, [
    ("Time-series foundation models — Chronos, Moirai and successors — are pretrained on", False, 0),
    ("large corpora and applied zero-shot. Drift does not disappear; its locus moves.", False, 0),
    ("Black-box adaptation.", True, 0),
    ("Where the model is served behind an API, the weights cannot be modified; adaptation", False, 1),
    ("proceeds by learning the structure of the model's errors in context.", False, 1),
    ("Drift-resilient priors.", True, 0),
    ("Alternatively, drift is incorporated into the in-context prior, so the model learns to", False, 1),
    ("estimate, adapt to and extrapolate change — Drift-Resilient TabPFN, NeurIPS'24.", False, 1),
    ("Both are continuous adaptation in the sense of §2; the parameters simply reside in", False, 0),
    ("the context or in a residual corrector rather than in the weights.", False, 0),
], top=1.85, size=17, gap=6)

# 24. Section 6 ------------------------------------------------------------
section("6.  Open problems",
        "What remains unresolved, and what the present harness can test.")

# 25. Open problems --------------------------------------------------------
s = slide("Unresolved questions")
bullets(s, [
    ("No criterion distinguishes real drift from omitted context.", True, 0),
    ("CDS holds that p(y | x) only appears to move because c was never conditioned on;", False, 1),
    ("Read holds that θ genuinely traverses Θ. Where c is observable and periodic,", False, 1),
    ("tracking is wasted; where it is latent, conditioning is impossible. No published", False, 1),
    ("criterion identifies which regime obtains.", False, 1),
    ("Recurrence and sustained drift partition the method space.", True, 0),
    ("A pool presumes concepts return; a tracker presumes smooth displacement. The", False, 1),
    ("crossover between the two has no published characterisation.", False, 1),
    ("Evaluation remains synthetic and label-immediate, while the applications that", True, 0),
    ("motivate the field are neither.", True, 0),
], top=1.6, size=17, gap=6)

# 26. Proposed -------------------------------------------------------------
s = slide("Proposed experiments", "each stated as a falsifiable prediction")
table(s, [
    ["", "question", "prediction"],
    ["A", "Why does momentum not assist?",
     "A rotation-aware extrapolator closes the tracking gap, and has\nno effect on sudden drift"],
    ["B", "Real drift, or omitted context?",
     "I(E_{t} ; c_{t}) separates the regimes; autocorrelation does not"],
    ["C", "When does tracking lose to storage?",
     "A crossover period p* exists, below which a pool dominates"],
    ["D", "What value should λ take?",
     "λ* scales as the square root of the drift rate"],
], left=M, top=1.85, width=W-2*M, height=3.3, col_w=[0.4,3.4,7.4], size=16,
   align=["l","l","l"])
bullets(s, [
    ("B addresses the first open problem. Electricity carries an observable periodic", False, 0),
    ("context, and the synthetic streams expose the ground-truth concept, so both", False, 0),
    ("regimes can be constructed and separated on one harness.", False, 0),
], top=5.4, size=17, gap=6)

# 27. Summary --------------------------------------------------------------
s = slide("Summary")
bullets(s, [
    ("Concept drift is a change in p(y | x) with time, distinct from covariate shift; most", False, 0),
    ("recent forecasting work addresses the latter.", False, 0),
    ("Which adaptation mechanism is available follows from the model's representation:", False, 0),
    ("a tree admits no Δθ.", False, 0),
    ("Read (2018) argues drift implies temporal dependence, hence a drifting stream is a", False, 0),
    ("time series and the concept should be tracked rather than detected.", False, 0),
    ("Reproduced: two of three methods within 2 points on Electricity. The condition on λ", False, 0),
    ("holds, but concerns recovery from discontinuities rather than tracking.", False, 0),
    ("Proceed (KDD'25) realises the forecasting proposal seven years later.", False, 0),
    ("The open question is separating genuine drift from context never modelled.", False, 0),
], top=1.6, size=18, gap=11)

prs.save("/tmp/claude-0/-root-time-series-research/350c80dd-3cf5-4b19-ac84-1e395d6dbfb5/scratchpad/deck/seminar.pptx")
print("saved, %d slides" % len(prs.slides._sldIdLst))
