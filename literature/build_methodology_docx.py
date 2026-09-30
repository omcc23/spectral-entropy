#!/usr/bin/env python3
"""Build methodology.docx with native Word OMML equations (not images)."""

from __future__ import annotations

import html
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path(__file__).resolve().parent / "methodology.docx"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = f'xmlns:m="{M_NS}" xmlns:w="{W_NS}"'


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def t(s: str, sty: str | None = None) -> str:
    body = f'<m:t xml:space="preserve">{esc(s)}</m:t>'
    if sty:
        return f'<m:r><m:rPr><m:sty m:val="{sty}"/></m:rPr>{body}</m:r>'
    return f"<m:r>{body}</m:r>"


def italic(s: str) -> str:
    return t(s, "i")


def roman(s: str) -> str:
    return t(s, "p")


def concat(*parts: str) -> str:
    return "".join(parts)


def ssub(base: str, sub: str) -> str:
    return f"<m:sSub><m:e>{base}</m:e><m:sub>{sub}</m:sub></m:sSub>"


def ssup(base: str, sup: str) -> str:
    return f"<m:sSup><m:e>{base}</m:e><m:sup>{sup}</m:sup></m:sSup>"


def frac(num: str, den: str) -> str:
    return f"<m:f><m:num>{num}</m:num><m:den>{den}</m:den></m:f>"


def acc(base: str, chr_: str) -> str:
    return (
        f'<m:acc><m:accPr><m:chr m:val="{esc(chr_)}"/></m:accPr>'
        f"<m:e>{base}</m:e></m:acc>"
    )


def tilde(base: str) -> str:
    return acc(base, "̃")


def dlim(inner: str, beg: str, end: str) -> str:
    return (
        f'<m:d><m:dPr><m:begChr m:val="{esc(beg)}"/>'
        f'<m:endChr m:val="{esc(end)}"/></m:dPr>'
        f"<m:e>{inner}</m:e></m:d>"
    )


def paren(inner: str) -> str:
    return dlim(inner, "(", ")")


def braces(inner: str) -> str:
    return dlim(inner, "{", "}")


def absbar(inner: str) -> str:
    return dlim(inner, "|", "|")


def nary_sum(expr: str, lower: str, upper: str | None = None) -> str:
    hide = '<m:supHide m:val="1"/>' if upper is None else ""
    sup = f"<m:sup>{upper}</m:sup>" if upper is not None else "<m:sup/>"
    return (
        "<m:nary><m:naryPr>"
        '<m:chr m:val="∑"/><m:limLoc m:val="undOvr"/>'
        f"{hide}</m:naryPr>"
        f"<m:sub>{lower}</m:sub>{sup}<m:e>{expr}</m:e></m:nary>"
    )


def omath(inner: str):
    return parse_xml(f"<m:oMath {NS}>{inner}</m:oMath>")


def omath_para(inner: str):
    return parse_xml(
        f'<m:oMathPara {NS}><m:oMathParaPr><m:jc m:val="center"/>'
        f"</m:oMathParaPr><m:oMath>{inner}</m:oMath></m:oMathPara>"
    )


def H_tilde() -> str:
    return tilde(italic("H"))


def S_tilde() -> str:
    return tilde(italic("S"))


def log2() -> str:
    return ssub(roman("log"), roman("2"))


def log10() -> str:
    return ssub(roman("log"), roman("10"))


def p_c() -> str:
    return ssub(italic("p"), italic("c"))


def n_c() -> str:
    return ssub(italic("n"), italic("c"))


def N_char() -> str:
    return ssub(italic("N"), roman("char"))


def N_content() -> str:
    return ssub(italic("N"), roman("content"))


def C_min() -> str:
    return ssub(italic("C"), roman("min"))


def S_H() -> str:
    return ssub(italic("S"), italic("H"))


def p_f() -> str:
    return ssub(italic("p"), italic("f"))


def E_f() -> str:
    return concat(italic("E"), paren(italic("f")))


def set_body_font(run, *, size=11, bold=False, italic=False, color=None):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def set_paragraph_font(p, *, size=11, after=6, before=0, indent=False, justify=True, center=False):
    pf = p.paragraph_format
    pf.space_after = Pt(after)
    pf.space_before = Pt(before)
    pf.line_spacing = 1.15
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif justify:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent:
        pf.first_line_indent = Cm(0.5)
    p.style.font.name = "Times New Roman"
    for run in p.runs:
        set_body_font(run, size=size)


