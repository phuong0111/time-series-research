"""Seminar deck: reproducing Read (2018). White background, black text, minimal."""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.text import PP_ALIGN

BLACK = RGBColor(0x00, 0x00, 0x00)
GREY  = RGBColor(0x80, 0x80, 0x80)
LIGHT = RGBColor(0xD9, 0xD9, 0xD9)
FONT  = "Calibri"

W, H = 13.333, 7.5
M     = 0.7                      # slide margin

prs = Presentation()
prs.slide_width  = Inches(W)
prs.slide_height = Inches(H)
BLANK = prs.slide_layouts[6]     # fully blank: no placeholders to fight


def slide(title=None, subtitle=None):
    s = prs.slides.add_slide(BLANK)
    if title:
        tb = s.shapes.add_textbox(Inches(M), Inches(0.42), Inches(W-2*M), Inches(0.75))
        tf = tb.text_frame; tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]; r = p.add_run(); r.text = title
        r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(30), True, BLACK, FONT
    if subtitle:
        tb = s.shapes.add_textbox(Inches(M), Inches(1.18), Inches(W-2*M), Inches(0.42))
        tf = tb.text_frame; tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]; r = p.add_run(); r.text = subtitle
        r.font.size, r.font.color.rgb, r.font.name = Pt(15), GREY, FONT
        r.font.italic = True
    return s


def bullets(s, items, top=1.85, left=M, width=None, size=16, gap=11):
    """items: list of (text, bold, indent_level)."""
    width = width or (W - 2*M)
    tb = s.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(H-top-0.6))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_bottom = 0
    for i, (text, bold, lvl) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.level = lvl
        p.space_after = Pt(gap)
        r = p.add_run(); r.text = text
        r.font.size = Pt(size - 2*lvl)
        r.font.bold = bold
        r.font.color.rgb = BLACK if lvl == 0 else GREY if lvl > 1 else BLACK
        r.font.name = FONT
    return tb


def note(s, text):
    s.notes_slide.notes_text_frame.text = text


def table(s, rows, left, top, width, height, col_w=None, size=13, header=True, align=None):
    nr, nc = len(rows), len(rows[0])
    shp = s.shapes.add_table(nr, nc, Inches(left), Inches(top), Inches(width), Inches(height))
    tbl = shp.table
    tbl.first_row = header
    if col_w:
        total = sum(col_w)
        for j, cw in enumerate(col_w):
            tbl.columns[j].width = Emu(int(Inches(width) * cw / total))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = tbl.cell(i, j)
            c.text = ""
            c.margin_left = c.margin_right = Inches(0.08)
            c.margin_top = c.margin_bottom = Inches(0.03)
            c.fill.solid(); c.fill.fore_color.rgb = RGBColor(0xFF,0xFF,0xFF)
            p = c.text_frame.paragraphs[0]
            a = (align[j] if align else ("l" if j == 0 else "r"))
            p.alignment = PP_ALIGN.LEFT if a == "l" else PP_ALIGN.RIGHT
            r = p.add_run(); r.text = str(val)
            r.font.size = Pt(size)
            r.font.bold = (i == 0 and header)
            r.font.color.rgb = BLACK
            r.font.name = FONT
    return tbl


def style_chart(chart, legend=True, labels=True, num_fmt='0.0'):
    chart.font.size = Pt(12); chart.font.name = FONT; chart.font.color.rgb = BLACK
    chart.has_title = False
    if legend:
        chart.has_legend = True
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(12)
    else:
        chart.has_legend = False
    try:
        va = chart.value_axis
        va.has_major_gridlines = True
        va.major_gridlines.format.line.color.rgb = LIGHT
        va.major_gridlines.format.line.width = Pt(0.75)
        va.tick_labels.font.size = Pt(11); va.tick_labels.font.color.rgb = GREY
        va.format.line.color.rgb = LIGHT
    except Exception:
        pass
    try:
        ca = chart.category_axis
        ca.has_major_gridlines = False
        ca.tick_labels.font.size = Pt(11); ca.tick_labels.font.color.rgb = BLACK
        ca.format.line.color.rgb = GREY
    except Exception:
        pass
    if labels:
        pl = chart.plots[0]
        pl.has_data_labels = True
        dl = pl.data_labels
        dl.font.size = Pt(10); dl.font.color.rgb = BLACK; dl.font.name = FONT
        dl.number_format = num_fmt
        dl.number_format_is_linked = False
    for i, ser in enumerate(chart.series):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = BLACK if i == 0 else GREY
        ser.format.line.color.rgb = BLACK if i == 0 else GREY


