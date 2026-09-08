#!/usr/bin/env python3
"""
Facsimile page builder for the LJ Idol reader (step 2: run after prep.py).

For each PDF page we emit
  pages/<article-id>/<n>.html   - background JPEG + absolutely positioned live text
  pages/<article-id>/p<n>.jpg   - the page with its text removed (images + vector art kept)
  pages/<article-id>/cover.jpg  - first page, full render, for the cover card
  pages/<article-id>/text.json  - reading-order plain text (for the static article pages)

Coordinates: PDF points x 1.6 = page pixels (same convention as the other two readers).
Adds, over each page: the picture hotspots (hover text + screen-reader text from _pics/<id>.json) and the folio line.
"""
import json, os, re, sys, html
import pymupdf as fitz

SCALE = 1.6
PIC_DPI = 150          # the enlargeable copy of each picture: generous on screen, modest on disk
PIC_Q = 86
PT_MM = 25.4 / 72.0
MARGIN = 72.0          # the Word file's side margins, in points: the folio aligns to them
FOLIO_BASE = 46.0      # folio baseline, points up from the foot of the page
PICS = []; PICPOS = []; FOLIO_SLUG = ''; FOLIO_COLOR = '#228B22'; COMMENT = {}

SERIF_HINTS = ('times', 'liberationserif', 'liberation serif', 'dejavuserif', 'palatino', 'georgia', 'garamond', 'minion', 'book antiqua', 'palladio',
               'century schoolbook', 'baskerville', 'cambria', 'caslon', 'bodoni', 'didot', 'antigoni')
MONO_HINTS = ('courier', 'mono', 'consolas')

GLYPH = {0xF0B7: '•', 0xF0A7: '▪', 0xF0D8: '→', 0xF0FC: '✓', 0xF0A8: '□', 0xF06E: '■'}


def savepix(pix, path, q=82):
    """fitz unlinks before it writes, which some mounted folders refuse; write beside it, then copy over."""
    import tempfile, shutil
    fd, tmp = tempfile.mkstemp(suffix=os.path.splitext(path)[1]); os.close(fd)
    pix.save(tmp, jpg_quality=q); shutil.copyfile(tmp, path); os.remove(tmp)

FONTMAP = {}    # basefont -> (family, bold, italic), read from the embedded font programs
def learn_fonts(doc):
    """Word's 'print to PDF' route names the fonts CIDFont+F1... and blanks the descriptor; the TrueType
    subset inside still carries the family name, weight and italic flag. Read those."""
    import io, re as _re
    from fontTools.ttLib import TTFont
    FONTMAP.clear()
    for pg in doc:
        for xref, ext, typ, base, name, enc in pg.get_fonts():
            if base in FONTMAP: continue
            try:
                buf = None
                try: buf = doc.extract_font(xref)[-1]
                except Exception: pass
                if not buf:
                    arr = doc.xref_get_key(xref, 'DescendantFonts')[1]
                    m = _re.search(r'FontFile2 (\d+) 0 R', arr) or _re.search(r'FontFile3 (\d+) 0 R', arr)
                    if m: buf = doc.xref_stream(int(m.group(1)))
                if not buf: continue
                f = TTFont(io.BytesIO(buf))
                nm = {r.nameID: r.toUnicode() for r in f['name'].names if r.platformID == 3}
                fam_ = nm.get(16) or nm.get(1) or base
                bold = ('OS/2' in f and f['OS/2'].usWeightClass >= 600) or bool('OS/2' in f and f['OS/2'].fsSelection & 32)
                ital = bool('OS/2' in f and f['OS/2'].fsSelection & 1) or (('post' in f) and f['post'].italicAngle != 0)
                FONTMAP[base] = (fam_, bold, ital)
            except Exception:
                pass

def fam(fontname):
    if fontname in FONTMAP: fontname = FONTMAP[fontname][0]
    f = fontname.lower()
    if any(h in f for h in MONO_HINTS):
        return "'Courier New',Courier,monospace"
    if any(h in f for h in SERIF_HINTS):
        if 'palatino' in f or 'palladio' in f:
            return "'TeX Gyre Pagella','Palatino Linotype',Palatino,'Book Antiqua',Georgia,serif"
        return "'Liberation Serif','Times New Roman',Times,serif"
    if 'calibri' in f or 'carlito' in f:
        return "Carlito,Calibri,'Segoe UI',Arial,sans-serif"
    if 'liberationsans' in f or 'liberation sans' in f or 'arial' in f or 'helvetica' in f:
        return "Arial,'Liberation Sans',Helvetica,sans-serif"
    return "Carlito,Calibri,'Segoe UI','Helvetica Neue',Arial,sans-serif"

# The Australian issues were typeset with a font whose quote glyphs are mis-mapped
# in the PDF text layer; these are the corrections (only applied when AUQUOTES is set).
AUQ = {'\u201f': '\u2019', '\u2015': '\u201c', '\u2016': '\u201d', '\u2018': '\u2019', '\u2017': '\u2018', '\u201e': '\u201c'}
AUQUOTES = False