def add_text_run(p, text, *, bold=False, italic=False, size=11, color=None):
    run = p.add_run(text)
    set_body_font(run, size=size, bold=bold, italic=italic, color=color)
    return run


def add_math(p, inner: str):
    p._p.append(omath(inner))


def mixed(doc, parts, *, lead=None, after=8, indent=False):
    p = doc.add_paragraph()
    set_paragraph_font(p, after=after, indent=indent and lead is None, justify=True)
    if lead:
        add_text_run(p, lead + " ", bold=True)
    for kind, content in parts:
        if kind == "t":
            add_text_run(p, content)
        elif kind == "i":
            add_text_run(p, content, italic=True)
        else:
            add_math(p, content)
    return p


def display(doc, inner: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.space_before = Pt(8)
    pf.space_after = Pt(8)
    pf.line_spacing = 1.15
    p._p.append(omath_para(inner))
    return p


def shade_header_row(row):
    for cell in row.cells:
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = parse_xml(
            '<w:shd xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'w:val="clear" w:color="auto" w:fill="E8E8E8"/>'
        )
        tcPr.append(shd)


def set_cell_margins(cell):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = parse_xml(
        '<w:tcMar xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:top w:w="60" w:type="dxa"/>'
        '<w:left w:w="80" w:type="dxa"/>'
        '<w:bottom w:w="60" w:type="dxa"/>'
        '<w:right w:w="80" w:type="dxa"/>'
        "</w:tcMar>"
    )
    tcPr.append(tcMar)


def apply_table_borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else parse_xml(
        '<w:tblPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
    )
    borders = parse_xml(
        '<w:tblBorders xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:top w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
        '<w:left w:val="nil"/>'
        '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
        '<w:right w:val="nil"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
        '<w:insideV w:val="nil"/>'
        "</w:tblBorders>"
    )
    tblPr.append(borders)


def add_caption(doc, label: str, text: str):
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
    cap.paragraph_format.space_before = Pt(12)
    cap.paragraph_format.space_after = Pt(6)
    add_text_run(cap, label + "  ", bold=True, size=10)
    add_text_run(cap, text, size=10, italic=True)
    return cap


def fill_header_cell(cell, kind, content, left=False):
    set_cell_margins(cell)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT if left else WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    if kind == "t":
        add_text_run(p, content, bold=True, size=10)
    else:
        add_math(p, content)


def fill_text_cell(cell, val, *, bold=False, left=False):
    set_cell_margins(cell)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT if left else WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    add_text_run(p, val, size=10, bold=bold)


def add_rules(doc):
    kicker = doc.add_paragraph()
    kicker.alignment = WD_ALIGN_PARAGRAPH.LEFT
    kicker.paragraph_format.space_after = Pt(2)
    r = kicker.add_run("METHODS")
    set_body_font(r, size=9, color=RGBColor(90, 90, 90))
    r.font.small_caps = True

    rule1 = doc.add_paragraph()
    rule1.paragraph_format.space_before = Pt(0)
    rule1.paragraph_format.space_after = Pt(6)
    pPr = rule1._p.get_or_add_pPr()
    pPr.append(parse_xml(
        '<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:bottom w:val="single" w:sz="12" w:space="1" w:color="000000"/>'
        "</w:pBdr>"
    ))

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title.paragraph_format.space_after = Pt(6)
    tr = title.add_run(
        "Hop-depth spectra, scaling exponent, and entropy of literary syntax"
    )
    set_body_font(tr, size=16, bold=True)

    rule2 = doc.add_paragraph()
    rule2.paragraph_format.space_before = Pt(0)
    rule2.paragraph_format.space_after = Pt(10)
    pPr2 = rule2._p.get_or_add_pPr()
    pPr2.append(parse_xml(
        '<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:bottom w:val="single" w:sz="6" w:space="1" w:color="000000"/>'
        "</w:pBdr>"
    ))


def setup_document() -> Document:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(1.8)
    section.right_margin = Cm(1.8)
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.8)

    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(11)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rpr.append(parse_xml(
            '<w:rFonts xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Times New Roman"/>'
        ))
    else:
        rfonts.set(qn("w:ascii"), "Times New Roman")
        rfonts.set(qn("w:hAnsi"), "Times New Roman")
        rfonts.set(qn("w:eastAsia"), "Times New Roman")

    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = hp.add_run("METHODS")
    set_body_font(run, size=9, color=RGBColor(90, 90, 90))
    run.font.small_caps = True

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_text_run(fp, "", size=9)
    fp._p.append(parse_xml(
        '<w:fldSimple xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'w:instr=" PAGE "/>'
    ))
    for r in fp.runs:
        set_body_font(r, size=9, color=RGBColor(90, 90, 90))
    return doc


