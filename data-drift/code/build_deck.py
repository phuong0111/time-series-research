"""Seminar deck: concept drift. White background, black text, formulae."""
import re
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from lxml import etree

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

# Openers that must keep their case: maths, and names whose first letter is
# deliberately lower ("kNN"). Anything else gets a sentence-initial capital.
_KEEP = ("p(", "p_", "kNN", "I(", "g_", "d ", "d =", "n ", "τ", "θ", "λ", "α",
         "δ", "σ", "Δ", "Θ", "√", "E_", "c_", "A^")


def _cap(text):
    """Capitalise the first letter of a sentence, leaving identifiers alone."""
    t = text.lstrip()
    if not t or not t[0].isascii() or not t[0].isalpha() or t[0].isupper():
        return text
    if any(t.startswith(k) for k in _KEEP):
        return text
    i = len(text) - len(t)
    return text[:i] + t[0].upper() + t[1:]


def _borders(cell, color="000000", w=9525):
    """Draw all four cell edges. python-pptx exposes no border API, so the
    line elements are written directly -- and in schema order (lnL, lnR, lnT,
    lnB) ahead of the fill, or PowerPoint rejects the part."""
    tcPr = cell._tc.get_or_add_tcPr()
    for idx, tag in enumerate(("a:lnL", "a:lnR", "a:lnT", "a:lnB")):
        for old in tcPr.findall(qn(tag)):
            tcPr.remove(old)
        ln = etree.Element(qn(tag))
        ln.set("w", str(w)); ln.set("cap", "flat")
        ln.set("cmpd", "sng"); ln.set("algn", "ctr")
        fill = etree.SubElement(ln, qn("a:solidFill"))
        etree.SubElement(fill, qn("a:srgbClr")).set("val", color)
        tcPr.insert(idx, ln)


def note(s, text):
    s.notes_slide.notes_text_frame.text = text
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
        tb = s.shapes.add_textbox(Inches(M), Inches(0.35), Inches(W-2*M), Inches(1.0))
        tf = tb.text_frame; tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_bottom = 0
        _emit(tf.paragraphs[0], title, 44, bold=True)
    if subtitle:
        tb = s.shapes.add_textbox(Inches(M), Inches(1.42), Inches(W-2*M), Inches(0.5))
        tf = tb.text_frame; tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_bottom = 0
        _emit(tf.paragraphs[0], subtitle, 22)
    return s


def bullets(s, items, top=2.2, left=M, width=None, size=28, gap=14):
    width = width or (W - 2*M)
    tb = s.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(H-top-0.5))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_bottom = 0
    for i, (text, bold, lvl) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.level, p.space_after = lvl, Pt(gap)
        _emit(p, _cap(text), size - 1*lvl, bold=bold)
    return tb


def eq(s, text, top, left=M, size=32, width=None):
    """A display formula, set in a math face."""
    tb = s.shapes.add_textbox(Inches(left), Inches(top),
                              Inches(width or (W-2*M)), Inches(0.8))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_bottom = 0
    _emit(tf.paragraphs[0], text, size, italic=True, font=MATH)
    return tb