def smart(t):
    """Straight quotes to curly. Openers after a space, bracket or dash, or at the start; closers otherwise;
    a lone apostrophe inside a word is always the right single quote."""
    t = re.sub(r'(^|[\s(\[{:;=\u2014\u2013-])"', lambda m: m.group(1) + '\u201c', t)
    t = t.replace('"', '\u201d')
    t = re.sub(r"(^|[\s(\[{:;=\u2014\u2013-])'(?=\S)", lambda m: m.group(1) + '\u2018', t)
    t = t.replace("'", '\u2019')
    return t
SMARTQUOTES = True
DEHYPHENATE = False    # True only if Word's automatic hyphenation is on for the entry (then a line-end hyphen is a break, not a hyphen)
def clean(t):
    t = unlig(t)
    if SMARTQUOTES: t = smart(t)
    out = []
    for ch in t:
        if AUQUOTES and ch in AUQ: ch = AUQ[ch]
        o = ord(ch)
        if o in GLYPH: out.append(GLYPH[o])
        elif 0xF000 <= o <= 0xF0FF: out.append('•')
        elif o == 0xAD: continue
        else: out.append(ch)
    return ''.join(out)

def span_style(s):
    st = ["font-family:" + fam(s['font'])]
    fl = s['flags']; fn = s['font'].lower()
    known = FONTMAP.get(s['font'])
    bold = known[1] if known else ((fl & 16) or 'bold' in fn or 'black' in fn or 'semibold' in fn or 'heavy' in fn)
    ital = known[2] if known else ((fl & 2) or 'italic' in fn or 'oblique' in fn)
    if bold: st.append('font-weight:700')
    if ital: st.append('font-style:italic')
    if fl & 1:
        st.append('vertical-align:super;font-size:.7em')
    return ';'.join(st)

_VOWEL = set('aeiouyAEIOUY')
def wordlike(tok):
    t = tok.strip('.,;:!?()[]"\'‘’“”-–—')
    if not t: return False
    if t.lower() in ('a', 'i', 'oh', 'ok', 'us', 'nsw', 'qld', 'vic', 'wa', 'sa', 'nt', 'act', 'usa', 'uk', 'nz'): return True
    if not re.fullmatch(r"[A-Za-z][A-Za-z'’-]*|\d[\d.,%]*(st|nd|rd|th)?", t): return False
    if re.search(r'[a-z][A-Z]', t): return False          # mIxEd case is a picture, not a word
    if t[0].isdigit(): return True
    has_v = any(c in _VOWEL for c in t); has_c = any(c.isalpha() and c not in _VOWEL for c in t)
    return has_v and has_c
def ocr_keep(text):
    toks = text.split()
    good = [t for t in toks if wordlike(t)]
    if len(toks) == 1: return len(good) == 1 and len(good[0]) >= 6
    return len(good) >= 2 and len(good) / len(toks) >= 0.6

LIGFIX = False   # some PDFs carry a phantom space after every fi/fl ligature; set per article
def unlig(t):
    return re.sub(r'\b(\w*(?:fi|fl|ff|ffi|ffl)) (?=[a-z])', r'\1', t) if LIGFIX else t

def inter(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1]); x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    return max(0, x1 - x0) * max(0, y1 - y0)