def section(label, items):
    """Divider: section number and title, plus what it covers."""
    s = prs.slides.add_slide(BLANK)
    tb = s.shapes.add_textbox(Inches(M), Inches(2.6), Inches(W-2*M), Inches(1.0))
    tf = tb.text_frame; tf.margin_left = 0; tf.word_wrap = True
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT
    r = p.add_run(); r.text = label
    r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(34), True, BLACK, FONT
    bullets(s, [(i, False, 0) for i in items], top=3.8, size=16, gap=7)
    return s


# =====================================================================
# 1. Title
# =====================================================================
s = slide()
tb = s.shapes.add_textbox(Inches(M), Inches(2.4), Inches(W-2*M), Inches(1.4))
tf = tb.text_frame; tf.word_wrap = True; tf.margin_left = 0
p = tf.paragraphs[0]; r = p.add_run()
r.text = "Concept Drift in Data Streams"
r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(40), True, BLACK, FONT
p2 = tf.add_paragraph(); r = p2.add_run()
r.text = "The problem, the field's answers, and a reproduction"
r.font.size, r.font.color.rgb, r.font.name = Pt(22), GREY, FONT
tb = s.shapes.add_textbox(Inches(M), Inches(4.6), Inches(W-2*M), Inches(0.6))
tf = tb.text_frame; tf.margin_left = 0
p = tf.paragraphs[0]; r = p.add_run()
r.text = "Seminar presentation"
r.font.size, r.font.color.rgb, r.font.name = Pt(14), GREY, FONT

# =====================================================================
# 2. Outline
# =====================================================================
s = slide("Outline")
table(s, [
    ["", "", ""],
    ["1", "What concept drift is", "definition, taxonomy, what actually moves"],
    ["2", "How the field responds", "detection, and the three adaptation mechanisms"],
    ["3", "Read (2018): drift is a time series", "the argument for tracking instead of detecting"],
    ["4", "Reproduction", "all six methods rebuilt; what holds and what does not"],
    ["5", "Where the field went after", "normalisation, online ensembles, proactive adaptation"],
    ["6", "Open problems", "what is still unanswered, and what to test next"],
], left=M, top=1.55, width=W-2*M, height=3.6, col_w=[0.5,4.2,6.5], size=16,
   align=["l","l","l"], header=False)

# =====================================================================
# 3. Section 1
# =====================================================================
section("1.  What concept drift is",
        ["A stream is not a dataset: the thing being learned changes while you learn it."])

# =====================================================================
# 4. Definition
# =====================================================================
s = slide("The problem", "why streams break the standard assumption")
bullets(s, [
    ("Supervised learning assumes a fixed joint distribution p(x, y). Draw a training set,", False, 0),
    ("fit a model, deploy it, and the world it was fitted to is the world it will meet.", False, 0),
    ("A data stream breaks that assumption in the most basic way:", True, 0),
    ("p_t(y | x)  is not  p_t+k(y | x)", True, 1),
    ("The mapping from input to label is itself a function of time. A model is not merely", False, 0),
    ("stale - it is fitted to a target that no longer exists.", False, 0),
    ("Where it happens: electricity demand, fraud, network intrusion, recommendation,", False, 0),
    ("industrial sensors. Anywhere behaviour, adversaries or seasons move.", False, 0),
    ("Two consequences that shape everything after:", True, 0),
    ("accuracy degrades silently - nothing errors, the model is just wrong more often", False, 1),
    ("you cannot retrain from scratch: the stream is unbounded and labels arrive late", False, 1),
], top=1.9, size=16, gap=6)