def table(s, rows, left, top, width, height, col_w=None, size=22,
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
            _borders(c)
            c.margin_left = c.margin_right = Inches(0.08)
            c.margin_top = c.margin_bottom = Inches(0.03)
            c.fill.solid(); c.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            p = c.text_frame.paragraphs[0]
            a = align[j] if align else ("l" if j == 0 else "r")
            p.alignment = PP_ALIGN.LEFT if a == "l" else PP_ALIGN.RIGHT
            _emit(p, _cap(str(val)), size, bold=(i == 0 and header))
    return tbl


def style_chart(chart, legend=True, num_fmt="0.0"):
    chart.font.size = Pt(16); chart.font.name = FONT; chart.font.color.rgb = BLACK
    chart.has_title = False
    if legend:
        chart.has_legend = True
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(16); chart.legend.font.color.rgb = BLACK
    else:
        chart.has_legend = False
    va = chart.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = RULE
    va.major_gridlines.format.line.width = Pt(0.75)
    va.tick_labels.font.size = Pt(15); va.tick_labels.font.color.rgb = BLACK
    va.format.line.color.rgb = RULE
    ca = chart.category_axis
    ca.has_major_gridlines = False
    ca.tick_labels.font.size = Pt(16); ca.tick_labels.font.color.rgb = BLACK
    ca.format.line.color.rgb = BLACK
    pl = chart.plots[0]
    pl.has_data_labels = True
    dl = pl.data_labels
    dl.font.size = Pt(15); dl.font.color.rgb = BLACK; dl.font.name = FONT
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
    _emit(tf.paragraphs[0], label, 44, bold=True)
    bullets(s, [(line, False, 0)], top=4.0, size=24)
    return s


# Ghi chú cho người trình bày (tiếng Việt), theo thứ tự slide.
NOTES = [
# 1 Title
"Giới thiệu: bài trình bày gồm ba phần — khái niệm trôi (concept drift) là gì, "
"cách cộng đồng nghiên cứu xử lý nó, và kết quả tái lập bài báo Read (2018). "
"Phần tái lập chỉ là một mục trong sáu mục, không phải trọng tâm duy nhất.",
# 2 Outline
"Nêu nhanh sáu phần. Nhấn mạnh mạch bài: từ định nghĩa bài toán, sang phương pháp, "
"rồi đến một lập luận cụ thể, phần kiểm chứng bằng thực nghiệm, và cuối cùng là "
"các câu hỏi còn bỏ ngỏ.",
# 3 Section 1
"Chuyển sang phần định nghĩa bài toán. Ý chính: phân phối mục tiêu không cố định "
"mà thay đổi theo thời gian.",
# 4 The problem
"Học máy truyền thống giả định phân phối đồng thời p(x, y) cố định — mô hình khớp "
"với mẫu huấn luyện thì cũng khớp với dữ liệu triển khai. Luồng dữ liệu phá vỡ giả "
"định đó. Nhấn mạnh: mô hình không chỉ 'cũ' mà là 'sai đặc tả', vì nó ước lượng một "
"mục tiêu không còn tồn tại. Hai hệ quả quan trọng: suy giảm diễn ra âm thầm (không "
"có lỗi nào được báo), và không thể huấn luyện lại từ đầu vì luồng là vô hạn và nhãn "
"đến muộn.",
# 5 Taxonomy
"Bốn dạng trôi theo phân loại kinh điển. Cột thứ ba là cột quan trọng nhất cho việc "
"thiết kế phương pháp: chỉ trôi tăng dần (incremental) mới tạo ra các trạng thái "
"trung gian là khái niệm thật, tức là có một quỹ đạo để bám theo. Trôi dần dần "
"(gradual) chỉ là sự pha trộn giữa hai khái niệm cố định.",
# 6 Which factor
"Phân tích phân phối đồng thời thành hai thừa số cho thấy có đúng hai chỗ có thể "
"thay đổi. Chỉ thay đổi ở phân phối có điều kiện mới làm dịch chuyển biên quyết định, "
"nên chỉ nó mới nhất thiết làm giảm độ chính xác. Điểm đáng lưu ý: phần lớn công trình "
"gần đây về dự báo chuỗi thời gian lại xử lý thừa số thứ nhất.",
# 7 Context drift
"Thuật ngữ 'context drift' được dùng cho ba hiện tượng khác nhau. Nghĩa thứ nhất và "
"thứ hai biểu hiện giống hệt nhau — sai số tăng theo thời gian — nhưng đòi hỏi cách "
"xử lý ngược nhau. Nếu một ngữ cảnh có chu kỳ giải thích được sự thay đổi thì việc "
"thích nghi là lãng phí, vì chu kỳ sau sẽ đảo ngược nó.",
# 8 Section 2
"Chuyển sang phần phương pháp: phát hiện trôi, và thích nghi sau khi trôi đã xảy ra.",
# 9 Detection
"Các bộ phát hiện không quan sát dữ liệu mà quan sát chuỗi sai số. ADWIN là lựa chọn "
"mặc định trên thực tế vì có cận sai dương rõ ràng và bộ nhớ chỉ O(log W). Điểm cần "
"nhấn: một bộ phát hiện trôi thực chất đang hỏi 'chuỗi thời gian này có thay đổi không', "
"nên bản thân nó đã là một phương pháp chuỗi thời gian.",
# 10 Evaluation
"Ba hạn chế của quy trình đánh giá hiện hành. Hạn chế thứ ba là nghiêm trọng nhất "
"trong thực tế: các bộ phát hiện kinh điển đều giả định nhãn có ngay lập tức, trong "
"khi ở bài toán gian lận thẻ, nhãn đến sau 30–180 ngày. Nếu tín hiệu sai số không "
"quan sát được trong nhiều tháng thì mọi phương pháp dựa vào nó đều không dùng được.",
# 11 Mechanisms
"Đây là slide quan trọng nhất của phần này. Cơ chế thích nghi khả dụng được quyết "
"định bởi mô hình được cấu tạo từ cái gì. Cây quyết định có tham số là một cấu trúc "
"rời rạc nên không tồn tại bước dịch chuyển nhỏ — chỉ có thể mọc thêm hoặc phá đi. "
"Bộ đệm cũng vậy: mô hình chính là dữ liệu lưu trữ. Chỉ mô hình có tham số liên tục "
"mới bám theo được khái niệm.",
# 12 Section 3
"Chuyển sang bài báo Read (2018), nền tảng cho phần tái lập tiếp theo.",
# 13 Lemma 1
"Lập luận cốt lõi. Cộng đồng giả định dữ liệu độc lập cùng phân phối trong mỗi khái "
"niệm, nhưng trôi khái niệm chính là sự thay đổi khái niệm đó — nên giả định tự mâu "
"thuẫn. Con số minh họa được đếm trực tiếp trên luồng 20 bước. Điểm then chốt: thời "
"điểm đổi τ không quan sát được. Nếu biết τ thì có thể cắt luồng làm đôi và toàn bộ "
"lập luận sụp đổ; vì không biết, một bước nhảy tức thời biểu hiện thành phụ thuộc "
"thời gian kéo dài trong tín hiệu sai số.",
# 14 Trajectory
"Cách diễn đạt lại: mỗi khái niệm là một điểm trong không gian tham số, trôi là một "
"quỹ đạo. Nếu là quỹ đạo thì về nguyên tắc có thể dự báo được, và bài toán trôi khái "
"niệm trở thành bài toán dự báo tham số. Công thức cuối là toàn bộ đơn thuốc của bài "
"báo: bám theo, không cần bộ phát hiện, không cần khởi tạo lại.",
# 15 Section 4
"Chuyển sang phần thực nghiệm: cài đặt lại toàn bộ sáu phương pháp trong Bảng 2 bằng "
"thư viện chuẩn của Python, chạy trên chính dữ liệu của bài báo.",
# 16 Setup
"Số lượng mẫu của hai tập dữ liệu khớp chính xác với con số bài báo nêu. Các phương "
"pháp được cài đặt lại chứ không thay thế bằng mô hình tương đương — kể cả cây "
"Hoeffding và ADWIN2. ADWIN2 được kiểm chứng riêng: phát hiện sau 55 mẫu kể từ điểm "
"đổi thật, và không có báo động giả nào trên 4.000 mẫu dừng.",
# 17 Results
"Electricity tái lập tốt: hai trong ba phương pháp nâng cao lệch dưới 2 điểm. "
"PBF-SGD lệch 5,2 điểm — nguyên nhân nằm ở bậc đa thức chứ không phải tốc độ học, "
"sẽ nói rõ ở slide sau. CoverType không so sánh được vì bài báo phân loại đủ bảy lớp "
"còn ở đây rút về nhị phân.",
# 18 Lambda
"Bài báo nêu điều kiện không được để tốc độ học giảm về 0, nhưng không có thực nghiệm "
"tách riêng. Kết quả cho thấy hình phạt lớn nhất là sau trôi đột ngột (18,6 điểm) và "
"gần như bằng không dưới trôi kéo dài (0,8 điểm) — ngược với trực giác. Lý do: dưới "
"trôi kéo dài, tốc độ học hằng số cũng chỉ đạt 88,1 nên việc giảm không làm mất thêm "
"gì; còn sau khi khái niệm bị lấy mẫu lại, tốc độ học còn sống thì học lại được, "
"đóng băng thì không.",
# 19 Buffer
"Đường kNN gần như nằm ngang qua cả năm kịch bản — biên độ 0,6 điểm so với 9,2 điểm "
"của SGD. Trôi gần như không làm kNN tệ đi, vì kNN chưa bao giờ tích lũy được gì để "
"trôi làm hỏng. Bài báo nêu hai nhận xét riêng biệt (khả năng bị chặn bởi kích thước "
"bộ đệm, và không có xu hướng tăng khi dừng); thực ra đó là cùng một tính chất.",
# 20 Unstated
"Ba tham số bài báo không nêu, trong đó số chiều dữ liệu tổng hợp là quan trọng nhất: "
"nó đưa SGD từ 57,7 lên 92,2. Nghĩa là hàng Synthetic trong Bảng 3 chỉ đạt được ở số "
"chiều lớn, không phải ở d = 2 như chính Hình 4 của bài báo vẽ. Ai trích dẫn cột đó "
"nên biết điều này.",
# 21 Section 5
"Chuyển sang các công trình sau 2018 — đặc biệt là công trình đã hiện thực hóa đúng "
"điều Read đề xuất.",
# 22 Families
"Bốn hướng tiếp cận chính hiện nay. Chỉ hướng cuối cùng thực sự làm điều Read lập "
"luận: Proceed ước lượng độ trôi giữa dữ liệu huấn luyện gần nhất và mẫu kiểm tra "
"hiện tại, rồi ánh xạ ước lượng đó thành điều chỉnh tham số qua một bộ sinh được học. "
"Read lập luận nhưng không xây dựng; bảy năm sau Proceed xây dựng đúng ánh xạ đó.",
# 23 Foundation models
"Với mô hình nền tảng, trôi khái niệm không biến mất mà chuyển vị trí. Nếu mô hình "
"được phục vụ qua API thì không thể sửa trọng số, nên phải thích nghi bằng cách học "
"cấu trúc sai số trong ngữ cảnh. Cả hai hướng vẫn là thích nghi liên tục theo nghĩa "
"ở phần 2 — chỉ khác là tham số nằm ở chỗ khác.",
# 24 Section 6
"Chuyển sang phần cuối: những gì còn bỏ ngỏ và những thí nghiệm có thể làm ngay.",
# 25 Open problems
"Vấn đề mở quan trọng nhất là vấn đề thứ nhất: chưa có tiêu chí nào phân biệt trôi "
"thật với ngữ cảnh bị bỏ sót. Hai cách giải thích đòi hỏi hai cách xử lý ngược nhau, "
"mà không có công trình nào chỉ ra đang ở trường hợp nào.",
# 26 Proposed
"Bốn thí nghiệm, mỗi thí nghiệm nêu kèm một dự đoán có thể bị bác bỏ — đó là điều "
"phân biệt đề xuất với mong muốn. Nếu trình bày thiếu thời gian, hãy ưu tiên thí "
"nghiệm B: nó trả lời trực tiếp vấn đề mở thứ nhất, và dữ liệu Electricity đã sẵn có "
"ngữ cảnh chu kỳ quan sát được.",
# 27 Summary
"Tóm tắt sáu ý. Nếu còn thời gian, nên kết thúc bằng câu hỏi mở ở slide trước thay vì "
"bằng slide tóm tắt — kết ở một câu hỏi mình có điều kiện trả lời sẽ mở ra trao đổi.",
]



# 1. Title -----------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
tb = s.shapes.add_textbox(Inches(M), Inches(2.3), Inches(W-2*M), Inches(1.8))
tf = tb.text_frame; tf.word_wrap = True; tf.margin_left = 0
_emit(tf.paragraphs[0], "Concept Drift in Data Streams", 48, bold=True)
_emit(tf.add_paragraph(), "Formulation, methods, and a reproduction", 26)
bullets(s, [("Seminar presentation", False, 0)], top=4.9, size=22)

# 2. Outline ---------------------------------------------------------------
s = slide("Outline")
bullets(s, [
    ("1.   Formulation", False, 0),
    ("2.   Methods", False, 0),
    ("3.   Read (2018)", False, 0),
    ("4.   Reproduction", False, 0),
    ("5.   Subsequent work", False, 0),
    ("6.   Open problems", False, 0),
], top=1.85, size=30, gap=16)

# 3. Section 1 -------------------------------------------------------------
section("1.  Formulation", "The target distribution is a function of time.")

# 4. Definition ------------------------------------------------------------
s = slide("The problem")
bullets(s, [
    ("Batch learning assumes a fixed joint law p(x, y).", False, 0),
    ("In a stream that law itself evolves:", False, 0),
], top=1.75, size=28, gap=12)
eq(s, "p_{t}(y | x)   ≠   p_{t+k}(y | x)", top=3.15, size=36)
bullets(s, [
    ("A deployed model is not stale but misspecified.", False, 0),
    ("Two consequences:", True, 0),
    ("degradation is silent", False, 1),
    ("retraining from scratch is unavailable", False, 1),
], top=4.35, size=28, gap=10)

# 5. Taxonomy --------------------------------------------------------------
s = slide("Taxonomy", "Gama et al. (2014); Read §3")
table(s, [
    ["type", "behaviour", "intermediate states"],
    ["Sudden", "one concept replaces another", "none"],
    ["Incremental", "advances stepwise", "genuine concepts"],
    ["Gradual", "two concepts alternate", "no new concepts"],
    ["Recurring", "concepts return periodically", "previously seen"],
], left=M, top=2.25, width=W-2*M, height=2.7, col_w=[2.4,5.0,3.6], size=24,
   align=["l","l","l"])
bullets(s, [
    ("Only incremental drift offers a path to follow.", False, 0),
], top=5.5, size=28)

# 6. Which factor ----------------------------------------------------------
s = slide("Which factor moves")
eq(s, "p(x, y)   =   p(x) · p(y | x)", top=1.7, size=36)
table(s, [
    ["", "changes", "remedy"],
    ["Virtual drift", "p(x)", "normalisation"],
    ["Real concept drift", "p(y | x)", "adaptation"],
], left=M, top=2.9, width=9.6, height=1.9, col_w=[3.4,3,3], size=24,
   align=["l","l","l"])
bullets(s, [
    ("Only the second moves the decision boundary.", False, 0),
    ("Most recent work addresses the first.", False, 0),
], top=5.2, size=28, gap=10)

# 7. Context drift ---------------------------------------------------------
s = slide("Three referents of “context drift”")
table(s, [
    ["sense", "what changes", "response"],
    ["Concept drift", "p(y | x) changes with t", "track the model"],
    ["Context-driven shift", "p(y | x, c) fixed; c omitted", "condition on c"],
    ["Context-window", "leaves the pretraining law", "adapt at inference"],
], left=M, top=1.9, width=W-2*M, height=2.5, col_w=[3.2,4.8,3.4], size=23,
   align=["l","l","l"])
bullets(s, [
    ("The first two share a symptom and need opposite fixes.", True, 0),
    ("SOLID scores the second by", False, 0),
], top=4.75, size=26, gap=8)
eq(s, "I(E_{t} ; c_{t})", top=6.2, size=32)

# 8. Section 2 -------------------------------------------------------------
section("2.  Methods", "Detecting drift, and adapting once it has occurred.")

# 9. Detection -------------------------------------------------------------
s = slide("Drift detection", "detectors observe the error sequence")
table(s, [
    ["detector", "test statistic", "guarantee"],
    ["DDM", "error exceeds a running minimum", "heuristic"],
    ["EDDM", "distance between errors contracts", "better on gradual"],
    ["ADWIN", "cut the window if halves differ", "false positives ≤ δ"],
], left=M, top=2.25, width=W-2*M, height=2.8, col_w=[2,5.4,3.6], size=23,
   align=["l","l","l"])
bullets(s, [
    ("A detector asks whether the series E_{t} has changed.", False, 0),
    ("Every detector is already a time-series method.", True, 0),
], top=5.35, size=27, gap=8)

# 10. Evaluation -----------------------------------------------------------
s = slide("Limits of the evaluation protocol")
bullets(s, [
    ("Synthetic benchmarks predominate.", True, 0),
    ("transfer to real data is unestablished", False, 1),
    ("Proxy evaluation conflates two quantities.", True, 0),
    ("detector quality with model adaptability", False, 1),
    ("Verification latency invalidates the classics.", True, 0),
    ("fraud labels arrive after 30–180 days", False, 1),
], top=1.9, size=28, gap=12)

# 11. Mechanisms -----------------------------------------------------------
s = slide("Three adaptation mechanisms")
table(s, [
    ["mechanism", "representation", "admits Δθ?"],
    ["Forgetting — kNN", "stored data", "no"],
    ["Detect and reset — HT", "a structure", "no"],
    ["Continuous — SGD", "a vector", "yes"],
], left=M, top=1.85, width=10.6, height=2.7, col_w=[4.2,3.4,2.4], size=24,
   align=["l","l","l"])
bullets(s, [
    ("A tree admits no Δθ.", True, 0),
    ("Its parameters are discrete, so no small step exists.", False, 0),
    ("Only a continuous parameter can be tracked.", False, 0),
], top=4.9, size=27, gap=8)

# 12. Section 3 ------------------------------------------------------------
section("3.  Read (2018)", "Concept-drifting Data Streams are Time Series.")

# 13. Lemma 1 --------------------------------------------------------------
s = slide("The contradiction")
bullets(s, [
    ("Lemma 1.  Drift implies temporal dependence.", True, 0),
    ("Independence would require P(C_{t}) = P(C_{t} | C_{t−1}):", False, 0),
], top=1.8, size=28, gap=10)
eq(s, "P(C_{t}=0) = 0.450      P(C_{t}=0 | C_{t−1}=1) = 0.000", top=3.3, size=30)
bullets(s, [
    ("The change point τ is not observed.", True, 0),
    ("Knowing τ would permit partitioning the stream.", False, 0),
    ("Absent that, a jump appears as dependence in E_{t}.", False, 0),
], top=4.5, size=28, gap=10)

# 14. Trajectory -----------------------------------------------------------
s = slide("Drift as a trajectory", "a concept is a point θ ∈ Θ")
table(s, [
    ["type", "trajectory", "path?"],
    ["Sudden", "θ resampled at τ", "no"],
    ["Incremental", "θ_{t} = A^{⊤}θ_{t−1}", "yes"],
    ["Gradual", "θ alternates; α_{t} evolves", "no"],
    ["Recurring", "a cycle of concepts", "yes"],
], left=M, top=2.25, width=9.4, height=2.9, col_w=[2.6,4.4,2],  size=24,
   align=["l","l","l"])
bullets(s, [
    ("A trajectory is predictable, so track θ rather than detect:", False, 0),
], top=5.35, size=26)
eq(s, "θ_{t+1}   ←   θ_{t} + λ ∇E", top=6.15, size=36)

# 15. Section 4 ------------------------------------------------------------
section("4.  Reproduction", "Table 2's six methods rebuilt in the standard library.")

# 16. Setup ----------------------------------------------------------------
s = slide("Experimental setup")
bullets(s, [
    ("Electricity 45,312 and CoverType 581,012", False, 0),
    ("counts exact against the paper", False, 1),
    ("All six methods of Table 2 reimplemented", False, 0),
    ("ADWIN2 validated: 55-instance latency, no false alarms", False, 1),
    ("Table 1 parameters, prequential over τ_{0} … T", False, 0),
], top=2.0, size=28, gap=14)

# 17. Results --------------------------------------------------------------
s = slide("Results: Table 3", "reproduced / reported")
table(s, [
    ["stream", "SAMkNN", "PBF-SGD", "RF-HT"],
    ["Electricity", "78.0 / 79.8", "80.7 / 85.9", "84.5 / 86.2"],
    ["RTG", "71.1 / 78.8", "82.8 / 81.8", "72.5 / 77.9"],
    ["Synthetic", "81.1 / 96.0", "88.5 / 95.1", "86.7 / 93.6"],
    ["CoverType †", "91.2 / 93.3", "91.0 / 92.6", "90.5 / 93.9"],
], left=M, top=2.25, width=W-2*M, height=3.0, col_w=[3,2.6,2.6,2.6], size=24)
bullets(s, [
    ("Electricity reproduces within 2 points.", False, 0),
    ("PBF-SGD (−5.2) is the deviation; the cause is the degree.", False, 0),
], top=5.6, size=26, gap=8)

# 18. lambda ---------------------------------------------------------------
s = slide("The condition on λ", "accuracy lost under λ_{t} = λ_{0} / √t")
cd = CategoryChartData()
cd.categories = ["stationary", "sudden", "incremental", "gradual", "sustained"]
cd.add_series("Penalty", (0.9, 18.6, 5.2, 14.9, 0.8))
style_chart(s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(M), Inches(2.2),
                               Inches(W-2*M), Inches(3.4), cd).chart, legend=False)