def build_page(doc, pno, outdir, n, title, links_out, manual=(), ocr=False):
    page = doc[pno]
    W, H = page.rect.width, page.rect.height
    flags = fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_MEDIABOX_CLIP  # ligatures expanded
    if ocr:
        # scanned / rasterised page: recognise the text so it can be selected, searched and read aloud,
        # but draw it transparent over the untouched picture
        tp = page.get_textpage_ocr(full=True, dpi=220)
        d = page.get_text('dict', textpage=tp, flags=flags)
        for b_ in d['blocks']:                       # the usual misreads of a display face
            for l_ in b_.get('lines', []):
                for s_ in l_['spans']:
                    s_['text'] = re.sub(r'(?<![A-Za-z])ln(?![A-Za-z])', 'In', re.sub(r'(?<!\S)\|(?!\S)', 'I', s_['text']))
    else:
        d = page.get_text('dict', flags=flags)
    uris = [(l['from'], l['uri']) for l in page.get_links() if l.get('kind') == fitz.LINK_URI and l.get('uri')]

    lines_html, redact, textlines, paras = [], [], [], []
    # Word spreads a justified line's words out with big gaps, and MuPDF then hands them back as several
    # "lines" on one baseline. Sew those back together (in x order) before anything else looks at them.
    def sew(lines):
        rows = {}
        for l in lines:
            k = round(l['bbox'][3] * 2) / 2
            rows.setdefault(k, []).append(l)
        out = []
        for k in sorted(rows):
            parts = sorted(rows[k], key=lambda l: l['bbox'][0])
            if len(parts) == 1: out.append(parts[0]); continue
            m = dict(parts[0]); m['spans'] = []; x0, y0, x1, y1 = parts[0]['bbox']
            for i, pt in enumerate(parts):
                sp = [dict(s) for s in pt['spans']]
                if i and sp and not sp[0]['text'].startswith(' ') and m['spans'] and not m['spans'][-1]['text'].endswith(' '):
                    sp[0]['text'] = ' ' + sp[0]['text']
                m['spans'] += sp
                x0 = min(x0, pt['bbox'][0]); y0 = min(y0, pt['bbox'][1]); x1 = max(x1, pt['bbox'][2]); y1 = max(y1, pt['bbox'][3])
            m['bbox'] = (x0, y0, x1, y1); out.append(m)
        return out
    # the column edges on this page: right-hand ends that three or more lines share
    def vis_x1(l):
        # MuPDF's line box includes the trailing space Word writes after every line; the visible
        # right end is a space (0.25 em) back per trailing space
        spans = [s_ for s_ in l['spans'] if s_['text']]
        if not spans: return l['bbox'][2]
        last = spans[-1]; t = last['text']; n_ = len(t) - len(t.rstrip(' \u00a0'))
        return l['bbox'][2] - n_ * 0.25 * last['size']
    # the column edges on this page: right-hand ends that three or more lines share (within a point)
    ends = []
    for b in d['blocks']:
        if b['type'] != 0: continue
        for l in sew(b['lines']):
            if sum(len(s['text'].strip()) for s in l['spans']) >= 20: ends.append(vis_x1(l))
    ends.sort(); EDGES = []; i_ = 0
    while i_ < len(ends):
        j_ = i_
        while j_ + 1 < len(ends) and ends[j_ + 1] - ends[i_] <= 1.0: j_ += 1
        if j_ - i_ + 1 >= 3: EDGES.append(sum(ends[i_:j_ + 1]) / (j_ - i_ + 1))
        i_ = j_ + 1
    def at_edge(x1): return any(abs(x1 - e) <= 1.6 for e in EDGES)
    for b in d['blocks']:
        if b['type'] != 0: continue
        blines = [l for l in sew(b['lines']) if any(s['text'].strip() for s in l['spans'])]
        if ocr: blines = [l for l in blines if ocr_keep(''.join(s['text'] for s in l['spans']))]
        if not blines: continue
        # MuPDF can run a heading and the body under it into one block; break a block where the type size
        # changes, so the text version gets the title as its own heading
        groups, cur = [], []
        for l in blines:
            lsz = max((s_['size'] for s_ in l['spans'] if s_['text'].strip()), default=0)
            if cur and lsz and cur[-1][1] and abs(lsz - cur[-1][1]) > 0.15 * max(lsz, cur[-1][1]):
                groups.append(cur); cur = []
            cur.append((l, lsz))
        if cur: groups.append(cur)
        for grp in groups:
            glines = [l for l, _ in grp]
            ptxt = ''
            for l in glines:
                t = clean(''.join(s['text'] for s in l['spans'])).strip()
                if not t: continue
                if ptxt.endswith('-') and t[:1].islower(): ptxt = (ptxt[:-1] if DEHYPHENATE else ptxt) + t   # 'then-' + 'very': one word, hyphen kept
                else: ptxt = (ptxt + ' ' + t).strip()
            if ptxt and ocr:                                   # drop runs of two or more junk tokens
                toks, out, run = ptxt.split(), [], []
                for tk in toks + [None]:
                    if tk is not None and not wordlike(tk): run.append(tk); continue
                    if len(run) == 1: out += run
                    run = []
                    if tk is not None: out.append(tk)
                ptxt = ' '.join(out)
            if ptxt:
                sz = max(s['size'] for l in glines for s in l['spans'])
                gx0 = min(l['bbox'][0] for l in glines); gx1 = max(l['bbox'][2] for l in glines); gy0 = min(l['bbox'][1] for l in glines)
                paras.append({'t': ptxt, 'size': round(sz, 1), 'y': round(gy0, 1), 'x': round(gx0, 1), 'w': round(gx1 - gx0, 1)})
        widths = [vis_x1(l) - l['bbox'][0] for l in blines]
        maxw = max(widths)
        for li, l in enumerate(blines):
            if abs(l['dir'][0]) < 0.9:      # rotated text: leave it in the picture
                continue
            x0, y0, x1, y1 = l['bbox']; x1 = vis_x1(l)
            spans = [s for s in l['spans'] if s['text']]
            if not spans: continue
            size = max(s['size'] for s in spans)
            segs = []                      # (text, style, href)
            for s in spans:
                t = clean(s['text'])
                if not t: continue
                href = None
                sb = s['bbox']; sa = max(1e-6, (sb[2]-sb[0])*(sb[3]-sb[1]))
                for r, u in uris:
                    if inter(sb, (r.x0, r.y0, r.x1, r.y1)) > 0.5 * sa:
                        href = u; break
                if href: links_out.append(href)
                segs.append([t, span_style(s), href])
            if not segs: continue
            just = at_edge(x1) and (li < len(blines) - 1 or len(blines) == 1 or widths[li] >= 0.985 * maxw)
            attrs = ' data-w="%.1f"' % ((x1 - x0) * SCALE) + (' data-j="1"' if just else '')
            lines_html.append(['<p style="position:absolute;left:%.1fpx;top:%.1fpx;font-size:%.1fpx;white-space:nowrap"%s>'
                              % (x0 * SCALE, y0 * SCALE, size * SCALE, attrs), segs])
            redact.append(fitz.Rect(x0 - 0.5, y0 - 0.5, l['bbox'][2] + 0.5, y1 + 0.5))
            textlines.append(''.join(clean(s['text']) for s in spans))

    apply_links(lines_html, n, links_out, [m for m in manual if m.get('page') == n])
    def _unlink_tail(segs):
        # a link that ends a line carries the line's trailing space; keep the space out of the anchor
        # so a stretched (justified) line does not grow an underlined gap after the last word
        if segs and segs[-1][2] and segs[-1][0].endswith(' '):
            t, st, h = segs[-1]; segs[-1] = [t.rstrip(' '), st, h]; segs.append([' ', st, None])
        return segs
    lines_html = [head + ''.join(render_seg(t, st, h) for t, st, h in _unlink_tail(segs)) + '</p>' for head, segs in lines_html]
    bg = fitz.open(); bg.insert_pdf(doc, from_page=pno, to_page=pno)
    bp = bg[0]
    for r in ([] if ocr else redact): bp.add_redact_annot(r)
    if not ocr: bp.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE, text=fitz.PDF_REDACT_TEXT_REMOVE)
    pix = bp.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), alpha=False)
    savepix(pix, os.path.join(outdir, 'p%d.jpg' % n), 82)
    if n == 1:
        savepix(page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0), alpha=False), os.path.join(outdir, 'cover.jpg'), 85)
    bg.close()

    # Pictures. p<n>.jpg keeps the artwork, so each hotspot is invisible - it marks where a picture is so the
    # reader can grow it. It grows into the ORIGINAL file from the Word document (pic<k>), matched here by
    # pixel size; the hover text and the screen-reader description come from _pics/<id>.json.
    pics_html = []
    used = set()
    for inf in page.get_image_info(xrefs=True):
        r = fitz.Rect(inf['bbox']) & page.rect
        if r.is_empty or r.is_infinite or r.width < 30 or r.height < 30: continue
        cand = [p for p in PICS if p['w'] == inf['width'] and p['h'] == inf['height'] and p['file'] not in used]
        if not cand:
            cand = [p for p in PICS if abs(p['w']/p['h'] - inf['width']/inf['height']) < 0.02 and p['file'] not in used]
        if not cand:
            print('   page %d: picture %dx%d not matched to the Word file' % (n, inf['width'], inf['height'])); continue
        p = cand[0]; used.add(p['file'])
        hover = p.get('hover') or ''; alt = p.get('alt') or hover or 'Picture'
        deco = alt.strip() == '-'
        if deco: alt = ''; hover = ''
        PICPOS.append({'page': n, 'file': p['file'], 'deco': deco, 'x': round(r.x0, 1), 'y': round(r.y0, 1), 'w': round(r.width, 1), 'h': round(r.height, 1), 'alt': alt, 'hover': hover})
        if p['w'] < 1.25 * r.width * SCALE: continue      # shown at (near) full size already: nothing to grow into
        pics_html.append('<a class="pic" data-src="%s" data-nw="%d" data-nh="%d" '
                         'style="left:%.1fpx;top:%.1fpx;width:%.1fpx;height:%.1fpx"%s%s></a>'
                         % (p['file'], p['w'], p['h'], r.x0 * SCALE, r.y0 * SCALE, r.width * SCALE, r.height * SCALE,
                            (' title="%s"' % html.escape(hover, quote=True)) if hover else '',
                            ' aria-hidden="true" tabindex="-1"' if deco else ' aria-label="%s"' % html.escape(alt, quote=True)))

    # the folio: issue slug at the left margin, page number at the right, in the bottom margin.
    # Decoration for sighted readers; hidden from screen readers so it is not read out thirteen times.
    # ...except where a picture bleeds over the slot: a magazine drops the folio there rather than print on the photo.
    fy = (H - FOLIO_BASE) * SCALE
    imgs = [fitz.Rect(i['bbox']) for i in page.get_image_info()]
    slotL = fitz.Rect(MARGIN, H - FOLIO_BASE - 9, MARGIN + 150, H - FOLIO_BASE + 4)
    slotR = fitz.Rect(W - MARGIN - 40, H - FOLIO_BASE - 9, W - MARGIN, H - FOLIO_BASE + 4)
    showL = not any(r.intersects(slotL) for r in imgs); showR = not any(r.intersects(slotR) for r in imgs)
    lj = ('<a class="o l" href="%s" target="_blank" rel="noopener" tabindex="-1"><img src="../../assets/lj.png" alt="">LiveJournal</a>' % html.escape(COMMENT['lj'], quote=True)) if COMMENT.get('lj') else '<span></span>'
    dw = ('<a class="o r" href="%s" target="_blank" rel="noopener" tabindex="-1"><img src="../../assets/dw.png" alt="">Dreamwidth</a>' % html.escape(COMMENT['dw'], quote=True)) if COMMENT.get('dw') else '<span></span>'
    comment = ('<div class="cmt" style="top:%.1fpx">%s<button type="button" aria-expanded="false" '
               'onclick="var o=this.parentNode.classList.toggle(\'open\');this.setAttribute(\'aria-expanded\',o);this.parentNode.querySelectorAll(\'a\').forEach(function(a){a.tabIndex=o?0:-1})">'
               '<span class="ic">&#x1F4AC;</span> Comment</button>%s</div>' % (fy - 7, lj, dw)) if (COMMENT.get('lj') or COMMENT.get('dw')) else ''
    folio = comment + '<div class="folio" aria-hidden="true">' + \
            (('<span class="fl" style="left:%.1fpx;top:%.1fpx">%s</span>' % (MARGIN * SCALE, fy, html.escape(FOLIO_SLUG))) if showL else '') + \
            (('<span class="fr" style="right:%.1fpx;top:%.1fpx">%d</span>' % (MARGIN * SCALE, fy, n)) if showR else '') + '</div>'
    pw, ph = round(W * SCALE), round(H * SCALE)
    wmm, hmm = W * PT_MM, H * PT_MM
    scaler = (wmm * 96 / 25.4) / pw
    doc_html = HEAD % dict(title=html.escape(title), n=n, wmm=wmm, hmm=hmm, scaler=scaler, pw=pw, ph=ph, fcol=FOLIO_COLOR)
    if ocr: doc_html = doc_html.replace('p{margin:0;position:absolute}', 'p{margin:0;position:absolute;color:transparent}\np::selection,p *::selection{background:rgba(249,197,0,.45);color:transparent}')
    doc_html += ('<img class="bg" src="p%d.jpg" alt="">\n' % n + '\n'.join(lines_html)
                 + ('\n' + '\n'.join(pics_html) if pics_html else '') + '\n' + folio
                 + '\n</div></div></div>\n' + TAIL)
    open(os.path.join(outdir, '%d.html' % n), 'w', encoding='utf-8').write(doc_html)
    return {'lines': textlines, 'paras': paras, 'mm': [round(wmm, 2), round(hmm, 2)]}