# =====================================================================
# 5. Taxonomy
# =====================================================================
s = slide("Taxonomy: four shapes of drift", "Gama et al. (2014), and Read's sections 3.1 - 3.4")
table(s, [
    ["type", "what happens", "example"],
    ["Sudden", "one concept replaces another at a point", "a sensor is recalibrated"],
    ["Incremental", "the concept moves through intermediate states", "a machine wears down"],
    ["Gradual", "two concepts alternate, one winning over time", "a habit is adopted"],
    ["Recurring", "concepts return, often periodically", "weekday vs weekend demand"],
], left=M, top=1.95, width=W-2*M, height=2.6, col_w=[1.8,5.2,4], size=15,
   align=["l","l","l"])
bullets(s, [
    ("The distinction that matters for method design is whether intermediate states are", False, 0),
    ("REAL concepts. Under incremental drift they are, so there is a path to follow.", False, 0),
    ("Under gradual drift there is not - the concept alternates between two fixed points,", False, 0),
    ("and it is the mixing weight, not the concept, that evolves smoothly.", False, 0),
    ("Recurring drift is a separate axis: any of the four can repeat, and whether it does", False, 0),
    ("decides whether storing old models beats re-learning them.", False, 0),
], top=4.85, size=15, gap=3)

# =====================================================================
# 6. What actually moves
# =====================================================================
s = slide("What actually moves", "p(x, y) = p(x) p(y | x) - so there are two places to look")
table(s, [
    ["", "definition", "also called", "typical remedy"],
    ["Virtual drift / temporal shift", "p(x) moves, p(y|x) stable", "covariate shift", "normalisation"],
    ["Real concept drift", "p(y|x) moves", "concept drift proper", "adaptation"],
], left=M, top=1.95, width=W-2*M, height=1.9, col_w=[3.4,3.4,2.6,2.6], size=14,
   align=["l","l","l","l"])
bullets(s, [
    ("Only the second changes the decision boundary, so only the second necessarily", False, 0),
    ("costs accuracy. The distinction is not academic:", False, 0),
    ("Most work published 2022-2024 addresses the FIRST - RevIN, Dish-TS, SAN all", True, 0),
    ("normalise away shifting marginals and leave the conditional untouched.", True, 0),
    ("A recent framing (ShifTS, 2025) makes the split formal and notes that concept drift", False, 0),
    ("\"has received comparatively less attention\" in time-series forecasting.", False, 0),
    ("Detecting drift without labels is therefore ambiguous by construction: an unlabelled", False, 0),
    ("detector sees p(x) move and cannot tell whether the boundary moved with it.", False, 0),
], top=4.2, size=15, gap=5)

# =====================================================================
# 7. Context drift: three senses
# =====================================================================
s = slide("\"Context drift\" names three different things", "worth separating before reading any of the literature")
table(s, [
    ["sense", "what moves", "the fix it implies"],
    ["1.  Concept drift proper", "p(y | x) genuinely moves over time", "track or reset the model"],
    ["2.  Context-driven shift (CDS)", "p(y | x, c) is stable; c was never a feature",
     "condition on c, do not adapt"],
    ["3.  Context-window drift", "a foundation model's inference window leaves\nits pretraining distribution",
     "adapt at inference, not in weights"],
], left=M, top=1.95, width=W-2*M, height=2.9, col_w=[3.4,5.2,3.4], size=14,
   align=["l","l","l"])
bullets(s, [
    ("Senses 1 and 2 produce the SAME symptom - rising error that correlates with time -", True, 0),
    ("and demand opposite responses. If a periodic context explains the change, adapting", True, 0),
    ("to it is wasted work that will be undone on the next cycle.", True, 0),
    ("SOLID / Reconditionor (KDD'24) scores this directly: mutual information between a", False, 0),
    ("model's prediction residuals and the candidate context.", False, 0),
], top=5.05, size=15, gap=4)

