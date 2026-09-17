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
# Mỗi ghi chú gồm: ý cần nói, số liệu cần dẫn, và câu hỏi có thể gặp.
NOTES = [
# 1 --------------------------------------------------------------------------
"MỞ ĐẦU (~1 phút). Bài gồm ba khối: (a) trôi khái niệm là gì và cộng đồng xử lý ra "
"sao — đây là phần khảo sát, chiếm nhiều nhất; (b) một lập luận cụ thể của Read "
"(2018) và kết quả tái lập của mình; (c) các vấn đề còn mở.\n\n"
"Nói rõ ngay từ đầu rằng phần tái lập chỉ là một trong sáu mục, để người nghe không "
"chờ đợi một bài báo cáo thực nghiệm thuần túy.\n\n"
"Phân bổ thời gian gợi ý: phần 1–2 khoảng 12 phút, phần 3 khoảng 6 phút, phần 4 "
"khoảng 10 phút, phần 5–6 khoảng 7 phút.",
# 2 --------------------------------------------------------------------------
"DÀN Ý (~30 giây). Đọc lướt sáu mục, không giải thích từng mục.\n\n"
"Mạch lập luận cần làm rõ: bài toán (1) → cách xử lý hiện có (2) → một lập luận cụ "
"thể nói rằng cách xử lý phổ biến là sai hướng (3) → kiểm chứng lập luận đó bằng thực "
"nghiệm (4) → những gì đã xảy ra sau đó (5) → những gì còn lại (6).\n\n"
"Nếu bị hỏi 'tại sao chọn bài báo 2018 cũ như vậy', trả lời trước: vì đề xuất trong "
"đó mãi đến 2025 mới được hiện thực hóa, và đó chính là nội dung phần 5.",
# 3 --------------------------------------------------------------------------
"CHUYỂN MỤC. Một câu: 'Trước hết cần định nghĩa chính xác bài toán, vì thuật ngữ "
"trong lĩnh vực này được dùng khá lỏng lẻo.'",
# 4 --------------------------------------------------------------------------
"BÀI TOÁN (~2 phút). Bắt đầu từ giả định của học máy truyền thống: phân phối đồng "
"thời p(x, y) cố định, nên mô hình khớp với mẫu huấn luyện thì cũng khớp với dữ liệu "
"triển khai. Luồng dữ liệu phá vỡ đúng giả định này.\n\n"
"Nhấn mạnh cách diễn đạt: mô hình không 'cũ' mà 'sai đặc tả' (misspecified) — nó ước "
"lượng một mục tiêu không còn tồn tại. Đây không phải vấn đề thiếu dữ liệu.\n\n"
"Ví dụ thực tế nên nêu 1–2 cái: nhu cầu điện (thói quen tiêu dùng, thời tiết), phát "
"hiện gian lận (đối thủ thay đổi chiến thuật), phát hiện xâm nhập mạng.\n\n"
"Hai hệ quả là phần quan trọng nhất slide này: (1) suy giảm âm thầm — không có "
"exception nào được ném ra, chỉ có độ chính xác tụt dần, nên nếu không đo thì không "
"biết; (2) không thể huấn luyện lại từ đầu — luồng vô hạn, và nhãn thường đến muộn "
"(sẽ quay lại ý này ở slide 10).",
# 5 --------------------------------------------------------------------------
"PHÂN LOẠI (~2 phút). Bốn dạng theo Gama et al. (2014), Read dùng lại ở mục 3.\n\n"
"Ví dụ nhanh cho từng dạng: đột ngột — cảm biến được hiệu chuẩn lại; tăng dần — máy "
"móc mòn đi theo thời gian; dần dần — thói quen người dùng chuyển từ A sang B; lặp "
"lại — nhu cầu điện ngày thường so với cuối tuần.\n\n"
"Cột thứ ba mới là cột đáng nói. Với trôi tăng dần, các trạng thái trung gian là "
"khái niệm THẬT, tức tồn tại một quỹ đạo liên tục để bám theo. Với trôi dần dần thì "
"không: chỉ có hai khái niệm cố định và một trọng số pha trộn α thay đổi — nên không "
"có quỹ đạo nào để dự báo. Ý này sẽ được dùng lại ở slide 14, nên cần nói kỹ ở đây.\n\n"
"Trôi lặp lại là một trục riêng, không loại trừ ba dạng kia: bất kỳ dạng nào cũng có "
"thể lặp.",
# 6 --------------------------------------------------------------------------
"HAI VỊ TRÍ THAY ĐỔI (~2 phút). Viết phân tích p(x, y) = p(x)·p(y|x) lên bảng nếu "
"có, vì cả slide này xoay quanh nó: phân phối đồng thời chỉ có đúng hai thừa số, nên "
"chỉ có đúng hai chỗ để thay đổi.\n\n"
"Trôi ảo (virtual drift): p(x) đổi nhưng biên quyết định đứng yên — mô hình vẫn đúng, "
"chỉ là dữ liệu đến từ vùng khác. Trôi khái niệm thật: p(y|x) đổi, biên quyết định "
"dịch chuyển, độ chính xác nhất thiết giảm.\n\n"
"Điểm gây ngạc nhiên nên nhấn: phần lớn công trình dự báo chuỗi thời gian 2022–2024 "
"(RevIN, Dish-TS, SAN) xử lý thừa số THỨ NHẤT. Chúng chuẩn hóa phân phối biên rồi "
"khôi phục lại, hoàn toàn không đụng tới p(y|x).\n\n"
"Hệ quả thực tiễn: một bộ phát hiện không dùng nhãn chỉ quan sát được p(x), nên về "
"nguyên tắc không thể phân biệt hai trường hợp này. Đây là lý do vấn đề nhãn muộn ở "
"slide 10 nghiêm trọng đến vậy.",
# 7 --------------------------------------------------------------------------
"BA NGHĨA CỦA 'CONTEXT DRIFT' (~2 phút). Slide này để gỡ rối thuật ngữ trước khi đọc "
"tài liệu, vì ba nghĩa bị dùng lẫn lộn.\n\n"
"Nghĩa 1 là trôi khái niệm đúng nghĩa. Nghĩa 2 (CDS) nói rằng p(y|x) chỉ CÓ VẺ thay "
"đổi, thực ra p(y|x, c) vẫn cố định — chỉ là biến ngữ cảnh c không được đưa vào mô "
"hình. Nghĩa 3 thuộc về mô hình nền tảng, sẽ nói ở slide 23.\n\n"
"Đây là điểm quan trọng nhất: nghĩa 1 và 2 cho CÙNG một triệu chứng — sai số tăng "
"theo thời gian — nhưng đòi hỏi xử lý NGƯỢC nhau. Nếu c là chu kỳ quan sát được "
"(ví dụ giờ trong ngày), thì thích nghi là lãng phí: chu kỳ sau sẽ đảo ngược mọi "
"điều chỉnh vừa làm. Cách đúng là điều kiện hóa theo c, không phải bám theo.\n\n"
"SOLID (KDD'24) đo trực tiếp bằng thông tin tương hỗ giữa phần dư dự báo và ngữ cảnh "
"ứng viên. Công thức này sẽ quay lại ở thí nghiệm B, slide 26.",
# 8 --------------------------------------------------------------------------
"CHUYỂN MỤC. 'Đã có bài toán, giờ xem cộng đồng xử lý thế nào — gồm hai câu hỏi tách "
"biệt: làm sao biết trôi đã xảy ra, và làm gì sau khi biết.'",
# 9 --------------------------------------------------------------------------
"PHÁT HIỆN TRÔI (~2 phút). Nhấn ngay: các bộ phát hiện KHÔNG quan sát dữ liệu mà "
"quan sát chuỗi sai số của mô hình.\n\n"
"DDM và EDDM dùng ngưỡng mang tính kinh nghiệm. ADWIN là lựa chọn mặc định trên thực "
"tế vì có bảo đảm lý thuyết: giữ một cửa sổ W, xét mọi cách cắt W thành W0·W1, và cắt "
"khi hai nửa khác nhau quá ngưỡng; xác suất báo động giả bị chặn bởi δ.\n\n"
"Chi tiết đáng nói nếu có thời gian: ADWIN lưu cửa sổ dưới dạng exponential histogram "
"nên bộ nhớ chỉ O(log W) thay vì O(W); và độ dài cửa sổ còn lại chính là ước lượng "
"'khái niệm hiện tại kéo dài bao xa về quá khứ'.\n\n"
"Câu chốt của slide, cũng là cầu nối sang phần 3: một bộ phát hiện đang hỏi 'chuỗi "
"E_t này có thay đổi không' — tức bản thân nó đã là một phương pháp chuỗi thời gian, "
"chỉ là không tự nhận.",
# 10 -------------------------------------------------------------------------
"HẠN CHẾ ĐÁNH GIÁ (~2 phút). Ba hạn chế, nói theo thứ tự tăng dần mức nghiêm trọng.\n\n"
"(1) Dữ liệu tổng hợp chiếm đa số: các luồng chuyển giữa những khái niệm định sẵn tại "
"những thời điểm cố định, phân phối đơn giản, động lực trôi không thực tế. Chưa có "
"bằng chứng kết quả chuyển được sang dữ liệu thật.\n\n"
"(2) Đánh giá gián tiếp: lấy 'huấn luyện lại có cải thiện không' làm thước đo sẽ trộn "
"lẫn chất lượng bộ phát hiện với khả năng thích nghi của mô hình, và không cho biết "
"độ chính xác lẫn độ trễ phát hiện.\n\n"
"(3) Nghiêm trọng nhất — độ trễ nhãn. DDM, EDDM, ADWIN đều giả định nhãn có ngay. "
"Trong phát hiện gian lận, nhãn thật đến sau 30–180 ngày, nên các phương pháp này "
"không dùng được ở dạng gốc.\n\n"
"Ý cần chốt, và nên nói rõ vì nó cắt cả hai phía: nếu tín hiệu sai số không quan sát "
"được trong nhiều tháng thì KHÔNG chỉ bộ phát hiện gặp khó — mọi phương pháp dựa vào "
"sai số, kể cả phương pháp bám theo ở phần 3, đều gặp khó như nhau.",
# 11 -------------------------------------------------------------------------
"BA CƠ CHẾ THÍCH NGHI (~3 phút). Đây là slide quan trọng nhất của phần khảo sát; nên "
"dành thời gian.\n\n"
"Luận điểm: cơ chế thích nghi nào KHẢ DỤNG là do mô hình được cấu tạo từ cái gì, chứ "
"không phải do người thiết kế chọn.\n\n"
"kNN: mô hình CHÍNH LÀ dữ liệu lưu trữ, nên 'thích nghi' nghĩa là thay dữ liệu — một "
"thao tác thay thế, không có mức độ. Cây Hoeffding: tham số là một cấu trúc rời rạc "
"(nút và ngưỡng), nên không tồn tại phép dịch chuyển nhỏ; chỉ có thể mọc thêm hoặc "
"phá đi rồi dựng lại. SGD: tham số là một vector trong không gian liên tục, nên cộng "
"thêm một lượng nhỏ là thao tác hợp lệ.\n\n"
"Nếu được hỏi 'đây là lập luận hay kết quả', trả lời: là tính chất cấu trúc, không "
"cần thực nghiệm. Trong phần cài đặt của mình, điều này hiện ra thành kiểu trả về: "
"hàm theta_hat() trả về vector cho SGD và PBF-SGD, trả về None cho kNN, SAMkNN, HT và "
"RF-HT. Đó không phải hàm chưa cài đặt — mà là không tồn tại θ để trả về.",
# 12 -------------------------------------------------------------------------
"CHUYỂN MỤC. 'Phần vừa rồi cho thấy có ba cơ chế. Bài báo sau đây lập luận rằng cộng "
"đồng đã chọn nhầm cơ chế.'",
# 13 -------------------------------------------------------------------------
"MÂU THUẪN VÀ BỔ ĐỀ 1 (~3 phút). Trình bày theo ba bước.\n\n"
"Bước 1 — mâu thuẫn: cộng đồng giả định dữ liệu độc lập cùng phân phối TRONG mỗi khái "
"niệm, rồi coi trôi là một sự kiện cần phát hiện để khởi tạo lại mô hình i.i.d. Nhưng "
"trôi chính là sự thay đổi khái niệm, nên giả định tự mâu thuẫn.\n\n"
"Bước 2 — số liệu: nếu độc lập thì phải có P(C_t) = P(C_t | C_{t−1}). Đếm trực tiếp "
"trên luồng 20 bước với τ = 10 được 0,450 so với 0,000. Giải thích tại sao xác suất "
"thứ hai bằng đúng 0: trôi đột ngột là không đảo ngược, một khi C đã lật thì không "
"quay lại.\n\n"
"Bước 3 — phản biện và trả lời: có người sẽ nói khi t đủ lớn thì chỉ số khái niệm trở "
"thành hằng, nên độc lập được khôi phục trong từng khái niệm. Trả lời: ta KHÔNG quan "
"sát được τ. Nếu biết τ thì cắt luồng tại đó và mỗi nửa là i.i.d., toàn bộ bài báo sụp "
"đổ. Vì không biết, một bước nhảy tức thời biểu hiện thành phụ thuộc thời gian kéo dài "
"trong tín hiệu sai số. Chính sự KHÔNG QUAN SÁT ĐƯỢC của τ mới biến một bước nhảy "
"thành một chuỗi thời gian.",
# 14 -------------------------------------------------------------------------
"QUỸ ĐẠO (~3 phút). Đây là đóng góp chính của bài báo: diễn đạt lại bài toán chứ "
"không đề xuất thuật toán mới.\n\n"
"Mỗi khái niệm là một điểm θ trong không gian tham số Θ; trôi trở thành một quỹ đạo. "
"Đọc bảng theo cột cuối: chỉ trôi tăng dần và trôi lặp lại mới có quỹ đạo để bám. "
"Nhắc lại ý từ slide 5 — với trôi dần dần thì α_t mới là chuỗi thời gian, còn θ chỉ "
"nhảy qua lại giữa hai điểm; bài báo thừa nhận điều này và để lại cho nghiên cứu sau.\n\n"
"Bước suy luận then chốt: nếu là quỹ đạo thì về nguyên tắc DỰ BÁO ĐƯỢC. Khi đó bài "
"toán trôi khái niệm trở thành bài toán dự báo θ_t — nguyên văn: 'giải bài toán trôi "
"khái niệm đồng nhất với giải bài toán dự báo θ_t'.\n\n"
"Công thức cuối là toàn bộ đơn thuốc: cập nhật theo gradient, không bộ phát hiện, "
"không khởi tạo lại. Kèm đúng một điều kiện — λ không được giảm về 0 — sẽ kiểm chứng "
"ở slide 18.\n\n"
"Lưu ý khi bị hỏi: đây vẫn là bám theo có tính phản ứng (reactive), chưa phải dự báo "
"thật sự. Bài báo lập luận cho dự báo nhưng không xây dựng nó; phần 5 sẽ cho thấy ai "
"đã xây dựng.",
# 15 -------------------------------------------------------------------------
"CHUYỂN MỤC. 'Lập luận đã rõ. Phần này kiểm chứng nó bằng cách cài đặt lại toàn bộ "
"phương pháp của bài báo và chạy trên chính dữ liệu của bài báo.'",
# 16 -------------------------------------------------------------------------
"THIẾT LẬP THỰC NGHIỆM (~2 phút). Ba điểm cần nhấn.\n\n"
"(1) Dữ liệu lấy từ đúng nguồn bài báo trích dẫn (kho MOA). Số mẫu khớp CHÍNH XÁC: "
"Electricity 45.312 và CoverType 581.012. Đây là kiểm tra đầu tiên cho thấy đang dùng "
"đúng tập dữ liệu.\n\n"
"(2) Cài đặt lại chứ không thay thế: cây Hoeffding thật (tách theo cận Hoeffding, bộ "
"ước lượng Gauss cho thuộc tính số, naive Bayes ở lá), ADWIN2 thật với exponential "
"histogram, RF-HT với 100 cây, không gian con ngẫu nhiên và lấy mẫu Poisson(6). Toàn "
"bộ bằng thư viện chuẩn Python, không scikit-multiflow, không numpy — nên mọi con số "
"đều truy được về một dòng mã đọc được.\n\n"
"(3) ADWIN2 được kiểm chứng ĐỘC LẬP trước khi dùng: trên luồng nhảy từ 0,2 lên 0,8 "
"tại bước 1.000, nó phát hiện sau 55 mẫu; trên 4.000 mẫu dừng, không có báo động giả "
"nào. Nếu bị hỏi 'làm sao tin bản cài đặt', đây là câu trả lời.\n\n"
"Cũng nên nói: độ chính xác chỉ tính từ τ_0 = T/10 trở đi, đúng như Bảng 1 quy định "
"và Bảng 5 xác nhận — nếu tính cả giai đoạn khởi động thì mọi phương pháp đều bị trừ "
"điểm oan.",
# 17 -------------------------------------------------------------------------
"KẾT QUẢ (~3 phút). Đọc bảng theo hàng, không đọc hết mọi số.\n\n"
"Electricity là hàng sạch nhất: SAMkNN 78,0 so với 79,8 (lệch 1,8) và RF-HT 84,5 so "
"với 86,2 (lệch 1,7) với đủ 100 cây. Hai trên ba phương pháp nâng cao tái lập trong "
"vòng 2 điểm — đủ để nói bản cài đặt là đúng.\n\n"
"RTG: PBF-SGD đạt 82,8 so với 81,8 của bài báo, tức VƯỢT; và thứ hạng bài báo công bố "
"ở hàng này (PBF-SGD dẫn đầu) cũng được giữ nguyên.\n\n"
"Hai sai lệch có hệ thống, cả hai đều truy được nguyên nhân. Thứ nhất, PBF-SGD trên "
"Electricity lệch 5,2 điểm — nguyên nhân là bậc đa thức chứ không phải λ, chứng minh "
"ở slide 20. Thứ hai, SAMkNN lệch theo thứ tự tăng dần: 1,8 rồi 7,7 rồi 14,9. Chính "
"THỨ TỰ này là bằng chứng: bản cài đặt của mình nén bộ nhớ dài hạn bằng FIFO thay vì "
"kMeans++ như Losing et al., nên sai lệch phải lớn dần ở những luồng mà bộ nhớ dài hạn "
"gánh nhiều việc hơn — và đúng như vậy. Nói rõ: không nên trích dẫn con số SAMkNN này "
"như con số của SAMkNN gốc.\n\n"
"CoverType không so sánh được: bài báo phân loại đủ 7 lớp, ở đây rút về nhị phân "
"một-chống-tất-cả trên một tập con. Chỉ để xếp hạng tương đối giữa các phương pháp.",
# 18 -------------------------------------------------------------------------
"ĐIỀU KIỆN VỀ λ (~3 phút). Đây là kết quả đáng nói nhất của phần thực nghiệm, vì nó "
"SỬA trực giác.\n\n"
"Bài báo chỉ nêu điều kiện 'không để λ giảm về 0' với lý do mô hình sẽ phản ứng ngày "
"càng chậm với trôi, và không có thực nghiệm nào tách riêng điều kiện này.\n\n"
"Kết quả đo được: hình phạt lớn nhất là sau trôi ĐỘT NGỘT (18,6 điểm) và gần như bằng "
"không dưới trôi KÉO DÀI (0,8 điểm). Ngược hẳn với cách diễn đạt của bài báo, vốn gợi "
"ý rằng trôi liên tục mới là nơi mô hình đóng băng chịu thiệt nhất.\n\n"
"Giải thích cơ chế — đây là phần quan trọng: dưới trôi kéo dài (xoay 0,01 rad mỗi "
"bước), λ hằng số cũng chỉ đạt 88,1 vì khái niệm di chuyển nhanh hơn mọi bước cố định; "
"đã không bám được thì giảm λ cũng chẳng mất thêm gì. Ngược lại, sau khi khái niệm bị "
"lấy mẫu lại, λ còn sống thì học lại được khái niệm mới, λ đóng băng thì không — nên "
"mất trọn 18,6 điểm.\n\n"
"Phòng câu hỏi 'có phải do λ_0 = 0,01 quá nhỏ không': đã kiểm tra trên dải 50 lần, "
"λ_0 ∈ {0,01; 0,1; 0,5}. Hình phạt ở trôi kéo dài giữ nguyên mức nhỏ (1,0 / 1,2 / 1,4) "
"ở mọi λ_0, nên không phải hiện tượng giả do tham số.\n\n"
"Kết luận cần chốt: điều kiện này thực chất nói về khả năng PHỤC HỒI sau gián đoạn, "
"chứ không phải về việc bám theo trôi liên tục.",
# 19 -------------------------------------------------------------------------
"PHƯƠNG PHÁP BỘ ĐỆM (~2 phút). Chỉ vào hình trước khi nói: đường kNN gần như nằm "
"ngang.\n\n"
"Số liệu: kNN dao động 0,6 điểm qua cả năm kịch bản (72,7 đến 73,3), trong khi SGD "
"dao động 9,2 điểm (88,1 đến 97,3).\n\n"
"Giải thích: trôi hầu như không làm kNN tệ đi, vì kNN chưa bao giờ tích lũy được gì "
"để trôi làm hỏng. Mô hình chính là 100 mẫu gần nhất, và 100 mẫu gần nhất thì luôn "
"thuộc khái niệm hiện tại dù có trôi hay không.\n\n"
"Điểm đóng góp của slide: bài báo nêu HAI nhận xét riêng biệt — mục 7 nói năng lực bị "
"chặn bởi kích thước bộ đệm, và Hình 5a nhận xét kNN không có xu hướng tăng ngay cả "
"khi khái niệm đứng yên. Thực ra đó là CÙNG một tính chất: không tích lũy được thì "
"vừa bị chặn trên, vừa không bị trôi làm hại. Trần năng lực và tính trơ là một.\n\n"
"Nếu bị hỏi về SAMkNN: SAMkNN khắc phục đúng điểm này bằng bộ nhớ dài hạn, và đó là "
"lý do nó tốt hơn kNN thuần trong Bảng 3.",
# 20 -------------------------------------------------------------------------
"THAM SỐ KHÔNG ĐƯỢC NÊU (~2 phút). Ba tham số bài báo không ghi, xếp theo mức ảnh "
"hưởng.\n\n"
"Quan trọng nhất là số chiều dữ liệu tổng hợp: SGD đạt 57,7 / 74,5 / 83,1 / 92,2 ứng "
"với d = 2 / 5 / 10 / 20. Biên độ này lớn hơn chênh lệch giữa bất kỳ hai phương pháp "
"nào trong Bảng 3.\n\n"
"Hệ quả: hàng Synthetic của bài báo (93,6–96,0) chỉ đạt được ở d lớn, KHÔNG đạt được "
"ở d = 2 như chính Hình 4 của bài báo vẽ. Ai trích dẫn cột đó nên biết nó phụ thuộc "
"vào một tham số tự do không được công bố.\n\n"
"Giải thích nguyên nhân nếu có thời gian: phép quay ở đây là quay Givens trong một "
"mặt phẳng tọa độ, nên chỉ làm nhiễu 2 trong d thành phần — d càng lớn thì càng nhiều "
"phần của θ sống sót sau mỗi bước. Cũng có thể bài báo hiểu 'ma trận quay góc 0,01' "
"theo nghĩa khác (quay ngẫu nhiên toàn phần), khi đó phụ thuộc vào d sẽ biến mất. "
"Văn bản không cho phép kết luận, nên nêu là điểm chưa giải quyết chứ đừng khẳng định.\n\n"
"Quan sát kèm theo, khá bất ngờ: trên luồng Synthetic, SGD thuần đạt 92,2 còn PBF-SGD "
"chỉ 88,5 — khai triển cơ sở làm TỆ ĐI. Lý do: khái niệm ở đó là siêu phẳng θᵀx = 0, "
"tuyến tính theo định nghĩa, nên cơ sở đa thức bậc 3 thêm 1.770 tham số chỉ đóng góp "
"phương sai mà không thêm năng lực biểu diễn. Khai triển cơ sở là một canh bạc đặt vào "
"tính phi tuyến, và đây đúng là ô mà canh bạc đó chắc chắn thua.",
# 21 -------------------------------------------------------------------------
"CHUYỂN MỤC. 'Bài báo 2018 đề xuất dự báo θ nhưng không xây dựng. Phần này xem điều "
"gì đã xảy ra sau đó.'",
# 22 -------------------------------------------------------------------------
"BỐN HƯỚNG TIẾP CẬN (~2 phút). Đọc bảng nhanh, dừng lại ở hàng cuối.\n\n"
"Ba hướng đầu đều mang tính phản ứng: chuẩn hóa xử lý phân phối biên; fast/slow cân "
"bằng giữa thích nghi nhanh và nhớ lại mẫu cũ; bể khái niệm giả định khái niệm sẽ "
"quay lại nên lưu sẵn mô hình cho từng khái niệm.\n\n"
"Chỉ Proceed (KDD'25) làm đúng điều Read lập luận. Cơ chế: ước lượng độ trôi giữa dữ "
"liệu huấn luyện gần nhất và mẫu kiểm tra hiện tại, rồi dùng một bộ sinh ĐƯỢC HỌC để "
"chuyển ước lượng đó thành điều chỉnh tham số — tức là một ánh xạ từ dịch chuyển trong "
"không gian khái niệm sang dịch chuyển trong không gian tham số. Bộ sinh được huấn "
"luyện trước trên các kiểu trôi tổng hợp đa dạng.\n\n"
"Câu chốt nên nói rõ ràng: Read lập luận rằng giải bài toán trôi đồng nghĩa với dự báo "
"θ, nhưng không xây dựng. Bảy năm sau Proceed xây dựng đúng ánh xạ đó, theo đúng hướng "
"ông đề xuất. Đây là lý do bài báo 2018 vẫn đáng đọc.\n\n"
"Phân biệt với động lượng (momentum): động lượng ngoại suy tuyến tính trên gradient; "
"Proceed học hẳn một ánh xạ. Đây cũng là nền cho thí nghiệm A ở slide 26.",
# 23 -------------------------------------------------------------------------
"MÔ HÌNH NỀN TẢNG (~2 phút). Ý chính: trôi khái niệm không biến mất, chỉ đổi vị trí.\n\n"
"Các mô hình nền tảng cho chuỗi thời gian (Chronos, Moirai và các mô hình kế tiếp) "
"được huấn luyện trước trên kho dữ liệu lớn và dùng ở chế độ zero-shot. Dữ liệu luồng "
"vẫn trôi như thường.\n\n"
"Hướng 1 — thích nghi hộp đen: nếu mô hình được phục vụ qua API thương mại thì không "
"thể sửa trọng số. Công trình gần đây thích nghi bằng cách học CẤU TRÚC SAI SỐ của mô "
"hình theo ngữ cảnh, rồi hiệu chỉnh đầu ra.\n\n"
"Hướng 2 — tiên nghiệm kháng trôi: đưa giả định 'mô hình thay đổi theo thời gian' vào "
"ngay trong tiên nghiệm học trong ngữ cảnh, để mô hình học cách ước lượng, thích nghi "
"và ngoại suy sự thay đổi (Drift-Resilient TabPFN, NeurIPS'24).\n\n"
"Liên hệ ngược về phần 2: cả hai vẫn là thích nghi liên tục theo đúng nghĩa đã định "
"nghĩa — tham số chỉ nằm ở chỗ khác, trong ngữ cảnh hoặc trong bộ hiệu chỉnh phần dư, "
"chứ không nằm trong trọng số.",
# 24 -------------------------------------------------------------------------
"CHUYỂN MỤC. 'Phần cuối: những gì chưa ai giải quyết, và những thí nghiệm có thể làm "
"ngay trên bộ công cụ hiện có.'",
# 25 -------------------------------------------------------------------------
"VẤN ĐỀ MỞ (~2 phút). Ba vấn đề, vấn đề đầu là quan trọng nhất.\n\n"
"(1) Chưa có tiêu chí phân biệt trôi thật với ngữ cảnh bị bỏ sót. CDS cho rằng p(y|x) "
"chỉ CÓ VẺ thay đổi vì thiếu biến c; Read cho rằng θ thật sự di chuyển trong Θ. Nếu c "
"quan sát được và có chu kỳ thì bám theo là lãng phí; nếu c tiềm ẩn và không lặp thì "
"điều kiện hóa là bất khả. Không công trình nào chỉ ra đang ở trường hợp nào — mà đây "
"lại là câu hỏi phải trả lời TRƯỚC khi chọn phương pháp.\n\n"
"(2) Trôi lặp lại và trôi kéo dài chia đôi không gian phương pháp: bể khái niệm giả "
"định khái niệm quay lại, bộ bám theo giả định dịch chuyển trơn. Ranh giới giữa hai "
"giả định này chưa được đặc tả.\n\n"
"(3) Đánh giá vẫn tổng hợp và giả định nhãn tức thì, trong khi các ứng dụng làm nên "
"động lực của lĩnh vực đều không như vậy. Nhắc lại slide 10 nếu cần.",
# 26 -------------------------------------------------------------------------
"THÍ NGHIỆM ĐỀ XUẤT (~3 phút). Mỗi thí nghiệm kèm một dự đoán CÓ THỂ SAI — đó là điều "
"phân biệt đề xuất nghiên cứu với mong muốn.\n\n"
"Thứ tự trình bày nên là D → A → C → B: rẻ nhất và chắc chắn nhất trước, tham vọng "
"nhất sau cùng, vì người nghe thường đánh giá thấp một danh sách mở đầu bằng thí "
"nghiệm khó nhất.\n\n"
"D (rẻ nhất): quét lưới tốc độ trôi × λ, tìm λ tối ưu cho mỗi tốc độ, khớp số mũ trên "
"đồ thị log-log. Nếu ra gần 0,5 thì biến cảnh báo ở mục 5 thành quy tắc chỉnh tham số.\n\n"
"A: giải thích vì sao động lượng không giúp gì. Quỹ đạo thật là phép QUAY, tức đường "
"cong, còn động lượng ngoại suy TUYẾN TÍNH — nên về dài hạn triệt tiêu. Thay bằng bộ "
"ngoại suy khớp đúng dạng hàm (ước lượng ma trận quay từ lịch sử θ̂). Dự đoán có thể "
"sai: nó phải thu hẹp khoảng cách bám ở trôi tăng dần VÀ không có tác dụng ở trôi đột "
"ngột — nếu giúp ở mọi nơi thì chỉ là tăng hệ số khuếch đại, tức không chứng minh được gì.\n\n"
"C: quét chu kỳ lặp, so bộ bám theo với bể khái niệm, tìm điểm giao p*. Đây là ranh "
"giới trung thực cho chính luận điểm của mình, nên trình bày nó làm tăng độ tin cậy.\n\n"
"B (để cuối, là thí nghiệm muốn người nghe nhớ): trả lời trực tiếp vấn đề mở thứ nhất. "
"Thêm một kiểu trôi mới trong đó θ phụ thuộc một ngữ cảnh có chu kỳ QUAN SÁT ĐƯỢC, rồi "
"so hai chẩn đoán: tự tương quan của phần dư (chẩn đoán kiểu Read) và thông tin tương "
"hỗ giữa phần dư với ngữ cảnh (chẩn đoán kiểu CDS). Dự đoán: tự tương quan phát hiện "
"CẢ HAI nên không phân biệt được, còn thông tin tương hỗ chỉ phát hiện trường hợp thứ "
"hai. Nếu đúng, ta có một quy tắc quyết định chưa ai công bố.\n\n"
"Lý do B khả thi ngay: Electricity đã có sẵn ngữ cảnh chu kỳ quan sát được (48 khung "
"nửa giờ trong ngày, và thứ trong tuần), còn luồng tổng hợp thì cho biết θ thật — nên "
"dựng và tách được cả hai trường hợp trên cùng một bộ công cụ.",
# 27 -------------------------------------------------------------------------
"TÓM TẮT (~1 phút). Sáu ý, đọc nhanh, không giải thích lại.\n\n"
"Nếu còn thời gian, nên kết thúc bằng câu hỏi mở ở slide 26 thay vì bằng slide tóm "
"tắt: kết ở một câu hỏi mà mình có điều kiện trả lời sẽ mở ra trao đổi, và đó cũng là "
"cách xin được buổi làm việc tiếp theo.\n\n"
"Câu hỏi có thể gặp và hướng trả lời:\n"
"• 'Sao không dùng scikit-multiflow cho nhanh?' — vì mục tiêu là truy được mọi con số "
"về mã nguồn đọc được, và vì bản cài đặt lại đã phát hiện ra chính những chỗ bài báo "
"không ghi rõ.\n"
"• 'Kết quả không khớp thì có phải bản cài đặt sai?' — hai trong ba phương pháp khớp "
"trong 2 điểm, ADWIN được kiểm chứng độc lập, và các sai lệch đều truy được nguyên "
"nhân cụ thể (bậc đa thức, cách nén bộ nhớ dài hạn).\n"
"• 'Bài báo 2018 còn giá trị không?' — luận điểm cấu trúc (cây không có Δθ) vẫn đúng "
"và không cần thực nghiệm; còn đề xuất dự báo θ thì đã được Proceed hiện thực hóa năm "
"2025.",
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