bullets(s, [
    ("Largest after sudden drift; negligible under sustained.", True, 0),
    ("The condition concerns recovery, not tracking.", False, 0),
], top=5.75, size=25, gap=6)

# 19. kNN ------------------------------------------------------------------
s = slide("Buffer methods", "capacity and insensitivity are one property")
cd = CategoryChartData()
cd.categories = ["stationary", "sudden", "incremental", "gradual", "sustained"]
cd.add_series("SGD", (97.3, 94.1, 96.1, 94.0, 88.1))
cd.add_series("kNN", (73.3, 73.1, 73.2, 72.8, 72.7))
ch = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(M), Inches(2.2),
                        Inches(W-2*M), Inches(3.4), cd).chart
style_chart(ch)
ch.value_axis.minimum_scale = 65; ch.value_axis.maximum_scale = 100
bullets(s, [
    ("kNN varies by 0.6 points; SGD by 9.2.", True, 0),
    ("A buffer accumulates nothing for drift to invalidate.", False, 0),
], top=5.75, size=25, gap=6)

# 20. Unstated -------------------------------------------------------------
s = slide("Unstated parameters")
table(s, [
    ["parameter", "measured effect"],
    ["Synthetic dimension", "SGD 57.7 → 92.2 as d = 2 → 20"],
    ["PBF-SGD degree", "degree 3 is 3.3 points below degree 2"],
    ["Electricity attributes", "stated as 6; the file declares 8"],
], left=M, top=1.9, width=W-2*M, height=2.6, col_w=[4,7.6], size=24,
   align=["l","l"])