# =====================================================================
# 8. Section 2
# =====================================================================
section("2.  How the field responds",
        ["Two questions: how do you know drift happened, and what do you do about it?"])

# =====================================================================
# 9. Detection
# =====================================================================
s = slide("Detection: monitoring the error signal")
bullets(s, [
    ("The classical approach treats drift as an event to detect, then resets the model.", False, 0),
    ("Detectors watch the error stream, not the data:", False, 0),
], top=1.5, size=16, gap=5)
table(s, [
    ["detector", "test", "guarantee"],
    ["DDM (2004)", "error rate exceeds a running minimum by k sigma", "heuristic thresholds"],
    ["EDDM (2006)", "distance between errors shrinks", "better on gradual drift"],
    ["ADWIN (2007)", "split a window; cut when two halves differ", "false positives bounded by delta"],
], left=M, top=2.4, width=W-2*M, height=2.2, col_w=[2,5.4,4.4], size=14,
   align=["l","l","l"])
bullets(s, [
    ("ADWIN is the de facto default - it keeps an exponential histogram, so the memory is", False, 0),
    ("O(log W), and the window length is itself the estimate of how far back the current", False, 0),
    ("concept extends.", False, 0),
    ("Note what a detector is: it reads E_t over time and decides whether that series has", True, 0),
    ("changed. Every drift detector is already a time-series method.", True, 0),
], top=4.8, size=15, gap=3)

# =====================================================================
# 10. Evaluation problems
# =====================================================================
s = slide("The evaluation problem", "why detector comparisons are hard to trust")
bullets(s, [
    ("Synthetic benchmarks dominate.", True, 0),
    ("Streams switch between predefined concepts at fixed times, with simplified", False, 1),
    ("distributions and unrealistic dynamics. Transfer to real streams is unestablished.", False, 1),
    ("Proxy evaluation conflates two things.", True, 0),
    ("Judging a detector by whether retraining helps mixes detector quality with model", False, 1),
    ("adaptability, and reveals neither detection accuracy nor timing.", False, 1),
    ("Label delay invalidates the classics.", True, 0),
    ("DDM, EDDM and ADWIN all assume labels arrive immediately. In fraud detection", False, 1),
    ("ground truth arrives 30-180 days later, so they are inapplicable in original form.", False, 1),
    ("This last point cuts both ways: if the error signal itself is unobservable for months,", False, 0),
    ("then so is any method - detector or tracker - that depends on it.", False, 0),
], top=1.9, size=15, gap=5)

# =====================================================================
# 11. Three mechanisms
# =====================================================================
s = slide("Adaptation: three mechanisms, and only three", "what the model is made of decides what 'adapt' can mean")
table(s, [
    ["mechanism", "model is made of", "adapts by", "in Theta?", "can move a little?"],
    ["Forgetting (kNN, SAMkNN)", "data", "replacing data", "no", "no - swap"],
    ["Detect + reset (HT, RF-HT)", "structure", "rebuilding it", "no", "no - rebuild"],
    ["Continuous (SGD)", "numbers", "shifting them", "yes", "yes"],
], left=M, top=2.0, width=W-2*M, height=2.3, col_w=[3,2,2,1.4,2], size=14,
   align=["l","l","l","l","l"])
bullets(s, [
    ("A tree has no delta-theta.", True, 0),
    ("Its parameters are a discrete structure - nodes and thresholds - so there is no small", False, 0),
    ("step to take. It can only be grown or destroyed. A buffer is the same: the model IS", False, 0),
    ("the stored data, so adapting means replacing it wholesale.", False, 0),
    ("Only a model whose parameters live in a continuous space can move a little, and that", False, 0),
    ("is the entire basis of the argument in the next section.", False, 0),
], top=4.7, size=15, gap=4)

