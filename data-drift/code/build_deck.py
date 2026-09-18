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


# Lời nói cho từng slide (tiếng Việt) — đọc thẳng, không phải chỉ dẫn trình bày.
NOTES = [
# 1 --------------------------------------------------------------------------
"Xin chào mọi người. Hôm nay tôi trình bày về trôi khái niệm trong luồng dữ liệu.\n\n"
"Bài gồm ba khối. Khối thứ nhất là bài toán: trôi khái niệm là gì, và cộng đồng "
"nghiên cứu đã xử lý nó bằng những cách nào. Khối thứ hai là một lập luận cụ thể của "
"Jesse Read năm 2018, cho rằng cách xử lý phổ biến hiện nay là sai hướng, cùng với "
"kết quả tôi tái lập lại bài báo đó. Khối thứ ba là những gì đã xảy ra sau năm 2018 "
"và những câu hỏi còn bỏ ngỏ.\n\n"
"Phần tái lập chỉ là một trong sáu mục, nên đây không phải một báo cáo thực nghiệm "
"thuần túy mà là một bài khảo sát có kèm phần kiểm chứng.",
# 2 --------------------------------------------------------------------------
"Mạch của bài đi như sau. Trước hết là định nghĩa bài toán cho chính xác. Sau đó là "
"các phương pháp hiện có, chia thành hai nhóm: phát hiện trôi, và thích nghi sau khi "
"trôi. Phần ba là bài báo của Read, lập luận rằng một luồng dữ liệu có trôi thực chất "
"là một chuỗi thời gian. Phần bốn là kết quả tôi tái lập lại bài báo đó. Phần năm là "
"những công trình ra đời sau, trong đó có một công trình năm 2025 đã hiện thực hóa "
"đúng điều Read đề xuất. Và phần sáu là các vấn đề còn mở.",
# 3 --------------------------------------------------------------------------
"Trước hết ta cần định nghĩa bài toán cho chính xác, bởi vì thuật ngữ trong lĩnh vực "
"này được dùng khá lỏng lẻo và nhiều khi cùng một từ chỉ những hiện tượng khác nhau.",
# 4 --------------------------------------------------------------------------
"Học máy truyền thống giả định rằng có một phân phối đồng thời p của x và y cố định. "
"Ta lấy một mẫu huấn luyện, khớp mô hình vào đó, rồi triển khai; mô hình tổng quát "
"hóa được là vì mẫu huấn luyện và dữ liệu triển khai cùng tuân theo một quy luật.\n\n"
"Luồng dữ liệu phá vỡ đúng giả định đó. Quy luật sinh dữ liệu tự nó thay đổi theo thời "
"gian: phân phối có điều kiện của y theo x tại thời điểm t không còn bằng phân phối "
"đó tại thời điểm t cộng k.\n\n"
"Điều này có nghĩa là mô hình đang triển khai không phải là mô hình cũ, mà là mô hình "
"sai đặc tả. Nó ước lượng một mục tiêu không còn tồn tại nữa. Đây không phải vấn đề "
"thiếu dữ liệu, và thêm dữ liệu cũng không giải quyết được.\n\n"
"Ta gặp hiện tượng này ở nhu cầu điện, khi thói quen tiêu dùng và thời tiết thay đổi; "
"ở phát hiện gian lận, khi đối thủ đổi chiến thuật; ở phát hiện xâm nhập mạng.\n\n"
"Có hai hệ quả ràng buộc mọi phương pháp về sau. Thứ nhất, sự suy giảm diễn ra âm "
"thầm: không có lỗi nào được báo, hệ thống vẫn chạy bình thường, chỉ có độ chính xác "
"tụt dần. Nếu không đo thì không biết. Thứ hai, ta không thể huấn luyện lại từ đầu, "
"vì luồng là vô hạn và nhãn thường đến rất muộn.",
# 5 --------------------------------------------------------------------------
"Trôi khái niệm được phân thành bốn dạng. Trôi đột ngột là khi một khái niệm thay thế "
"khái niệm khác tại một thời điểm, ví dụ một cảm biến được hiệu chuẩn lại. Trôi tăng "
"dần là khi khái niệm dịch chuyển qua từng bước nhỏ, ví dụ máy móc mòn đi theo thời "
"gian. Trôi dần dần là khi hai khái niệm luân phiên nhau, khái niệm mới dần thắng thế, "
"ví dụ thói quen người dùng chuyển từ A sang B. Trôi lặp lại là khi các khái niệm quay "
"trở lại theo chu kỳ, ví dụ nhu cầu điện ngày thường so với cuối tuần.\n\n"
"Cột đáng chú ý là cột cuối. Với trôi tăng dần, các trạng thái trung gian là những "
"khái niệm thật, nghĩa là tồn tại một quỹ đạo liên tục để bám theo. Với trôi dần dần "
"thì không: chỉ có hai khái niệm cố định và một trọng số pha trộn thay đổi. Cái biến "
"thiên trơn ở đây là trọng số pha trộn, chứ không phải bản thân khái niệm. Điểm khác "
"biệt này sẽ quyết định phương pháp nào dùng được, và ta sẽ quay lại nó ở phần ba.\n\n"
"Trôi lặp lại là một trục riêng, không loại trừ ba dạng kia; bất kỳ dạng nào cũng có "
"thể lặp.",
# 6 --------------------------------------------------------------------------
"Phân phối đồng thời của x và y phân tích được thành tích của phân phối biên p của x "
"với phân phối có điều kiện p của y theo x. Nó chỉ có hai thừa số, nên chỉ có đúng hai "
"chỗ mà sự thay đổi có thể xảy ra.\n\n"
"Trường hợp thứ nhất gọi là trôi ảo: phân phối biên thay đổi nhưng biên quyết định "
"đứng yên. Mô hình vẫn đúng, chỉ là dữ liệu đến từ một vùng khác của không gian đầu "
"vào. Trường hợp thứ hai là trôi khái niệm thật: phân phối có điều kiện thay đổi, biên "
"quyết định dịch chuyển, và độ chính xác nhất thiết giảm.\n\n"
"Chỉ trường hợp thứ hai mới nhất thiết gây thiệt hại. Nhưng phần lớn công trình về dự "
"báo chuỗi thời gian trong giai đoạn 2022 đến 2024 — RevIN, Dish-TS, SAN — lại xử lý "
"trường hợp thứ nhất. Chúng chuẩn hóa phân phối biên ở đầu vào rồi khôi phục lại ở đầu "
"ra, và hoàn toàn không đụng tới phân phối có điều kiện.\n\n"
"Hệ quả thực tiễn là: một bộ phát hiện không dùng nhãn thì chỉ quan sát được phân phối "
"biên, nên về nguyên tắc nó không thể phân biệt hai trường hợp này với nhau.",
# 7 --------------------------------------------------------------------------
"Cụm từ context drift được dùng cho ba hiện tượng khác nhau, nên tôi muốn tách bạch "
"trước khi đi tiếp.\n\n"
"Nghĩa thứ nhất là trôi khái niệm đúng nghĩa: phân phối có điều kiện thật sự thay đổi "
"theo thời gian. Nghĩa thứ hai gọi là context-driven shift: phân phối có điều kiện của "
"y theo x và theo biến ngữ cảnh c vẫn cố định, chỉ là biến c không được đưa vào mô "
"hình. Nghĩa thứ ba thuộc về mô hình nền tảng, khi cửa sổ suy luận đi ra khỏi phân phối "
"lúc huấn luyện trước; tôi sẽ nói ở phần năm.\n\n"
"Điều quan trọng là hai nghĩa đầu cho cùng một triệu chứng — sai số tăng dần theo thời "
"gian — nhưng đòi hỏi hai cách xử lý ngược nhau. Nếu c là một ngữ cảnh có chu kỳ mà ta "
"quan sát được, chẳng hạn giờ trong ngày, thì việc cho mô hình thích nghi là lãng phí: "
"chu kỳ sau sẽ đảo ngược mọi điều chỉnh vừa làm. Cách đúng là điều kiện hóa theo c, "
"chứ không phải bám theo sự thay đổi.\n\n"
"Công trình SOLID tại KDD 2024 đo trực tiếp bằng thông tin tương hỗ giữa phần dư dự "
"báo của mô hình và biến ngữ cảnh ứng viên. Nếu thông tin tương hỗ này cao, nghĩa là "
"mô hình đang thiếu một biến, chứ không phải khái niệm đang trôi.",
# 8 --------------------------------------------------------------------------
"Đã có bài toán, giờ ta xem cộng đồng xử lý nó thế nào. Có hai câu hỏi tách biệt: làm "
"sao biết trôi đã xảy ra, và làm gì sau khi đã biết.",
# 9 --------------------------------------------------------------------------
"Điểm đầu tiên cần lưu ý là các bộ phát hiện trôi không quan sát dữ liệu, mà quan sát "
"chuỗi sai số của mô hình.\n\n"
"DDM năm 2004 báo động khi tỷ lệ lỗi vượt quá mức thấp nhất từng ghi nhận một khoảng "
"k lần độ lệch chuẩn. EDDM năm 2006 theo dõi khoảng cách giữa hai lỗi liên tiếp, và "
"làm tốt hơn với trôi dần dần. Cả hai đều dùng ngưỡng mang tính kinh nghiệm.\n\n"
"ADWIN năm 2007 là lựa chọn mặc định trên thực tế, vì nó có bảo đảm lý thuyết. Nó giữ "
"một cửa sổ các quan sát gần nhất, xét mọi cách cắt cửa sổ đó thành hai nửa, và cắt bỏ "
"nửa cũ khi trung bình hai nửa khác nhau quá một ngưỡng. Xác suất báo động giả bị chặn "
"bởi tham số delta. Cửa sổ được lưu dưới dạng exponential histogram nên bộ nhớ chỉ là "
"log của độ dài cửa sổ; và độ dài cửa sổ còn lại sau khi cắt chính là ước lượng cho "
"câu hỏi khái niệm hiện tại kéo dài bao xa về quá khứ.\n\n"
"Có một điều đáng suy nghĩ ở đây. Một bộ phát hiện trôi đang hỏi rằng chuỗi sai số "
"theo thời gian này có thay đổi hay không. Tức là bản thân nó đã là một phương pháp "
"chuỗi thời gian rồi, chỉ là không tự nhận như vậy. Đây chính là điểm bài báo ở phần "
"ba khai thác.",
# 9b -------------------------------------------------------------------------
"Tôi nói kỹ hơn một chút về ba phép kiểm định này, vì chúng đại diện cho ba cách nghĩ "
"khác nhau về cùng một tín hiệu.\n\n"
"DDM theo dõi trực tiếp tỷ lệ lỗi. Tại mỗi bước nó có tỷ lệ lỗi p chỉ số i và sai số "
"chuẩn nhị thức s chỉ số i, bằng căn của p nhân một trừ p chia i. Nó ghi nhớ giá trị "
"nhỏ nhất từng đạt được trong suốt luồng, và lấy đó làm mốc tham chiếu, với ý là mô "
"hình khi khớp tốt nhất thì sai bao nhiêu. Khi tổng hiện tại vượt mốc đó ba lần độ "
"lệch chuẩn thì báo trôi; ở mức hai lần thì mới chỉ là cảnh báo, và thường được dùng "
"để bắt đầu gom dữ liệu cho mô hình thay thế. Cách này đơn giản và nhạy với trôi đột "
"ngột, nhưng vì mốc tham chiếu là giá trị nhỏ nhất từng thấy nên nó không tự quên đi "
"quá khứ.\n\n"
"EDDM đổi đại lượng quan sát. Thay vì tỷ lệ lỗi, nó theo dõi khoảng cách giữa hai lỗi "
"liên tiếp. Ý tưởng là khi mô hình đang tốt thì các lỗi thưa ra, khoảng cách giữa "
"chúng lớn dần; còn khi khái niệm trôi thì các lỗi dồn lại gần nhau. Nó so tỷ số giữa "
"giá trị hiện tại và giá trị lớn nhất từng đạt, và báo trôi khi tỷ số này tụt xuống "
"dưới ngưỡng beta. Vì đo khoảng cách chứ không đo tỷ lệ, EDDM nhạy hơn với trôi dần "
"dần, là trường hợp mà tỷ lệ lỗi thay đổi quá chậm để DDM kịp nhận ra.\n\n"
"ADWIN khác hẳn hai cái trên ở chỗ nó không cần chọn trước kích thước cửa sổ. Nó giữ "
"một cửa sổ các quan sát gần nhất, rồi xét mọi cách cắt cửa sổ đó thành hai phần, "
"phần cũ và phần mới. Nếu trung bình của hai phần chênh nhau quá một ngưỡng epsilon "
"thì nó kết luận rằng đã có thay đổi, và cắt bỏ phần cũ đi. Ngưỡng epsilon được tính "
"từ phương sai trong cửa sổ và kích thước của hai phần, sao cho xác suất báo động giả "
"bị chặn bởi delta. Đây là điểm mạnh của nó: có bảo đảm hình thức, và kích thước cửa "
"sổ tự điều chỉnh theo dữ liệu thay vì do ta đặt tay.",
# 10 -------------------------------------------------------------------------
"Quy trình đánh giá hiện nay có ba hạn chế.\n\n"
"Thứ nhất, dữ liệu tổng hợp chiếm đa số. Các luồng chuẩn thường chuyển giữa những khái "
"niệm định sẵn tại những thời điểm cố định, với phân phối đơn giản và động lực trôi "
"không thực tế. Chưa có bằng chứng cho thấy kết luận rút ra từ đó chuyển được sang dữ "
"liệu thật.\n\n"
"Thứ hai, nhiều nghiên cứu đánh giá gián tiếp, tức lấy tiêu chí huấn luyện lại có cải "
"thiện hay không. Cách này trộn lẫn chất lượng của bộ phát hiện với khả năng thích "
"nghi của mô hình, và không cho biết bộ phát hiện chính xác đến đâu hay phát hiện "
"nhanh đến đâu.\n\n"
"Thứ ba, và nghiêm trọng nhất, là độ trễ nhãn. DDM, EDDM và ADWIN đều giả định nhãn có "
"gần như ngay lập tức. Nhưng trong phát hiện gian lận, nhãn thật chỉ đến sau ba mươi "
"đến một trăm tám mươi ngày. Ở dạng gốc, các phương pháp này không dùng được.\n\n"
"Điều này cắt về cả hai phía. Nếu tín hiệu sai số không quan sát được trong nhiều "
"tháng, thì không chỉ bộ phát hiện gặp khó — mọi phương pháp dựa vào sai số, kể cả "
"phương pháp bám theo mà tôi sẽ trình bày ở phần sau, đều gặp khó y như vậy.",
# 11 -------------------------------------------------------------------------
"Sau khi phát hiện được trôi thì làm gì. Có ba cơ chế, và điều đáng nói là cơ chế nào "
"khả dụng không phải do người thiết kế chọn, mà do mô hình được cấu tạo từ cái gì.\n\n"
"Với k láng giềng gần nhất, mô hình chính là dữ liệu được lưu. Thích nghi nghĩa là "
"thay dữ liệu cũ bằng dữ liệu mới. Đó là một thao tác thay thế, không có mức độ: ta "
"không thể thay một chút.\n\n"
"Với cây Hoeffding, tham số là một cấu trúc rời rạc gồm các nút và các ngưỡng. Không "
"tồn tại phép dịch chuyển nhỏ trên một cấu trúc như vậy. Cây chỉ có thể mọc thêm, hoặc "
"bị phá đi rồi dựng lại từ đầu.\n\n"
"Với hạ gradient ngẫu nhiên, tham số là một vector trong không gian liên tục, nên cộng "
"thêm một lượng nhỏ là thao tác hoàn toàn hợp lệ.\n\n"
"Nói cách khác, một cái cây không có đại lượng delta theta. Đây là tính chất cấu trúc, "
"không cần thực nghiệm nào để chứng minh. Trong phần cài đặt của tôi, điều này hiện ra "
"thành kiểu trả về của hàm: hàm theta_hat trả về một vector đối với SGD và PBF-SGD, và "
"trả về None đối với kNN, SAMkNN, cây Hoeffding và rừng ngẫu nhiên. Đó không phải hàm "
"chưa được cài đặt, mà là không tồn tại tham số nào để trả về.",
# 12 -------------------------------------------------------------------------
"Phần vừa rồi cho thấy có ba cơ chế thích nghi. Bài báo sau đây lập luận rằng cộng "
"đồng nghiên cứu đã chọn nhầm cơ chế, và lý do nằm ngay trong giả định nền tảng.",
# 13 -------------------------------------------------------------------------
"Lập luận bắt đầu từ một mâu thuẫn. Tài liệu trong lĩnh vực giả định rằng các mẫu là "
"độc lập cùng phân phối ở trong mỗi khái niệm, rồi coi trôi là một sự kiện cần phát "
"hiện để có thể khởi tạo lại một mô hình độc lập cùng phân phối. Nhưng trôi chính là "
"sự thay đổi của khái niệm, nên giả định này tự mâu thuẫn với chính nó.\n\n"
"Bổ đề 1 phát biểu rằng một luồng có trôi khái niệm thì tất yếu có phụ thuộc thời "
"gian. Nếu thật sự độc lập thì xác suất của chỉ số khái niệm tại thời điểm t phải bằng "
"xác suất đó khi đã biết chỉ số tại thời điểm trước. Đếm trực tiếp trên một luồng hai "
"mươi bước với điểm đổi tại bước thứ mười, ta được 0,450 so với 0,000. Xác suất thứ "
"hai bằng đúng không, bởi vì trôi đột ngột là không đảo ngược: một khi đã chuyển sang "
"khái niệm mới thì không quay lại khái niệm cũ nữa.\n\n"
"Có một phản biện tự nhiên: khi t đủ lớn thì chỉ số khái niệm trở thành hằng số, nên "
"tính độc lập được khôi phục ở trong từng khái niệm. Câu trả lời nằm ở một điểm duy "
"nhất: ta không quan sát được thời điểm đổi tau. Nếu biết tau thì ta cắt luồng tại đó, "
"mỗi nửa là độc lập cùng phân phối, và toàn bộ bài báo sụp đổ. Vì không biết, một bước "
"nhảy tức thời giữa hai thời điểm lại biểu hiện thành phụ thuộc thời gian kéo dài "
"trong tín hiệu sai số. Chính sự không quan sát được của tau mới biến một bước nhảy "
"thành một chuỗi thời gian.",
# 14 -------------------------------------------------------------------------
"Từ đó bài báo diễn đạt lại bài toán. Mỗi khái niệm là một điểm theta trong không gian "
"tham số, và trôi trở thành một quỹ đạo đi qua không gian đó.\n\n"
"Với trôi đột ngột, theta được lấy mẫu lại từ phân phối tiên nghiệm, nên không có quỹ "
"đạo, chỉ có một điểm gián đoạn. Với trôi tăng dần, theta tại thời điểm t bằng ma trận "
"quay nhân với theta tại thời điểm trước, góc quay là 0,01 radian mỗi bước; đây là một "
"quỹ đạo thật sự. Với trôi dần dần, theta chỉ nhảy qua lại giữa hai điểm cố định, cái "
"biến thiên là trọng số pha trộn, nên không có gì để bám theo; bài báo thừa nhận điều "
"này và để lại cho nghiên cứu sau. Với trôi lặp lại, quỹ đạo là một chu trình.\n\n"
"Bước suy luận then chốt là: nếu trôi là một quỹ đạo thì về nguyên tắc nó dự báo được. "
"Khi đó, theo nguyên văn bài báo, giải bài toán trôi khái niệm đồng nhất với giải bài "
"toán dự báo theta tại thời điểm t.\n\n"
"Và đơn thuốc là công thức ở cuối slide: theta mới bằng theta cũ cộng lambda nhân "
"gradient của sai số. Không cần bộ phát hiện, không cần khởi tạo lại mô hình. Chỉ kèm "
"đúng một điều kiện, là lambda không được giảm dần về không — tôi sẽ kiểm chứng điều "
"kiện này bằng thực nghiệm.\n\n"
"Cần nói thêm cho công bằng: đây vẫn là bám theo có tính phản ứng, chưa phải dự báo "
"thật sự. Bài báo lập luận cho việc dự báo nhưng không xây dựng nó. Ai đã xây dựng thì "
"tôi sẽ nói ở phần năm.",
# 15 -------------------------------------------------------------------------
"Lập luận đã rõ. Phần này tôi trình bày thực nghiệm của mình: tôi cài đặt lại sáu "
"phương pháp trong Bảng 2 và chạy chúng trên bốn luồng dữ liệu, để xem chúng thực sự "
"hành xử ra sao dưới các dạng trôi khác nhau.",
# 16 -------------------------------------------------------------------------
"Dữ liệu tôi lấy từ đúng kho mà bài báo trích dẫn, tức kho MOA của Waikato. Số mẫu "
"khớp chính xác: Electricity có 45.312 mẫu và CoverType có 581.012 mẫu, đúng như bài "
"báo ghi. Đây là kiểm tra đầu tiên cho thấy tôi đang dùng đúng tập dữ liệu.\n\n"
"Cả sáu phương pháp trong Bảng 2 đều được cài đặt lại, chứ không thay thế bằng mô hình "
"tương đương. Cụ thể là cây Hoeffding thật, với phép tách theo cận Hoeffding, bộ ước "
"lượng Gauss cho thuộc tính số và naive Bayes ở lá; ADWIN2 thật với exponential "
"histogram; và rừng ngẫu nhiên thích nghi với một trăm cây, không gian con ngẫu nhiên "
"và lấy mẫu Poisson với lambda bằng sáu. Toàn bộ viết bằng thư viện chuẩn của Python, "
"không dùng scikit-multiflow, không dùng numpy. Nhờ vậy mọi con số đều truy ngược được "
"về một dòng mã đọc được.\n\n"
"ADWIN2 được kiểm chứng độc lập trước khi đem dùng. Trên một luồng nhảy từ 0,2 lên 0,8 "
"tại bước một nghìn, nó phát hiện sau 55 mẫu. Trên bốn nghìn mẫu ở trạng thái dừng, "
"nó không đưa ra báo động giả nào.\n\n"
"Độ chính xác chỉ được tính từ mốc tau không, bằng một phần mười độ dài luồng, trở đi "
"— đúng như Bảng 1 quy định và Bảng 5 xác nhận. Nếu tính cả giai đoạn khởi động thì "
"mọi phương pháp đều bị trừ điểm oan vì lúc đó mô hình chưa học được gì.",
# 17 -------------------------------------------------------------------------
"Đây là kết quả của tôi trên bốn luồng, tính bằng độ chính xác prequential theo phần "
"trăm, và chỉ tính từ mốc một phần mười độ dài luồng trở đi.\n\n"
"Điều đáng chú ý nhất là không có phương pháp nào thắng ở mọi luồng, và thứ hạng thay "
"đổi hẳn giữa các luồng.\n\n"
"Trên Electricity, rừng ngẫu nhiên dẫn đầu với 84,5 điểm, theo sau là PBF-SGD 80,7 và "
"SAMkNN 78,0. Đây là luồng thực, nhiều nhiễu, và tổ hợp một trăm cây tỏ ra đáng giá.\n\n"
"Trên RTG thì PBF-SGD dẫn đầu với 82,8 điểm, bỏ xa rừng ngẫu nhiên 72,5. Lý do là RTG "
"được sinh ra từ một cây ngẫu nhiên, nên biên quyết định phi tuyến và rời rạc; khai "
"triển đa thức bậc ba có đất dụng võ ở đây.\n\n"
"Trên luồng tổng hợp, SGD thuần đạt 92,2 và vượt cả PBF-SGD chỉ được 88,5. Khái niệm ở "
"đó là một siêu phẳng, tuyến tính theo định nghĩa, nên khai triển cơ sở chỉ thêm phương "
"sai chứ không thêm năng lực biểu diễn. Đây là trường hợp mô hình đơn giản hơn lại "
"thắng.\n\n"
"Tôi có chạy cả CoverType nhưng đã bỏ khỏi bảng này. Lý do là sau khi cắt phần khởi "
"động, tỷ lệ lớp dương trong phần được chấm chỉ còn 9,7 phần trăm, nên đoán bừa theo "
"lớp đa số đã được 90,3 điểm. Mọi phương pháp đều nằm trong khoảng một điểm quanh "
"mức đó, thậm chí hai phương pháp còn thấp hơn. Con số trông đẹp nhưng không nói lên "
"điều gì, nên tôi không đưa vào.\n\n""Ngược lại, ba luồng còn lại đều có mức đoán bừa quanh 50 đến 57 điểm, nên các con số "
"ở bảng đều là kết quả học thật sự chứ không phải hiệu ứng mất cân bằng lớp.\n\n"
"Và xuyên suốt cả bốn luồng, kNN thuần luôn ở nhóm kém nhất — đúng như ta sẽ thấy rõ "
"hơn ở slide tiếp theo.",
# 18 -------------------------------------------------------------------------
"Bài báo nêu đúng một điều kiện cho phương pháp của mình: không được để tốc độ học "
"lambda giảm dần về không, với lý do là mô hình sẽ phản ứng ngày càng chậm với trôi. "
"Bài báo không có thực nghiệm nào tách riêng điều kiện này, nên tôi làm thử.\n\n"
"Kết quả là hình phạt lớn nhất xảy ra sau trôi đột ngột, mất 18,6 điểm độ chính xác, "
"và gần như bằng không dưới trôi kéo dài, chỉ mất 0,8 điểm. Điều này ngược với cách "
"diễn đạt của bài báo, vốn gợi ý rằng trôi liên tục mới là nơi một mô hình đóng băng "
"chịu thiệt nhiều nhất.\n\n"
"Cơ chế giải thích như sau. Dưới trôi kéo dài, khái niệm quay 0,01 radian mỗi bước, "
"tức là di chuyển nhanh hơn mọi bước cập nhật cố định; ngay cả lambda hằng số cũng chỉ "
"đạt 88,1 điểm. Đã không bám được thì việc giảm lambda cũng chẳng làm mất thêm gì mấy. "
"Ngược lại, sau khi khái niệm bị lấy mẫu lại hoàn toàn, một lambda còn sống thì học "
"lại được khái niệm mới, còn lambda đã đóng băng thì không; nên mất trọn 18,6 điểm.\n\n"
"Có thể hỏi liệu đây có phải do lambda ban đầu bằng 0,01 là quá nhỏ hay không. Tôi đã "
"kiểm tra trên dải năm mươi lần, với lambda ban đầu bằng 0,01, 0,1 và 0,5. Hình phạt ở "
"trôi kéo dài giữ nguyên mức nhỏ, lần lượt 1,0, 1,2 và 1,4 điểm. Vậy đây không phải "
"hiện tượng giả do chọn tham số.\n\n"
"Kết luận là điều kiện này thực chất nói về khả năng phục hồi sau một gián đoạn, chứ "
"không phải về việc bám theo trôi liên tục.",
# 19 -------------------------------------------------------------------------
"Nhìn vào hình, điều đập vào mắt là đường kNN gần như nằm ngang.\n\n"
"Cụ thể, kNN dao động 0,6 điểm qua cả năm kịch bản, từ 72,7 đến 73,3. Trong khi đó SGD "
"dao động 9,2 điểm, từ 88,1 đến 97,3.\n\n"
"Lý do là trôi hầu như không làm kNN tệ đi, bởi vì kNN chưa bao giờ tích lũy được gì "
"để trôi làm hỏng. Mô hình của nó chính là một trăm mẫu gần nhất, mà một trăm mẫu gần "
"nhất thì luôn thuộc về khái niệm hiện tại, dù có trôi hay không.\n\n"
"Bài báo đưa ra hai nhận xét riêng biệt. Ở mục 7, nó nói năng lực dự báo của phương "
"pháp bộ đệm bị chặn bởi kích thước bộ đệm. Ở Hình 5a, nó nhận xét rằng kNN không có "
"xu hướng đi lên ngay cả khi khái niệm đứng yên và dữ liệu cứ tích lũy thêm. Thực ra "
"đây là cùng một tính chất: cái gì không tích lũy được thì vừa bị chặn trên, vừa không "
"bị trôi làm hại. Trần năng lực và tính trơ trước trôi là hai mặt của một điều.\n\n"
"SAMkNN khắc phục đúng điểm này bằng cách thêm một bộ nhớ dài hạn, và đó là lý do nó "
"tốt hơn hẳn kNN thuần trong bảng kết quả.",
# 20 -------------------------------------------------------------------------
"Có hai tham số mà ảnh hưởng của chúng lớn hơn cả việc chọn phương pháp nào, nên tôi "
"tách riêng ra đây.\n\n"
"Thứ nhất là số chiều của luồng tổng hợp. SGD đạt 57,7 điểm khi số chiều bằng hai, và "
"92,2 điểm khi số chiều bằng hai mươi. Chênh lệch gần 35 điểm. Nguyên nhân là phép "
"quay tôi dùng chỉ làm nhiễu hai trong số các thành phần của theta, nên số chiều càng "
"lớn thì càng nhiều phần của khái niệm sống sót qua mỗi bước, và bài toán càng dễ.\n\n"
"Thứ hai là bậc của khai triển đa thức trong PBF-SGD. Bậc ba cho kết quả thấp hơn bậc "
"hai 3,3 điểm trên Electricity, và tôi đã kiểm tra rằng tốc độ học không ảnh hưởng gì "
"đáng kể trên dải năm mươi lần.\n\n"
"Điều cần rút ra là cả hai biên độ này đều lớn hơn khoảng cách giữa hai phương pháp "
"bất kỳ ở bảng trước. Nghĩa là nếu một kết quả được công bố mà không nói rõ hai tham "
"số này thì ta không diễn giải được nó, và cũng không so sánh được với kết quả khác.",
# 21 -------------------------------------------------------------------------
"Bài báo năm 2018 đề xuất dự báo theta nhưng không xây dựng nó. Phần này tôi xem điều "
"gì đã xảy ra sau đó.",
# 22 -------------------------------------------------------------------------
"Các công trình sau này chia thành bốn hướng.\n\n"
"Hướng chuẩn hóa loại bỏ sự dịch chuyển của phân phối biên và để nguyên phân phối có "
"điều kiện; đại diện là RevIN và SAN. Hướng nhanh chậm cân bằng giữa thích nghi nhanh "
"với dữ liệu mới và nhớ lại các mẫu cũ; đại diện là FSNet và OneNet. Hướng bể khái "
"niệm giữ một mô hình cho mỗi khái niệm rồi chọn mô hình gần nhất với mẫu hiện tại; "
"đại diện là CEP, dùng cho trôi lặp lại.\n\n"
"Ba hướng này đều mang tính phản ứng. Chỉ hướng thứ tư, với công trình Proceed tại KDD "
"2025, mới làm đúng điều Read lập luận. Proceed ước lượng độ trôi giữa dữ liệu huấn "
"luyện gần nhất và mẫu kiểm tra hiện tại, rồi dùng một bộ sinh được học để chuyển ước "
"lượng đó thành điều chỉnh tham số. Tức là nó học hẳn một ánh xạ từ dịch chuyển trong "
"không gian khái niệm sang dịch chuyển trong không gian tham số. Bộ sinh này được "
"huấn luyện trước trên nhiều kiểu trôi tổng hợp khác nhau để tổng quát hóa tốt hơn.\n\n"
"Read lập luận rằng giải bài toán trôi đồng nghĩa với dự báo theta, nhưng ông không "
"xây dựng. Bảy năm sau, Proceed xây dựng đúng ánh xạ đó, theo đúng hướng ông đề xuất. "
"Đây là lý do bài báo 2018 vẫn đáng đọc.\n\n"
"Cần phân biệt với động lượng trong tối ưu: động lượng chỉ ngoại suy tuyến tính trên "
"gradient, còn Proceed học hẳn một ánh xạ có tham số.",
# 23 -------------------------------------------------------------------------
"Với mô hình nền tảng cho chuỗi thời gian, như Chronos hay Moirai, trôi khái niệm "
"không biến mất; nó chỉ đổi vị trí.\n\n"
"Các mô hình này được huấn luyện trước trên kho dữ liệu rất lớn và dùng ở chế độ "
"zero-shot, tức không huấn luyện lại trên miền đích. Nhưng dữ liệu luồng thì vẫn trôi "
"như thường.\n\n"
"Hướng thứ nhất là thích nghi hộp đen. Nếu mô hình được phục vụ qua một API thương "
"mại thì ta không thể sửa trọng số. Công trình gần đây thích nghi bằng cách học cấu "
"trúc sai số của mô hình theo ngữ cảnh, rồi hiệu chỉnh đầu ra dựa trên cấu trúc đó.\n\n"
"Hướng thứ hai là đưa giả định trôi vào ngay trong tiên nghiệm. Drift-Resilient TabPFN "
"tại NeurIPS 2024 xây dựng tiên nghiệm học trong ngữ cảnh với giả định rằng mô hình "
"sinh dữ liệu thay đổi theo thời gian, nhờ đó mô hình học được cách ước lượng, thích "
"nghi và ngoại suy sự thay đổi đó.\n\n"
"Cả hai hướng vẫn là thích nghi liên tục theo đúng nghĩa tôi đã định nghĩa ở phần hai. "
"Tham số chỉ nằm ở chỗ khác: trong ngữ cảnh, hoặc trong một bộ hiệu chỉnh phần dư, chứ "
"không nằm trong trọng số của mô hình.",
# 24 -------------------------------------------------------------------------
"Phần cuối, tôi nói về những gì chưa ai giải quyết, và những thí nghiệm có thể làm "
"ngay trên bộ công cụ tôi đã dựng.",
# 25 -------------------------------------------------------------------------
"Có ba vấn đề còn mở.\n\n"
"Thứ nhất, và quan trọng nhất, là chưa có tiêu chí nào phân biệt trôi thật với ngữ "
"cảnh bị bỏ sót. Phía context-driven shift cho rằng phân phối có điều kiện chỉ có vẻ "
"thay đổi, vì ta thiếu một biến ngữ cảnh. Phía Read cho rằng theta thật sự di chuyển "
"trong không gian tham số. Nếu ngữ cảnh quan sát được và có chu kỳ thì việc bám theo "
"là lãng phí; còn nếu nó tiềm ẩn và không lặp lại thì điều kiện hóa là bất khả. Nhưng "
"không công trình nào cho ta biết đang ở trường hợp nào, trong khi đây lại là câu hỏi "
"phải trả lời trước khi chọn phương pháp.\n\n"
"Thứ hai, trôi lặp lại và trôi kéo dài chia đôi không gian phương pháp. Bể khái niệm "
"giả định khái niệm sẽ quay lại; bộ bám theo giả định khái niệm dịch chuyển trơn. Ranh "
"giới giữa hai giả định này chưa được ai đặc tả.\n\n"
"Thứ ba, đánh giá vẫn dựa trên dữ liệu tổng hợp và giả định nhãn có ngay, trong khi "
"các ứng dụng làm nên động lực của lĩnh vực thì không như vậy.",
# 26 -------------------------------------------------------------------------
"Tôi đề xuất bốn thí nghiệm, mỗi thí nghiệm kèm một dự đoán có thể bị bác bỏ.\n\n"
"Thí nghiệm D là rẻ nhất: quét lưới tốc độ trôi nhân với lambda, tìm lambda tối ưu cho "
"mỗi tốc độ, rồi khớp số mũ trên đồ thị log-log. Dự đoán là lambda tối ưu tỉ lệ với "
"căn bậc hai của tốc độ trôi. Nếu số mũ khớp ra gần 0,5 thì ta biến một cảnh báo định "
"tính thành một quy tắc chỉnh tham số.\n\n"
"Thí nghiệm A giải thích vì sao động lượng không giúp gì. Quỹ đạo thật là một phép "
"quay, tức một đường cong, trong khi động lượng chỉ ngoại suy tuyến tính; nên về dài "
"hạn tác dụng triệt tiêu. Tôi đề xuất thay bằng một bộ ngoại suy khớp đúng dạng hàm, "
"tức ước lượng ma trận quay từ lịch sử của theta ước lượng. Dự đoán là nó thu hẹp "
"khoảng cách bám ở trôi tăng dần, và không có tác dụng gì ở trôi đột ngột. Nếu nó giúp "
"ở mọi nơi thì tức là nó chỉ đang tăng hệ số khuếch đại, và thí nghiệm không chứng "
"minh được gì.\n\n"
"Thí nghiệm C quét chu kỳ lặp, so bộ bám theo với bể khái niệm, và tìm điểm giao. Dự "
"đoán là tồn tại một chu kỳ ngưỡng, dưới ngưỡng đó thì bể khái niệm thắng. Đây là một "
"ranh giới trung thực cho chính luận điểm tôi vừa trình bày.\n\n"
"Thí nghiệm B là thí nghiệm tôi quan tâm nhất, vì nó trả lời trực tiếp vấn đề mở thứ "
"nhất. Tôi sẽ thêm một kiểu trôi trong đó theta phụ thuộc vào một ngữ cảnh có chu kỳ "
"quan sát được, rồi so sánh hai chẩn đoán: tự tương quan của phần dư, là chẩn đoán "
"kiểu Read, và thông tin tương hỗ giữa phần dư với ngữ cảnh, là chẩn đoán kiểu "
"context-driven shift. Dự đoán là tự tương quan sẽ báo động ở cả hai trường hợp nên "
"không phân biệt được, còn thông tin tương hỗ chỉ báo ở trường hợp thứ hai. Nếu đúng, "
"ta có một quy tắc quyết định mà chưa ai công bố.\n\n"
"Thí nghiệm này làm được ngay, vì dữ liệu Electricity đã có sẵn ngữ cảnh chu kỳ quan "
"sát được, gồm 48 khung nửa giờ trong ngày và thứ trong tuần; còn luồng tổng hợp thì "
"cho biết theta thật. Nên tôi dựng và tách được cả hai trường hợp trên cùng một bộ "
"công cụ.",
# 27 -------------------------------------------------------------------------
"Tóm lại.\n\n"
"Trôi khái niệm là sự thay đổi của phân phối có điều kiện theo thời gian, và nó khác "
"với dịch chuyển hiệp biến; phần lớn công trình gần đây lại xử lý cái thứ hai.\n\n"
"Cơ chế thích nghi nào khả dụng là do mô hình được cấu tạo từ cái gì. Một cái cây "
"không có delta theta, nên chỉ mô hình có tham số liên tục mới bám theo được.\n\n"
"Read lập luận rằng trôi kéo theo phụ thuộc thời gian, nên một luồng có trôi chính là "
"một chuỗi thời gian, và ta nên bám theo khái niệm thay vì phát hiện sự thay đổi.\n\n"
"Về thực nghiệm, không phương pháp nào thắng ở mọi luồng; thứ hạng đổi theo dạng "
"trôi và theo việc biên quyết định là tuyến tính hay phi tuyến. Điều kiện về lambda "
"đúng, nhưng nó nói về khả năng phục hồi sau gián đoạn chứ không phải về việc bám "
"theo.\n\n"
"Đề xuất dự báo theta đã được Proceed hiện thực hóa năm 2025.\n\n"
"Và câu hỏi còn mở là làm sao tách được trôi thật với ngữ cảnh chưa bao giờ được mô "
"hình hóa.\n\n"
"Tôi xin dừng ở đây và sẵn sàng nhận câu hỏi.",
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
    ("4.   Experiment", False, 0),
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

# 9b. Detectors in detail ---------------------------------------------------
s = slide("The three tests", "what each detector actually computes")
_y = 1.95
for _name, _formula, _desc in (
    ("DDM (2004) — error rate",
     "p_{i} + s_{i}   ≥   p_{min} + 3·s_{min}",
     "Here s is the binomial standard error; the minimum ever seen is the reference."),
    ("EDDM (2006) — distance between errors",
     "(p′_{i} + 2s′_{i}) ⁄ (p′_{max} + 2s′_{max})   <   β",
     "Here p′ is the mean gap between errors. Errors bunching up signals drift."),
    ("ADWIN (2007) — two-window test",
     "| μ_{W0} − μ_{W1} |   >   ε_{cut}",
     "Every split of the window is tested; ε_{cut} bounds false positives by δ."),
):
    bullets(s, [(_name, True, 0)], top=_y, size=24)
    eq(s, _formula, top=_y + 0.42, size=26)
    bullets(s, [(_desc, False, 0)], top=_y + 1.0, size=21)
    _y += 1.62

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
section("4.  Experiment", "Table 2's six methods rebuilt in the standard library.")

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
s = slide("Results", "prequential accuracy, %")
table(s, [
    ["stream", "kNN", "SAMkNN", "SGD", "PBF-SGD", "HT", "RF-HT"],
    ["Electricity", "73.1", "78.0", "74.3", "80.7", "75.8", "84.5"],
    ["RTG", "61.2", "71.1", "66.9", "82.8", "68.0", "72.5"],
    ["Synthetic", "73.6", "81.1", "92.2", "88.5", "88.0", "86.7"],
], left=M, top=2.35, width=W-2*M, height=2.5,
   col_w=[2.6,1.5,1.9,1.5,1.9,1.5,1.7], size=22)
bullets(s, [
    ("No method wins everywhere: RF-HT leads on Electricity,", False, 0),
    ("PBF-SGD on RTG, plain SGD on the linear synthetic stream.", False, 0),
    ("Majority-class baselines: 57.2, 50.8, 50.9 — all beaten.", False, 0),
], top=5.25, size=24, gap=6)

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
s = slide("Sensitivity", "two parameters dominate the results")
table(s, [
    ["parameter", "measured effect"],
    ["Synthetic dimension d", "SGD 57.7 → 92.2 as d goes 2 → 20"],
    ["PBF-SGD basis degree", "degree 3 scores 3.3 points below degree 2"],
], left=M, top=2.2, width=W-2*M, height=2.0, col_w=[4.2,7.4], size=24,
   align=["l","l"])
bullets(s, [
    ("Either swing exceeds the gap between methods.", True, 0),
    ("A result quoted without these settings is not interpretable.", False, 0),
], top=4.8, size=26, gap=8)

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
    ("No method wins on every stream; the ranking flips.", False, 0),
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