def render_seg(t, st, href):
    inner = '<span style="%s">%s</span>' % (st, html.escape(t, quote=False))
    return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (html.escape(href, quote=True), inner) if href else inner

DOCLINKS = []; LINKI = 0; FOUND = []          # hyperlinks harvested from the .docx, in document order
_QMAP = {0x201c: '"', 0x201d: '"', 0x2018: "'", 0x2019: "'", 0x2013: '-', 0x2014: '-', 0xa0: ' '}
def _norm(t): return re.sub(r'-\s+', '-', re.sub(r'\s+', ' ', t.translate(_QMAP))).strip().lower()   # 'then-' + newline + 'very' == 'then-very'
PAGE_TEXT = {}

def apply_links(lines, n, links_out, manual=()):
    """Turn phrases into links across the page's lines (a phrase may run over several lines and spans).
    Two sources: the .docx's own hyperlinks, consumed in document order with a cursor that moves page by
    page (so a phrase that recurs gets the right address each time), and any manual specs for this page."""
    global LINKI
    if not lines: return
    # one character stream over the page, with a map back to (line, segment, char)
    stream, index = '', []
    for ln, (head, segs) in enumerate(lines):
        for sn, seg in enumerate(segs):
            for ci, ch in enumerate(seg[0]): stream += ch; index.append((ln, sn, ci))
        stream += ' '; index.append(None)
    low = stream.translate(_QMAP).lower()
    nstr, npos, prev_sp = '', [], False
    for i_, ch in enumerate(low):
        sp = ch.isspace()
        if sp and (prev_sp or nstr.endswith('-')): continue      # same rules as _norm: one space, none after a hyphen
        nstr += ' ' if sp else ch; npos.append(i_); prev_sp = sp
    url_at = {}                                   # stream position -> url
    def take(k, want, url):
        for q in npos[k:k + len(want)]: url_at[q] = url
    pos = 0; used = set()
    def find(want):
        """first occurrence after the cursor; failing that, anywhere on the page not already linked
        (the page stream is in block order, which is not always reading order)"""
        def free(k): return not any((k + q) in used for q in range(len(want)))
        k = nstr.find(want, pos)
        if k >= 0 and free(k): return k
        k = 0
        while True:
            k = nstr.find(want, k)
            if k < 0: return -1
            if free(k): return k
            k += 1
    while LINKI < len(DOCLINKS):
        text, url = DOCLINKS[LINKI]; want = _norm(text)
        if len(want) < 2: LINKI += 1; continue
        k = find(want)
        if k < 0:
            # not on this page. If it is on a later page, wait for it; if it is nowhere, note it and move on
            # rather than jam the queue behind it.
            if any(want in PAGE_TEXT.get(m, '') for m in range(n + 1, max(PAGE_TEXT) + 1 if PAGE_TEXT else n)): break
            print('   hyperlink text not found in the pages, skipped: %r' % text[:60]); LINKI += 1; continue
        take(k, want, url); used.update(range(k, k + len(want)))
        FOUND.append({'page': n, 'text': text, 'url': url}); links_out.append(url)
        pos = max(pos, k + len(want)); LINKI += 1
    for spec in manual:
        want = _norm(spec['text']); k = nstr.find(want)
        if k < 0: print('   manual link phrase not found on page %d: %s' % (n, spec['text'])); continue
        take(k, want, spec['url']); links_out.append(spec['url'])
    if not url_at: return
    # rebuild every touched segment, splitting where the link changes
    base = 0
    for ln, (head, segs) in enumerate(lines):
        new = []
        for sn, seg in enumerate(segs):
            t, st, h = seg; L = len(t)
            marks = [url_at.get(base + ci, h) for ci in range(L)]; base += L
            if all(m == h for m in marks): new.append(seg); continue
            start = 0
            for ci in range(1, L + 1):
                if ci == L or marks[ci] != marks[start]:
                    new.append([t[start:ci], st, marks[start]]); start = ci
        base += 1                                  # the line separator
        lines[ln][1] = new