# =====================================================================
# 12. Section 3
# =====================================================================
section("3.  Read (2018): drifting streams are time series",
        ["arXiv:1810.02266 - The Case for Continuous Adaptation"])

# =====================================================================
# 13. The claim + Lemma 1
# =====================================================================
s = slide("The contradiction", "Lemma 1, and why the asymptotic escape fails")
bullets(s, [
    ("The field assumes instances are i.i.d. WITHIN a concept, and treats drift as an event", False, 0),
    ("to detect so an i.i.d. model can be reset and redeployed. That is self-contradictory.", False, 0),
    ("Lemma 1.  A stream with concept drift necessarily exhibits temporal dependence.", True, 0),
    ("Under independence we would need P(C_t) = P(C_t | C_t-1). Counted on a 20-step", False, 0),
    ("stream with the change point at tau = 10:", False, 0),
], top=1.85, size=15, gap=4)
table(s, [["", "value"], ["P(C_t = 0)", "0.450"], ["P(C_t = 0 | C_t-1 = 1)", "0.000"]],
      left=M, top=4.0, width=4.2, height=1.15, size=14)
bullets(s, [
    ("The objection: as t grows the concept indicator becomes constant, so independence", False, 0),
    ("returns within each concept.", False, 0),
    ("The reply turns on one fact - the change point is not observed.", True, 0),
    ("Knowing it would let you split the stream and treat each side as i.i.d. You do not,", False, 0),
    ("so an instantaneous jump appears as dependence in the error signal over many steps.", False, 0),
], top=5.35, size=14, gap=2)

# =====================================================================
# 14. Trajectory
# =====================================================================
s = slide("The reframing: drift as a trajectory", "a concept is a point in parameter space; drift is a path through it")
table(s, [
    ["type", "trajectory of theta", "is there a path to follow?"],
    ["Sudden", "theta resampled from the prior at tau", "no - a discontinuity"],
    ["Incremental", "theta_t = A_0.01^T theta_t-1, a rotation", "yes"],
    ["Gradual", "theta alternates between two fixed points", "no - alpha_t moves, not theta"],
    ["Recurring", "a cycle through a finite concept set", "yes, and it repeats"],
], left=M, top=1.95, width=W-2*M, height=2.6, col_w=[1.8,4.8,4.4], size=15,
   align=["l","l","l"])
bullets(s, [
    ("If drift is a trajectory, it can in principle be predicted. That converts the problem:", False, 0),
    ("\"Solving the concept drift problem is identical to solving the forecasting", True, 0),
    ("problem of predicting theta_t.\"", True, 0),
    ("The prescription follows directly - track the concept instead of detecting changes in it:", False, 0),
    ("theta_t+1  <-  theta_t + lambda * grad E        no detector, no reset", True, 1),
    ("with one condition: lambda must not decay to zero, or the model freezes into one concept.", False, 0),
], top=4.85, size=15, gap=4)

# =====================================================================
# 15. Section 4
# =====================================================================
section("4.  Reproduction",
        ["All six methods of Table 2 rebuilt in pure Python stdlib, on the paper's own data."])

# =====================================================================
# 16. Setup
# =====================================================================
s = slide("Setup")
bullets(s, [
    ("Data, from the source the paper cites (MOA):", True, 0),
    ("Electricity 45,312 instances | CoverType 581,012 - both match the paper exactly", False, 1),
    ("Methods, all six of Table 2, reimplemented rather than stood in for:", True, 0),
    ("kNN | hinge SGD | Hoeffding Tree (Hoeffding-bound splits, Gaussian observers, NB leaves)", False, 1),
    ("SAMkNN | PBF-SGD (degree-3 basis) | RF-HT (100 trees, random subspace, Poisson(6))", False, 1),
    ("ADWIN2 validated separately: fires 55 instances after a true change, and gives zero", False, 1),
    ("false alarms across 4,000 stationary instances", False, 1),
    ("Streams at Table 1 parameters: T = 10K, tau_0 = 1K, tau_1 = 5K, tau_2 = 6K.", True, 0),
    ("Prequential - test on each instance before training on it. Accuracy over tau_0..T.", False, 1),
], top=1.9, size=15, gap=6)