def add_ref(doc, text: str):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(2)
    pf.space_before = Pt(0)
    pf.line_spacing = 1.15
    pf.left_indent = Cm(0.6)
    pf.first_line_indent = Cm(-0.6)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    add_text_run(p, text, size=10)


def build() -> None:
    doc = setup_document()
    add_rules(doc)

    # ── Corpus ────────────────────────────────────────────────────────────
    mixed(
        doc,
        [
            (
                "t",
                "We selected 267 public-domain books in nine European languages from Project Gutenberg [1]: "
                "English (98), French (27), Spanish (26), German (26), Italian (25), Polish (19), "
                "Portuguese (19), Swedish (14), and Finnish (13). We downloaded each book as plain text "
                "(.txt). After we removed the Project Gutenberg licence banners, we discarded any file "
                "shorter than ",
            ),
            ("m", concat(C_min(), roman(" = 500"))),
            (
                "t",
                " characters. We kept a book only when spaCy (a grammatical parser that marks each word "
                "and the word it depends on) returned at least ",
            ),
            ("m", concat(N_content(), roman(" = 10,000"))),
            (
                "t",
                " content tokens (words that are not punctuation, spaces, or unreadable symbols). "
                "We curated English titles across novels, drama, verse, and non-fiction, and we removed "
                "duplicates. We dropped two Spanish books whose mean hop-depth was 5 or greater, because "
                "those parses had failed.",
            ),
        ],
        lead="Corpus construction and sampling.",
    )

    # ── Prior encodings ───────────────────────────────────────────────────
    mixed(
        doc,
        [
            (
                "t",
                "Earlier work already turns a text into a number series and takes its Fourier spectrum "
                "(the breakdown of a signal into frequencies): letter sequences [2], word-frequency rank [3], "
                "sentence-length variability (SLV; Drożdż et al. find literary ",
            ),
            ("m", concat(roman("1/"), ssup(italic("f"), italic("β")), roman(" with "), italic("β"), roman(" ≈ 0.5"))),
            (
                "t",
                ") [4], part-of-speech rank [5], and lexical information density [6]. Recursive grammars "
                "produce power-law mutual information; Markov-like strings do not [7]. We apply that "
                "construction to hop-depth [8]. We recompute SLV as a control: it is much flatter than "
                "hop-depth and is not interchangeable with it. Letter and rank series survive "
                "vocabulary-preserving shuffles; hop-depth does not. We compute spectral entropy as in "
                "Verma et al. [9], using Eqs. (1)–(2) of the main text. We report normalized composition "
                "Shannon entropy [10,11] separately, on the text itself rather than on the spectrum.",
            ),
        ],
        lead="Prior text-to-series encodings.",
    )

    # ── Hop-depth ─────────────────────────────────────────────────────────
    mixed(
        doc,
        [
            (
                "t",
                "Hop-depth is the number of grammatical steps from a word to the main verb of its "
                "sentence (the root). Mean hierarchical distance (MHD) is the average of those steps [8]. "
                "MHD usually lies between about 2 and 4. We treat MHD as the mean of a token series and "
                "we analyse that series with a Fourier transform.",
            ),
        ],
        lead="Syntactic hop-depth encoding.",
    )
    mixed(
        doc,
        [
            ("t", "For each language we used spaCy with its largest Universal Dependencies model [12,13] "
                  "(a shared map of which word depends on which). We used a medium or small model only "
                  "when no large model existed. We turned off named-entity recognition (labelling names "
                  "and places), lemmatization (reducing words to dictionary form), and text classification "
                  "so the parser ran faster. We fed the text in blocks of "),
            ("m", concat(italic("K"), roman(" = 50,000"))),
            ("t", " characters until we had collected "),
            ("m", concat(N_content(), roman(" = 10,000"))),
            ("t", " content tokens. We dropped tokens tagged PUNCT, SPACE, or X. For each remaining token "),
            ("m", ssub(italic("t"), italic("i"))),
            ("t", ", hop-depth "),
            ("m", concat(italic("x"), paren(italic("i")))),
            ("t", " is the number of head steps to the root. If a damaged parse looped and never reached "
                  "a root, we stopped the walk at 100 steps so the count could not run away. MHD is the "
                  "mean of that series at "),
            ("m", concat(italic("N"), roman(" = 10,000"))),
            ("t", ":"),
        ],
        after=2,
    )
    display(
        doc,
        concat(
            italic("x"),
            paren(italic("i")),
            roman(" = depth"),
            paren(ssub(italic("t"), italic("i"))),
            roman(",    depth"),
            paren(italic("t")),
            roman(" = min"),
            braces(concat(italic("d"), roman(" : "), ssup(roman("head"), italic("d")), paren(italic("t")), roman(" = "), italic("t"))),
            roman("    (stop at 100),    MHD = "),
            frac(roman("1"), italic("N")),
            nary_sum(
                concat(italic("x"), paren(italic("i"))),
                concat(italic("i"), roman(" = 1")),
                italic("N"),
            ),
            roman("."),
        ),
    )
    mixed(
        doc,
        [
            ("t", "A short example makes the encoding concrete. In "),
            ("m", italic("The cat sat on the mat.")),
            ("t", ", "),
            ("m", italic("sat")),
            ("t", " is the root. Walking each token to that root and dropping the period gives "),
            ("m", concat(italic("x"), roman(" = [2, 1, 0, 1, 3, 2]"))),
            ("t", ", so the sentence MHD is 1.50. Each book series is the concatenation of such "
                  "sentences, truncated at "),
            ("m", italic("N")),
            ("t", "."),
        ],
    )

    # ── PSD ───────────────────────────────────────────────────────────────
    mixed(
        doc,
        [
            ("t", "Each book is one sample per token, so frequency is "),
            ("m", concat(italic("f"), roman(" = "), italic("n"), roman("/"), italic("N"))),
            ("t", " in cycles per word ("),
            ("m", concat(italic("n"), roman(" = 0, …, "), italic("N"), roman(" − 1"))),
            ("t", "), with Nyquist frequency 1/2 and resolution "),
            ("m", concat(italic("Δf"), roman(" = "), ssup(roman("10"), roman("−4")))),
            ("t", ". We subtract the mean of the series and we take a single unwindowed discrete Fourier "
                  "transform (DFT). We do not use Welch or short-time averaging, so the lowest frequency "),
            ("m", concat(italic("f"), roman(" = 1/"), italic("N"))),
            ("t", " remains resolved [4,3]:"),
        ],
        lead="Hop-depth power spectral density.",
        after=2,
    )
    display(
        doc,
        concat(
            italic("x̃"),
            roman(" = "),
            italic("x"),
            roman(" − "),
            italic("x̄"),
            roman(",    "),
            italic("X"),
            paren(italic("f")),
            roman(" = "),
            nary_sum(
                concat(
                    italic("x̃"),
                    paren(italic("n")),
                    roman(" "),
                    ssup(italic("e"), concat(roman("−2π i "), italic("f n"))),
                ),
                concat(italic("n"), roman(" = 0")),
                concat(italic("N"), roman(" − 1")),
            ),
            roman(",    "),
            italic("E"),
            paren(italic("f")),
            roman(" = "),
            ssup(absbar(concat(italic("X"), paren(italic("f")))), roman("2")),
            roman("."),
        ),
    )
    mixed(
        doc,
        [
            ("t", "Subtracting the mean sends "),
            ("m", concat(italic("E"), paren(roman("0")), roman(" ≈ 0"))),
            ("t", ". Because "),
            ("m", italic("x")),
            ("t", " is real, "),
            ("m", concat(italic("E"), paren(italic("f")), roman(" = "), italic("E"), paren(concat(roman("1 − "), italic("f"))))),
            ("t", ", and only the band "),
            ("m", concat(roman("0 < "), italic("f"), roman(" ≤ 1/2"))),
            ("t", " is unique."),
        ],
    )

    # Reuse Nature_entropy_26sept Eqs. (1)–(3); do not renumber them here.
    mixed(
        doc,
        [
            ("t", "We obtain the scaling exponent "),
            ("m", italic("β")),
            ("t", " using Eq. (3) of the main text: ordinary least squares of "),
            ("m", concat(log10(), roman(" "), E_f())),
            ("t", " on "),
            ("m", concat(log10(), roman(" "), italic("f"))),
            ("t", " after a 250-bin moving average over "),
            ("m", concat(roman("0 < "), italic("f"), roman(" ≤ 1/2"))),
            ("t", ". For the same spectrum we compute spectral entropy "),
            ("m", italic("H")),
            ("t", " using Eq. (1) with the mass function"),
        ],
        lead="Spectral entropy and scaling.",
        after=2,
    )
    display(
        doc,
        concat(
            ssub(italic("P"), italic("f")),
            roman(" = "),
            frac(
                E_f(),
                nary_sum(E_f(), italic("f")),
            ),
            roman("."),
        ),
    )
    mixed(
        doc,
        [
            ("t", "Non-positive bins are dropped before the sum. We then report the unit-interval score "),
            ("m", H_tilde()),
            ("t", " from Eq. (2) with "),
            ("m", concat(italic("N"), roman(" = 10,000"))),
            ("t", " ("),
            ("m", concat(log2(), roman(" 10,000 ≈ 13.29"))),
            ("t", "). Eq. (3) already implies "),
            ("m", concat(E_f(), roman(" ∝ "), ssup(italic("f"), concat(roman("−"), italic("β"))))),
            ("t", "; "),
            ("m", concat(italic("β"), roman(" = 1"))),
            ("t", " is pink noise. The spectrum is near-white for "),
            ("m", concat(italic("f"), roman(" ≲ 0.009–0.015"))),
            ("t", "; linearly spaced bins still let the decaying band dominate Eq. (3). "
                  "Restricting that fit to the decaying band steepens "),
            ("m", italic("β")),
            ("t", " by about 0.13–0.20 but does not change language rank. White, pink, and brown "
                  "noise anchors give "),
            ("m", concat(H_tilde(), roman(" ≈ 0.955, 0.747, and 0.253"))),
            ("t", " via Eqs. (1)–(2). Literary hop-depth lies between white and pink."),
        ],
    )

    # ── Real-space Shannon (not the music amplitude-spectrum Shannon) ─────
    mixed(
        doc,
        [
            (
                "t",
                "Separately we compute composition Shannon entropy on the book text itself (real space), "
                "not spectral entropy H from Eq. (1) and not an amplitude envelope. Each distinct Unicode "
                "character is a symbol, including spaces, punctuation, and case. We use the plug-in "
                "estimator [10,11]",
            ),
        ],
        lead="Normalized composition Shannon entropy (real space).",
        after=2,
    )
    display(
        doc,
        concat(
            italic("S"),
            roman(" = −"),
            nary_sum(
                concat(p_c(), roman(" "), log2(), roman(" "), p_c()),
                italic("c"),
            ),
            roman(",     "),
            p_c(),
            roman(" = "),
            frac(n_c(), N_char()),
            roman("."),
        ),
    )
    mixed(
        doc,
        [
            ("t", "This is the maximum-likelihood estimator of Shannon entropy [14]. Shannon used the "
                  "same estimator for printed English [11]. At the character counts of a novel, plug-in "
                  "bias is negligible at the precision we report [15]. Following Eq. (2) we report the "
                  "unit-interval score"),
        ],
        after=2,
    )
    display(
        doc,
        concat(
            S_tilde(),
            roman(" = "),
            frac(italic("S"), concat(log2(), roman(" "), italic("A"))),
            roman("."),
        ),
    )
    mixed(
        doc,
        [
            ("t", "where "),
            ("m", italic("A")),
            ("t", " is the number of distinct characters. "),
            ("m", S_tilde()),
            ("t", " does not use the hop-depth series. We do not bin amplitudes and we do not sample "
                  "an envelope "),
            ("m", concat(italic("P"), paren(italic("t")))),
            ("t", "."),
        ],
    )
    mixed(
        doc,
        [
            ("t", "The same cat-mat sentence used for MHD makes the count concrete. For "),
            ("m", italic("The cat sat on the mat.")),
            ("t", " we have "),
            ("m", concat(N_char(), roman(" = 23"))),
            ("t", " characters and 12 distinct symbols (Table 1). Then"),
        ],
        after=2,
    )
    display(
        doc,
        concat(
            italic("S"),
            roman(" = −"),
            frac(roman("5"), roman("23")),
            log2(),
            frac(roman("5"), roman("23")),
            roman(" − "),
            frac(roman("4"), roman("23")),
            log2(),
            frac(roman("4"), roman("23")),
            roman(" − ⋯  = 3.29 bits/char, so "),
            S_tilde(),
            roman(" = 3.29 / "),
            log2(),
            roman(" 12 = 0.92."),
        ),
    )
    mixed(
        doc,
        [
            ("t", "A book-length English text lands near "),
            ("m", concat(S_tilde(), roman(" = 0.70"))),
            ("t", " because rare letters, digits, and punctuation enlarge "),
            ("m", italic("A")),
            ("t", " faster than they raise "),
            ("m", italic("S")),
            ("t", ". Language means of "),
            ("m", S_tilde()),
            ("t", " appear in Table 2."),
        ],
    )

    add_caption(
        doc,
        "Table 1.",
        "Real-space character counts for “The cat sat on the mat.”  S = 3.29 bits/char; S̃ = 0.92.",
    )
    example_rows = [
        ("space", "5", "5/23", "0.217"),
        ("t", "4", "4/23", "0.174"),
        ("a", "3", "3/23", "0.130"),
        ("e", "2", "2/23", "0.087"),
        ("h", "2", "2/23", "0.087"),
        ("T, c, m, n, o, s, .", "1 each", "1/23", "0.043"),
    ]
    t2 = doc.add_table(rows=1 + len(example_rows), cols=4)
    t2.alignment = WD_TABLE_ALIGNMENT.CENTER
    t2.autofit = True
    shade_header_row(t2.rows[0])
    for i, (kind, content) in enumerate([
        ("t", "Symbol"),
        ("t", "Count n"),
        ("t", "p = n / 23"),
        ("t", "p (decimal)"),
    ]):
        fill_header_cell(t2.rows[0].cells[i], kind, content, left=(i == 0))
    for r_i, row in enumerate(example_rows, start=1):
        for c_i, val in enumerate(row):
            fill_text_cell(t2.rows[r_i].cells[c_i], val, bold=(c_i == 0), left=(c_i == 0))
    apply_table_borders(t2)

    mixed(
        doc,
        [
            ("t", "Unless we note otherwise, we used "),
            ("i", "Pride and Prejudice"),
            ("t", ", the English small parser, "),
            ("m", E_f()),
            ("t", ", and "),
            ("m", concat(italic("N"), roman(" = 10,000"))),
            ("t", ". White, pink, and brown noise anchors give "),
            ("m", concat(H_tilde(), roman(" ≈ 0.955, 0.747, and 0.253"))),
            ("t", ". Literary hop-depth lies between white and pink, and corpus MHD anti-correlates "
                  "with "),
            ("m", H_tilde()),
            ("t", " (Pearson "),
            ("m", concat(italic("r"), roman(" = −0.63"))),
            ("t", ")."),
        ],
        lead="Ablations.",
    )
    mixed(
        doc,
        [
            ("t", "Sentence shuffle leaves the scaling almost unchanged ("),
            ("m", concat(italic("s"), roman(" = −1.079 → −1.066"))),
            ("t", "; Shakespeare "),
            ("m", concat(italic("Δs"), roman(" = −0.040"))),
            ("t", "). Phase randomisation leaves "),
            ("m", H_tilde()),
            ("t", " unchanged. A part-of-speech-constrained word shuffle followed by re-parsing stays "
                  "pink. SLV [4] is much flatter ("),
            ("m", concat(italic("s"), roman(" ≈ −0.20"))),
            ("t", ") than hop-depth ("),
            ("m", concat(italic("s"), roman(" ≈ −1.08"))),
            ("t", "). Subtracting each sentence’s mean depth yields "),
            ("m", concat(italic("s"), roman(" = −0.938"))),
            ("t", ", which is not white; per-sentence mean depth tracks SLV. On twelve texts, about "
                  "76% ± 5% of "),
            ("m", concat(absbar(italic("s")))),
            ("t", " is intra-sentence. Even forcing every sentence to length 23 remains pink ("),
            ("m", concat(italic("s"), roman(" = −0.897"))),
            ("t", ")."),
        ],
    )

    # ── Summary + Table 1 ─────────────────────────────────────────────────
    mixed(
        doc,
        [
            ("t", "Table 2 reports language means. "),
            ("m", italic("β")),
            ("t", " is Eq. (3), MHD is mean hop-depth, "),
            ("m", H_tilde()),
            ("t", " is Eq. (2), and "),
            ("m", S_tilde()),
            ("t", " is normalized composition Shannon."),
        ],
        lead="Cross-linguistic summary.",
    )

    add_caption(
        doc,
        "Table 2.",
        "Language means (N = 10,000 hop-depths/book). β: Eq. (3). H̃: Eq. (2). "
        "S̃: normalized composition Shannon.",
    )
    lang_rows = [
        ("English", "IE/Germanic", "98", "3.07", "1.07", "0.85", "0.70"),
        ("Spanish", "IE/Romance", "26", "2.53", "0.86", "0.86", "0.70"),
        ("French", "IE/Romance", "27", "2.44", "0.85", "0.86", "0.69"),
        ("Swedish", "IE/Germanic", "14", "2.42", "0.90", "0.87", "0.70"),
        ("Finnish", "Uralic", "13", "2.03", "0.88", "0.87", "0.70"),
        ("Portuguese", "IE/Romance", "19", "2.38", "0.81", "0.88", "0.68"),
        ("German", "IE/Germanic", "26", "2.40", "0.91", "0.88", "0.72"),
        ("Italian", "IE/Romance", "25", "2.47", "0.81", "0.88", "0.70"),
        ("Polish", "IE/Slavic", "19", "2.84", "0.78", "0.89", "0.70"),
    ]
    t1 = doc.add_table(rows=1 + len(lang_rows), cols=7)
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    t1.autofit = True
    shade_header_row(t1.rows[0])
    headers = [
        ("t", "Language"),
        ("t", "Family"),
        ("t", "n"),
        ("t", "MHD"),
        ("m", italic("β")),
        ("m", H_tilde()),
        ("m", S_tilde()),
    ]
    for i, (kind, content) in enumerate(headers):
        fill_header_cell(t1.rows[0].cells[i], kind, content, left=(i < 2))
    for r_i, row in enumerate(lang_rows, start=1):
        for c_i, val in enumerate(row):
            fill_text_cell(t1.rows[r_i].cells[c_i], val, bold=(c_i == 0), left=(c_i < 2))
    apply_table_borders(t1)

    refs_h = doc.add_paragraph()
    refs_h.paragraph_format.space_before = Pt(14)
    refs_h.paragraph_format.space_after = Pt(6)
    add_text_run(refs_h, "References.", bold=True, size=11)

    refs = [
        "[1]  Project Gutenberg. https://www.gutenberg.org/.",
        "[2]  W. Ebeling and A. Neiman, Physica A 215, 233 (1995).",
        "[3]  M. A. Montemurro and P. A. Pury, Fractals 10, 451 (2002).",
        "[4]  S. Drożdż et al., Inf. Sci. 331, 32 (2016).",
        "[5]  E. De Santis, G. De Santis, A. Rizzi, IEEE Trans. Pattern Anal. Mach. Intell. 45, 10143 (2023).",
        "[6]  Y. Xu and D. Reitter, in ACL (2017), p. 623.",
        "[7]  H. W. Lin and M. Tegmark, Entropy 19, 299 (2017).",
        "[8]  Y. Jing and H. Liu, in Depling (2015), p. 161.",
        "[9]  M. K. Verma et al., Phys. Rev. E 110, 055106 (2024).",
        "[10] C. E. Shannon, Bell Syst. Tech. J. 27, 379 (1948).",
        "[11] C. E. Shannon, Bell Syst. Tech. J. 30, 50 (1951).",
        "[12] M. Honnibal and I. Montani. spaCy 2 (2017). https://spacy.io/.",
        "[13] M.-C. de Marneffe et al., Comput. Linguist. 47, 255 (2021).",
        "[14] T. M. Cover and J. A. Thomas, Elements of Information Theory, 2nd ed. (Wiley, 2006).",
        "[15] L. Paninski, Neural Comput. 15, 1191 (2003).",
    ]
    for line in refs:
        add_ref(doc, line)

    doc.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