bullets(s, [
    ("The reported Synthetic row needs large d.", False, 0),
    ("It is not attainable at the d = 2 of Figure 4.", False, 0),
], top=4.85, size=27, gap=8)

# 21. Section 5 ------------------------------------------------------------
section("5.  Subsequent work", "The forecasting problem Read posed was solved in 2025.")

# 22. Families -------------------------------------------------------------
s = slide("Four families of response")
table(s, [
    ["family", "principle", "work"],
    ["Normalisation", "remove shifting marginals", "RevIN, SAN"],
    ["Online fast/slow", "adapt vs recall old patterns", "FSNet, OneNet"],
    ["Concept pools", "one model per concept", "CEP"],
    ["Proactive", "predict the parameter shift", "Proceed"],
], left=M, top=1.85, width=W-2*M, height=2.9, col_w=[3.2,5.2,3.2], size=23,
   align=["l","l","l"])
bullets(s, [
    ("Only Proceed realises Read's proposal.", False, 0),
    ("It maps drift to a parameter adjustment:", False, 0),
], top=5.05, size=26, gap=6)
eq(s, "Δθ   =   g_{φ}(Δĉ)", top=6.35, size=32)

# 23. Foundation models ----------------------------------------------------
s = slide("Drift under foundation models")
bullets(s, [
    ("Pretrained models are applied zero-shot; drift persists.", False, 0),
    ("Black-box adaptation.", True, 0),
    ("weights are unavailable — learn the error structure", False, 1),
    ("Drift-resilient priors.", True, 0),
    ("build change into the in-context prior", False, 1),
    ("Both are continuous adaptation.", False, 0),
    ("The parameters merely reside elsewhere.", False, 0),
], top=1.9, size=28, gap=11)