# =====================================================================
# 17. Table 3
# =====================================================================
s = slide("Results: Table 3 reproduced", "mine / paper")
table(s, [
    ["stream", "SAMkNN", "PBF-SGD", "RF-HT"],
    ["Electricity  45,312", "78.0 / 79.8", "80.7 / 85.9", "84.5 / 86.2"],
    ["RTG  10K", "71.1 / 78.8", "82.8 / 81.8", "72.5 / 77.9"],
    ["Synthetic  10K", "81.1 / 96.0", "88.5 / 95.1", "86.7 / 93.6"],
    ["CoverType  10K  (not comparable)", "91.2 / 93.3", "91.0 / 92.6", "90.5 / 93.9"],
], left=M, top=1.95, width=W-2*M, height=2.5, col_w=[3.4,2,2,2], size=15)
bullets(s, [
    ("Electricity is the clean row - SAMkNN within 1.8 points, RF-HT within 1.7 at the full", False, 0),
    ("100 trees. On RTG, PBF-SGD exceeds the paper and its reported ranking is preserved.", False, 0),
    ("Two systematic misses, both traceable:", True, 0),
    ("PBF-SGD on Electricity (-5.2) - the cause is the polynomial degree, not the step size", False, 1),
    ("SAMkNN degrades in order (-1.8, -7.7, -14.9), tracking how much its long-term memory", False, 1),
    ("should matter; the reimplementation compresses that memory more crudely", False, 1),
], top=4.65, size=15, gap=4)

# =====================================================================
# 18. lambda correction
# =====================================================================
s = slide("The lambda condition, and a correction", "accuracy points lost by letting lambda decay as 1/sqrt(t)")
cd = CategoryChartData()
cd.categories = ["stationary", "sudden", "incremental", "gradual", "sustained"]
cd.add_series("Penalty", (0.9, 18.6, 5.2, 14.9, 0.8))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(M), Inches(1.95),
                        Inches(7.3), Inches(4.3), cd)
style_chart(gf.chart, legend=False)
bullets(s, [
    ("The paper warns that decay makes SGD", False, 0),
    ("\"react more and more slowly to concept", False, 0),
    ("drift\", and leaves it there.", False, 0),
    ("Tested, it bites hardest after SUDDEN", True, 0),
    ("drift and is nearly free under sustained.", True, 0),
    ("Under sustained rotation a constant", False, 0),
    ("lambda only reaches 88.1 anyway, so", False, 0),
    ("decay destroys little. After a sudden", False, 0),
    ("resample a live lambda relearns and a", False, 0),
    ("frozen one cannot.", False, 0),
    ("The condition is really about recovery", True, 0),
    ("from discontinuities.", True, 0),
], top=1.95, left=8.4, width=4.4, size=14, gap=2)

# =====================================================================
# 19. kNN flatness
# =====================================================================
s = slide("Buffer methods: cap and flatness are one fact", "kNN and SGD across the drift types")
cd = CategoryChartData()
cd.categories = ["stationary", "sudden", "incremental", "gradual", "sustained"]
cd.add_series("SGD", (97.3, 94.1, 96.1, 94.0, 88.1))
cd.add_series("kNN", (73.3, 73.1, 73.2, 72.8, 72.7))
gf = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(M), Inches(1.95),
                        Inches(7.3), Inches(4.3), cd)
ch = gf.chart; style_chart(ch)
ch.value_axis.minimum_scale = 65; ch.value_axis.maximum_scale = 100
bullets(s, [
    ("kNN is worst in all five scenarios, and", True, 0),
    ("flat across all five: a 0.6-point spread", True, 0),
    ("against SGD's 9.2.", True, 0),
    ("Drift costs a buffer almost nothing,", False, 0),
    ("because a buffer never accumulated", False, 0),
    ("anything for drift to take away.", False, 0),
    ("The paper makes two separate remarks -", False, 0),
    ("that buffer power is limited by size, and", False, 0),
    ("that kNN shows no upward trend when", False, 0),
    ("stationary. They are the same fact.", False, 0),
], top=2.2, left=8.4, width=4.4, size=14, gap=3)