def docx_links(path):
    """(text, url) for every external hyperlink in the Word file, in document order."""
    import zipfile
    z = zipfile.ZipFile(path)
    doc = z.read('word/document.xml').decode('utf-8'); rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
    doc = re.sub(r'<mc:Fallback>.*?</mc:Fallback>', '', doc, flags=re.S)  # text boxes repeat their content in the VML fallback
    rmap = {}
    for rel in re.findall(r'<Relationship [^>]*/>', rels):
        if 'TargetMode="External"' not in rel: continue
        i_ = re.search(r'Id="([^"]+)"', rel); t_ = re.search(r'Target="([^"]+)"', rel)
        if i_ and t_: rmap[i_.group(1)] = html.unescape(t_.group(1))
    out = []
    for m in re.finditer(r'<w:hyperlink [^>]*r:id="([^"]+)"[^>]*>(.*?)</w:hyperlink>', doc, re.S):
        if m.group(1) not in rmap: continue
        t = html.unescape(''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', m.group(2), re.S)))
        if t.strip(): out.append((t, rmap[m.group(1)]))
    return out

HEAD = '''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(title)s &mdash; page %(n)d</title>
<link rel="stylesheet" href="../../assets/fonts.css">
<style>
html,body{margin:0;padding:0;background:#fff}
.sheet{width:calc(%(wmm).2fmm * var(--k,1));height:calc(%(hmm).2fmm * var(--k,1));overflow:hidden;position:relative}
.scaler{transform:scale(calc(%(scaler).5f * var(--k,1)));transform-origin:top left}
.page{position:relative;width:%(pw)dpx;height:%(ph)dpx}
.page img.bg{position:absolute;left:0;top:0;width:%(pw)dpx;height:%(ph)dpx}
p{margin:0;position:absolute}
a{color:inherit}
a:hover{text-decoration:underline}
a.pic{position:absolute;display:block;z-index:4;cursor:zoom-in}
.folio span{position:absolute;font:12px/1 'Liberation Serif','Times New Roman',serif;font-variant:small-caps;letter-spacing:.14em;color:%(fcol)s;white-space:nowrap}
.folio .fr{letter-spacing:0;font-variant:normal}
/* Comment, centred at the foot: the button holds the middle; LiveJournal slides out to its left,
   Dreamwidth to its right, from behind it */
.cmt{position:absolute;left:50%%;width:360px;margin-left:-180px;z-index:6;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;column-gap:8px;font:600 12px/1 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.cmt button{position:relative;z-index:2;background:rgba(17,17,17,.86);color:#f2ead6;border:none;border-radius:14px;padding:6px 13px 6px 10px;cursor:pointer;font:inherit;letter-spacing:.03em;box-shadow:0 3px 10px rgba(0,0,0,.28);display:inline-flex;align-items:center;gap:6px}
.cmt button:hover{background:%(fcol)s;color:#111}
.cmt .ic{font-size:13px}
.cmt .o{display:inline-flex;align-items:center;gap:6px;background:#fff;color:#1a1a1a;border:1px solid %(fcol)s;border-radius:14px;padding:5px 12px 5px 7px;text-decoration:none;box-shadow:0 3px 10px rgba(0,0,0,.22);white-space:nowrap;
  opacity:0;pointer-events:none;transition:transform .28s cubic-bezier(.2,.8,.3,1.1),opacity .2s}
.cmt .o.l{justify-self:end;transform:translateX(70px)}
.cmt .o.r{justify-self:start;transform:translateX(-70px)}
.cmt.open .o{opacity:1;pointer-events:auto;transform:none}
.cmt .o:hover{background:%(fcol)s;text-decoration:none}
.cmt .o img{width:16px;height:16px;display:block}
</style></head><body><div class="sheet"><div class="scaler"><div class="page">
'''

TAIL = '''<script>
/* The reader tells this page how big to draw itself, so text is re-rendered at the new size
   instead of being stretched as a bitmap (which is what happens when an iframe is transform-scaled). */
(function(){
  function setK(k){ document.documentElement.style.setProperty('--k', String(k)); }
  window.addEventListener('message',function(e){ var m=e.data; if(m&&m.abj==='zoom'&&isFinite(m.k)&&m.k>0) setK(m.k); });
})();
</script>
<script>
/* Pictures: tell the reader when the pointer is over one (it grows it there); on its own, open the file. */
(function(){
  var inParent=(window.parent&&window.parent!==window);
  document.querySelectorAll('a.pic').forEach(function(a,i){
    var src=new URL(a.getAttribute('data-src'),location.href).href;
    a.href=src; a.target='_blank'; a.rel='noopener';
    function rect(){ var r=a.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height}; }
    a.addEventListener('mouseenter',function(){ if(!inParent) return;
      try{ parent.postMessage({abj:'pic',id:location.pathname+'#'+i,src:src,r:rect(),nw:+a.getAttribute('data-nw'),nh:+a.getAttribute('data-nh')},'*'); }catch(e){} });
    a.addEventListener('mouseleave',function(){ if(!inParent) return; try{ parent.postMessage({abj:'picleave',id:location.pathname+'#'+i},'*'); }catch(e){} });
    a.addEventListener('click',function(e){ if(inParent){ e.preventDefault(); try{ parent.postMessage({abj:'picclick',id:location.pathname+'#'+i,src:src,r:rect(),nw:+a.getAttribute('data-nw'),nh:+a.getAttribute('data-nh')},'*'); }catch(err){} } });
  });
})();
</script>
<script>
/* Fit each line to the width it occupied in the PDF: stretch the spaces on
   justified lines, and tighten any line the substitute font renders too wide
   (which would otherwise run into the next column). Backs off rather than
   crushing the spacing when a line is too far off to fix. */
(function(){
  function fit(){
    var ps=document.querySelectorAll('p[data-w]');
    for(var i=0;i<ps.length;i++){
      var p=ps[i];
      p.style.wordSpacing=''; p.style.letterSpacing='';
      var target=parseFloat(p.getAttribute('data-w')), nat=p.offsetWidth;
      if(!target||!nat) continue;
      var d=target-nat, stretch=p.hasAttribute('data-j');
      if(Math.abs(d)<0.5) continue;
      if(d>0&&!stretch) continue;
      if(!stretch && Math.abs(d)>target*0.18){ continue; }
      var txt=(p.textContent||'').replace(/\s+$/,''), sp=(txt.match(/ /g)||[]).length;   /* a trailing space does not render */
      var fs=parseFloat(getComputedStyle(p).fontSize)||12;
      if(sp>0){
        /* a justified line gets exactly the width it had on the page - Word's gaps are even, so one
           word-spacing per line reproduces them, however wide (beside a picture a two-word line can
           carry a gap of several ems); other lines are only ever tightened */
        var ws=d/sp, cap=stretch?fs*8:fs*0.6, floor=-fs*0.06;
        if(ws>cap)ws=cap; if(ws<floor)ws=floor;
        p.style.wordSpacing=ws.toFixed(3)+'px';
        d=target-p.offsetWidth;
      }
      if(d<-0.5){
        var n=Math.max(1,txt.length-1), ls=d/n, lf=-fs*0.02;
        if(ls<lf)ls=lf;
        p.style.letterSpacing=ls.toFixed(3)+'px';
      }
    }
  }
  fit();
  if(document.fonts&&document.fonts.ready) document.fonts.ready.then(fit);
  window.addEventListener('resize',fit);
})();
</script>
<style>html.bee-on,html.bee-on *{cursor:none !important}</style>
<script>
/* Report the pointer to the parent reader so its bee can follow across the page,
   and hide this document's own cursor only once the parent confirms the bee is on. */
(function(){
  if(window.parent===window) return;
  /* a click on the page itself (not on one of its links) is the parent's business - in the stack it opens
     the card. A drag is a text selection, not a click. This runs on touch devices too. */
  var cx0=0, cy0=0;
  document.addEventListener('mousedown',function(e){ cx0=e.clientX; cy0=e.clientY; });
  document.addEventListener('click',function(e){
    if(e.target&&e.target.closest&&e.target.closest('a[href]')) return;
    if(Math.abs(e.clientX-cx0)>6||Math.abs(e.clientY-cy0)>6) return;
    try{ parent.postMessage({abj:'click'},'*'); }catch(err){}
  });
  if(!matchMedia('(hover:hover)').matches) return;
  if(matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  window.addEventListener('message',function(e){
    var m=e.data; if(m&&m.abj==='bee') document.documentElement.classList.toggle('bee-on',!!m.on);
  });
  try{ parent.postMessage({abj:'hello'},'*'); }catch(e){}
  var raf=0,px=0,py=0;
  var plink=false;
  document.addEventListener('mousemove',function(e){
    px=e.clientX; py=e.clientY;
    plink=!!(e.target&&e.target.closest&&e.target.closest('a[href]'));
    if(!raf) raf=requestAnimationFrame(function(){ raf=0;
      try{ parent.postMessage({abj:'pointer',x:px,y:py,link:plink},'*'); }catch(err){} });
  },{passive:true});
  document.addEventListener('mouseleave',function(){
    try{ parent.postMessage({abj:'pointerleave'},'*'); }catch(err){} });
})();
</script>
</body></html>
'''

def build_entry(pdf_path, outdir, title, manual=(), docx=None):
    global PICPOS, MARGIN, DOCLINKS, LINKI, FOUND
    DOCLINKS = docx_links(docx) if docx and os.path.exists(docx) else []; LINKI = 0; FOUND = []
    PAGE_TEXT.clear()
    os.makedirs(outdir, exist_ok=True)
    doc = fitz.open(pdf_path)
    learn_fonts(doc)
    for n_, pg in enumerate(doc, start=1): PAGE_TEXT[n_] = _norm(clean(pg.get_text()))   # for the link cursor's look-ahead
    # the folio sits on the text margin: the commonest left edge of a long line
    import collections as _c
    lefts = _c.Counter()
    for pg in doc:
        for b in pg.get_text('dict')['blocks']:
            if b['type'] != 0: continue
            for l in b['lines']:
                if sum(len(s_['text'].strip()) for s_ in l['spans']) >= 30: lefts[round(l['bbox'][0])] += 1
    if lefts: MARGIN = float(min(x for x, n in lefts.items() if n >= max(3, lefts.most_common(1)[0][1] * 0.15)))
    print('   fonts:', ', '.join('%s=%s%s%s' % (k, v[0], ' bold' if v[1] else '', ' italic' if v[2] else '') for k, v in FONTMAP.items()) or 'named', '| text margin %.1f pt' % MARGIN)
    alltext, links = [], []
    PICPOS = []
    for n, pno in enumerate(range(doc.page_count), start=1):
        alltext.append(build_page(doc, pno, outdir, n, title, links, manual, False))
    W, H = doc[0].rect.width, doc[0].rect.height
    if DOCLINKS:
        print('   hyperlinks: %d of %d from the Word file placed' % (len(FOUND), len(DOCLINKS)))
        for t, u in DOCLINKS[LINKI:]: print('      not found in the page text:', repr(t[:60]))
    json.dump({'pages': alltext, 'links': sorted(set(links)), 'pt': [W, H], 'pics': PICPOS, 'doclinks': FOUND},
              open(os.path.join(outdir, 'text.json'), 'w'), ensure_ascii=False, indent=0)
    doc.close()
    return doc_count(pdf_path), (W * PT_MM, H * PT_MM)
def doc_count(p): d = fitz.open(p); n = d.page_count; d.close(); return n

if __name__ == '__main__':
    site = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = json.load(open(os.path.join(site, '_config.json')))
    meta = json.load(open(os.path.join(site, '_entries_meta.json')))
    only = sys.argv[1:]
    for a in meta:
        if only and a['id'] not in only: continue
        pdf = os.path.join(site, '_pdf', a['id'] + '.pdf')
        if not os.path.exists(pdf): print(a['id'], ': no PDF yet - run prep.py first'); continue
        pj = os.path.join(site, '_pics', a['id'] + '.json')
        PICS = json.load(open(pj)) if os.path.exists(pj) else []
        FOLIO_SLUG = '%s · Vol. %s · Topic %s' % (cfg.get('folio_prefix', 'LJI'), a['vol'], a['topic'])
        FOLIO_COLOR = cfg.get('frame_color', '#228B22')
        COMMENT = {'lj': a.get('lj'), 'dw': a.get('dw')}
        out = os.path.join(site, 'pages', a['id'])
        n, mm = build_entry(pdf, out, a['title'], a.get('links', ()), os.path.join(site, '_src', a['src']))
        a['n'] = n; a['mm'] = [round(mm[0], 2), round(mm[1], 2)]
        tj = json.load(open(os.path.join(out, 'text.json'))); a['pmm'] = [pg['mm'] for pg in tj['pages']]
        print('%-10s %2d pages  %.0fx%.0f mm  %s' % (a['id'], n, mm[0], mm[1], a['title'][:50]))
    json.dump(meta, open(os.path.join(site, '_entries_meta.json'), 'w'), indent=1, ensure_ascii=False)