# 24. Section 6 ------------------------------------------------------------
section("6.  Open problems", "What remains unresolved, and what can now be tested.")

# 25. Open problems --------------------------------------------------------
s = slide("Unresolved questions")
bullets(s, [
    ("No criterion separates real drift from omitted context.", True, 0),
    ("tracking a periodic context is wasted work", False, 1),
    ("Recurrence and sustained drift partition the methods.", True, 0),
    ("the crossover has no published characterisation", False, 1),
    ("Evaluation is synthetic and label-immediate.", True, 0),
    ("the motivating applications are neither", False, 1),
], top=1.9, size=28, gap=12)

# 26. Proposed -------------------------------------------------------------
s = slide("Proposed experiments", "each a falsifiable prediction")
table(s, [
    ["", "question", "prediction"],
    ["A", "Why no gain from momentum?", "a rotation-aware extrapolator\ncloses the gap"],
    ["B", "Drift, or omitted context?", "I(E_{t} ; c_{t}) separates them"],
    ["C", "Tracking or storage?", "a crossover period p* exists"],
    ["D", "What value should λ take?", "λ* ∝ √(drift rate)"],
], left=M, top=2.25, width=W-2*M, height=3.3, col_w=[0.5,4.6,6.5], size=23,
   align=["l","l","l"])
bullets(s, [
    ("B is testable on the present harness.", False, 0),
], top=5.9, size=27)

# 27. Summary --------------------------------------------------------------
s = slide("Summary")
bullets(s, [
    ("Drift is a change in p(y | x), distinct from covariate shift.", False, 0),
    ("A tree admits no Δθ; only a vector can be tracked.", False, 0),
    ("Two of three methods reproduce within 2 points.", False, 0),
    ("The condition on λ concerns recovery, not tracking.", False, 0),
    ("Proceed realises the forecasting proposal.", False, 0),
    ("Open: separating drift from context never modelled.", False, 0),
], top=1.9, size=28, gap=14)


# --- Ghi chú người trình bày ------------------------------------------------
assert len(NOTES) == len(prs.slides._sldIdLst), (
    "NOTES has %d entries for %d slides" % (len(NOTES), len(prs.slides._sldIdLst)))
for _sl, _txt in zip(prs.slides, NOTES):
    _sl.notes_slide.notes_text_frame.text = _txt

prs.save("/tmp/claude-0/-root-time-series-research/350c80dd-3cf5-4b19-ac84-1e395d6dbfb5/scratchpad/deck/seminar.pptx")
print("saved, %d slides" % len(prs.slides._sldIdLst))