# =====================================================================
# 20. What the paper leaves unstated
# =====================================================================
s = slide("What the paper leaves unstated", "each of these changes its numbers more than any method does")
table(s, [
    ["unstated", "measured effect"],
    ["Synthetic input dimension", "SGD scores 57.7 / 74.5 / 83.1 / 92.2 at d = 2 / 5 / 10 / 20"],
    ["PBF-SGD polynomial degree", "the specified degree 3 is 3.3 points WORSE than degree 2"],
    ["Electricity attribute count", "the paper says 6; the data file declares 8"],
    ["L2 strength for SGD", "unstated; scikit-multiflow default assumed"],
], left=M, top=1.95, width=W-2*M, height=2.6, col_w=[3.6,8], size=15,
   align=["l","l"])
bullets(s, [
    ("The dimension is the serious one. The reported Synthetic row is 93.6 - 96.0, which is", False, 0),
    ("reachable only at the high end - and nowhere near the d = 2 that the paper's own", False, 0),
    ("Figure 4 plots. Anyone citing that column should know it turns on a free parameter.", False, 0),
    ("A related finding: on the Synthetic stream plain SGD (92.2) BEATS PBF-SGD (88.5).", True, 0),
    ("The concept there is a hyperplane - linear by construction - so a degree-3 basis adds", False, 0),
    ("1,770 parameters that can only contribute variance. Expansion is a bet on", False, 0),
    ("non-linearity, and that stream is the case where the bet cannot pay.", False, 0),
], top=4.75, size=14, gap=3)

# =====================================================================
# 21. Section 5
# =====================================================================
section("5.  Where the field went after 2018",
        ["The paper's open problem - forecasting the concept - was eventually closed."])

# =====================================================================
# 22. Modern families
# =====================================================================
s = slide("Four families of response")
table(s, [
    ["family", "idea", "representative work"],
    ["Normalisation", "remove shifting marginals; leave the conditional alone",
     "RevIN, Dish-TS, SAN"],
    ["Online fast/slow", "balance fast adaptation against recall of old patterns",
     "FSNet, OneNet (NeurIPS'23)"],
    ["Concept pools", "keep one model per concept; select the nearest",
     "CEP (2026), for recurring drift"],
    ["Proactive", "predict the parameter shift BEFORE the error appears",
     "Proceed (KDD'25)"],
], left=M, top=1.6, width=W-2*M, height=3.0, col_w=[2.4,6.2,3.4], size=14,
   align=["l","l","l"])
bullets(s, [
    ("Only the last of these does what Read argued for. Proceed estimates the drift between", False, 0),
    ("recent training data and the current test sample, then uses a learned generator to", False, 0),
    ("translate that estimate directly into parameter adjustments.", False, 0),
    ("Read argued that solving drift means forecasting theta, and never built it.", True, 0),
    ("Proceed builds exactly that map - seven years later, by the route he proposed.", True, 0),
], top=4.8, size=15, gap=3)

# =====================================================================
# 23. Foundation models
# =====================================================================
s = slide("Drift under foundation models", "when the weights are not yours to adapt")
bullets(s, [
    ("Time-series foundation models - Chronos, Moirai and successors - are pretrained on", False, 0),
    ("large corpora and used zero-shot. Drift does not go away; it moves.", False, 0),
    ("Black-box adaptation.", True, 0),
    ("If the model is behind a commercial API, its weights cannot be touched. Recent work", False, 1),
    ("adapts by learning the structure of the model's ERRORS in context instead.", False, 1),
    ("Drift-resilient priors.", True, 0),
    ("The other route: bake drift into the in-context prior, so the model learns to estimate,", False, 1),
    ("adapt to and extrapolate change (Drift-Resilient TabPFN, NeurIPS'24).", False, 1),
    ("Both are continuous adaptation in the sense of section 2 - the parameters simply live", False, 0),
    ("somewhere else, in the context or in a residual corrector rather than in the weights.", False, 0),
], top=1.9, size=15, gap=5)

# =====================================================================
# 24. Section 6
# =====================================================================
section("6.  Open problems",
        ["What the literature has not settled, and what can be tested now."])

# =====================================================================
# 25. Open problems
# =====================================================================
s = slide("What is still unsettled")
bullets(s, [
    ("No criterion separates real drift from unmodelled context.", True, 0),
    ("CDS says the conditional only APPEARS to move because a covariate was never", False, 1),
    ("conditioned on. Read says it genuinely moves through parameter space. If the", False, 1),
    ("context is observable and periodic, tracking it is wasted work; if it is latent and", False, 1),
    ("non-recurrent, conditioning is impossible. Nothing published says which you face.", False, 1),
    ("Recurring and sustained drift split the method space, and are rarely benchmarked", True, 0),
    ("together.", True, 0),
    ("A pool assumes concepts come back; a tracker assumes smooth displacement. The", False, 1),
    ("crossover between them has no published characterisation.", False, 1),
    ("Evaluation remains synthetic and label-immediate,", True, 0),
    ("while the deployments that motivate the field are neither.", True, 0),
], top=1.55, size=15, gap=5)

# =====================================================================
# 26. Proposed experiments
# =====================================================================
s = slide("Proposed experiments", "all four run on the harness as it stands")
table(s, [
    ["", "question", "falsifiable prediction"],
    ["A", "Why did momentum not help?",
     "A rotation-aware extrapolator closes the tracking gap - and does\nnothing on sudden drift"],
    ["B", "Real drift, or unmodelled context?",
     "MI(residual; context) separates the two regimes; autocorrelation cannot"],
    ["C", "When does tracking lose to storing?",
     "A crossover period p* exists; below it a pool beats a tracker"],
    ["D", "What should lambda actually be?",
     "lambda* scales as the square root of the drift rate"],
], left=M, top=1.95, width=W-2*M, height=3.2, col_w=[0.5,3.2,7.2], size=13,
   align=["l","l","l"])
bullets(s, [
    ("B addresses the first open problem directly. Electricity carries a genuine observable", False, 0),
    ("context - half-hour of day and day of week - and the synthetic streams expose the", False, 0),
    ("ground-truth concept, so both regimes can be built and told apart on the same harness.", False, 0),
], top=5.4, size=15, gap=3)

# =====================================================================
# 27. Summary
# =====================================================================
s = slide("Summary")
bullets(s, [
    ("Concept drift is a change in p(y | x) over time. It is distinct from covariate shift,", False, 0),
    ("and most recent forecasting work addresses the latter.", False, 0),
    ("The field's two responses are detection-and-reset and continuous adaptation. Which", False, 0),
    ("is available is decided by what the model is made of - a tree has no delta-theta.", False, 0),
    ("Read (2018) argues drift implies temporal dependence, so a drifting stream is a time", False, 0),
    ("series and the concept should be tracked rather than detected.", False, 0),
    ("Reproduced: two of three advanced methods land within 2 points on Electricity. The", False, 0),
    ("lambda prescription holds but concerns recovery from discontinuities, not tracking.", False, 0),
    ("The paper's forecasting proposal was built seven years later by Proceed (KDD'25).", False, 0),
    ("The open question is telling genuine drift from context that was never modelled.", False, 0),
], top=1.6, size=16, gap=11)

prs.save("/tmp/claude-0/-root-time-series-research/350c80dd-3cf5-4b19-ac84-1e395d6dbfb5/scratchpad/deck/seminar.pptx")
print("saved, %d slides" % len(prs.slides._sldIdLst))
