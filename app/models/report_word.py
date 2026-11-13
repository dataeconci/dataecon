# -*- coding: utf-8 -*-
"""
Rapport Word académique : Times New Roman 12, texte noir, page de garde, sommaire,
sections numérotées, tableaux et figures numérotés et légendés, pagination.
"""
import base64
import io
from datetime import datetime

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = 'Times New Roman'
SIZE = Pt(12)
BLACK = RGBColor(0, 0, 0)


# ---------------------------------------------------------------- utilitaires XML
def _set_run_font(run, bold=None, italic=None, size=SIZE):
    run.font.name = FONT
    run.font.size = size
    run.font.color.rgb = BLACK
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts')
        rpr.append(rf)
    for a in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
        rf.set(qn(a), FONT)


def _style_font(style, bold=None, italic=None, caps=None):
    style.font.name = FONT
    style.font.size = SIZE
    style.font.color.rgb = BLACK
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    if caps is not None:
        style.font.all_caps = caps
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts')
        rpr.append(rf)
    for a in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
        rf.set(qn(a), FONT)
    for a in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]


def _shade(cell, fill='F2F2F2'):
    tcpr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill)
    tcpr.append(shd)


def _field(paragraph, instr, result_text=''):
    """Insère un champ Word (PAGE, TOC...) avec un résultat pré-rempli."""
    def mk(t):
        r = paragraph.add_run()
        _set_run_font(r)
        fc = OxmlElement('w:fldChar')
        fc.set(qn('w:fldCharType'), t)
        r._element.append(fc)
        return r
    mk('begin')
    r = paragraph.add_run()
    _set_run_font(r)
    it = OxmlElement('w:instrText')
    it.set(qn('xml:space'), 'preserve')
    it.text = f' {instr} '
    r._element.append(it)
    mk('separate')
    rr = paragraph.add_run(result_text)
    _set_run_font(rr)
    mk('end')


def _para_fmt(p, align=WD_ALIGN_PARAGRAPH.JUSTIFY, spacing=1.5, before=0, after=6, keep_next=False, indent_first=False):
    pf = p.paragraph_format
    p.alignment = align
    pf.line_spacing = spacing
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.keep_with_next = keep_next
    if indent_first:
        pf.first_line_indent = Cm(1)


def _borders(table):
    tblPr = table._element.tblPr
    b = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        e = OxmlElement(f'w:{edge}')
        e.set(qn('w:val'), 'single')
        e.set(qn('w:sz'), '4')
        e.set(qn('w:space'), '0')
        e.set(qn('w:color'), '000000')
        b.append(e)
    tblPr.append(b)


def _repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    h = OxmlElement('w:tblHeader')
    h.set(qn('w:val'), 'true')
    trPr.append(h)


def _no_split(row):
    trPr = row._tr.get_or_add_trPr()
    c = OxmlElement('w:cantSplit')
    c.set(qn('w:val'), 'true')
    trPr.append(c)


# ---------------------------------------------------------------- constructeur
class Rapport:
    def __init__(self, titre, auteur='DataEcon.Ci'):
        self.doc = Document()
        self.titre = titre
        self.auteur = auteur
        self.n_tab = 0
        self.n_fig = 0
        self.toc = []                    # (niveau, texte) pour le sommaire
        self._setup()

    def _setup(self):
        d = self.doc
        sec = d.sections[0]
        sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
        sec.left_margin = sec.right_margin = Cm(2.5)
        sec.top_margin = sec.bottom_margin = Cm(2.5)
        st = d.styles
        _style_font(st['Normal'])
        for name in ('Heading 1', 'Heading 2', 'Heading 3', 'Heading 4', 'Title', 'List Bullet', 'Caption', 'Table Grid'):
            try:
                _style_font(st[name])
            except KeyError:
                pass
        _style_font(st['Heading 1'], bold=True, italic=False, caps=True)
        _style_font(st['Heading 2'], bold=True, italic=False)
        _style_font(st['Heading 3'], bold=True, italic=True)
        _style_font(st['Heading 4'], bold=False, italic=True)
        _style_font(st['Title'], bold=True)
        # pied de page : numéro de page centré
        fp = sec.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _field(fp, 'PAGE', '1')
        sec.different_first_page_header_footer = True      # pas de numéro sur la page de garde

    # ----- texte
    def titre_n(self, texte, niveau=1):
        h = self.doc.add_heading('', level=niveau)
        r = h.add_run(texte.upper() if niveau == 1 else texte)
        _set_run_font(r, bold=(niveau <= 3), italic=(niveau >= 3))
        r.font.all_caps = False
        _para_fmt(h, align=WD_ALIGN_PARAGRAPH.LEFT, spacing=1.15, before=18 if niveau == 1 else 12, after=6, keep_next=True)
        self.toc.append((niveau, texte.upper() if niveau == 1 else texte))
        return h

    def para(self, texte, italic=False, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True):
        p = self.doc.add_paragraph()
        r = p.add_run(str(texte))
        _set_run_font(r, bold=bold, italic=italic)
        _para_fmt(p, align=align, indent_first=indent and align == WD_ALIGN_PARAGRAPH.JUSTIFY)
        return p

    def puces(self, items):
        for t in items:
            p = self.doc.add_paragraph(style='List Bullet')
            r = p.add_run(str(t))
            _set_run_font(r)
            _para_fmt(p, spacing=1.15, after=3)

    def saut_page(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ----- tableaux et figures
    def tableau(self, colonnes, lignes, legende=None):
        self.n_tab += 1
        if legende:
            p = self.doc.add_paragraph()
            r = p.add_run(f"Tableau {self.n_tab} : ")
            _set_run_font(r, bold=True)
            r2 = p.add_run(str(legende))
            _set_run_font(r2)
            _para_fmt(p, align=WD_ALIGN_PARAGRAPH.LEFT, spacing=1.0, before=6, after=3, keep_next=True)
        ncol = len(colonnes)
        taille = SIZE if ncol <= 6 else (Pt(10) if ncol <= 8 else Pt(9))   # tableaux très larges : police réduite pour tenir dans la page
        t = self.doc.add_table(rows=1, cols=ncol)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        _borders(t)
        for i, c in enumerate(colonnes):
            cell = t.rows[0].cells[i]
            cell.text = ''
            p = cell.paragraphs[0]
            r = p.add_run(str(c))
            _set_run_font(r, bold=True, size=taille)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(2)
            _shade(cell)
        _repeat_header(t.rows[0])
        for row in lignes:
            cells = t.add_row().cells
            _no_split(t.rows[-1])
            for i, v in enumerate(row):
                cells[i].text = ''
                p = cells[i].paragraphs[0]
                r = p.add_run(str(v))
                _set_run_font(r, size=taille)
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.0
        if ncol > 6:
            t.autofit = False
            first = 2.9
            rest = (16.0 - first) / (ncol - 1)
            lay = OxmlElement('w:tblLayout')
            lay.set(qn('w:type'), 'fixed')
            t._element.tblPr.append(lay)
            for i, col in enumerate(t.columns):
                col.width = Cm(first if i == 0 else rest)
            for row in t.rows:
                for i, c in enumerate(row.cells):
                    c.width = Cm(first if i == 0 else rest)
        sp = self.doc.add_paragraph()
        sp.paragraph_format.space_after = Pt(6)

    def figure(self, b64, legende=None, largeur=15.0):
        try:
            self.doc.add_picture(io.BytesIO(base64.b64decode(b64)), width=Cm(largeur))
        except Exception:
            return
        pic = self.doc.paragraphs[-1]
        pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pic.paragraph_format.keep_with_next = True
        pic.paragraph_format.space_before = Pt(6)
        self.n_fig += 1
        p = self.doc.add_paragraph()
        r = p.add_run(f"Figure {self.n_fig} : ")
        _set_run_font(r, bold=True)
        r2 = p.add_run(str(legende or ''))
        _set_run_font(r2)
        _para_fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.0, before=2, after=10)

    # ----- page de garde et sommaire
    def page_garde(self, sous_titre, infos):
        d = self.doc
        for _ in range(5):
            d.add_paragraph()
        p = d.add_paragraph()
        _set_run_font(p.add_run("RAPPORT D'ANALYSE STATISTIQUE ET ÉCONOMÉTRIQUE"), bold=True)
        _para_fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.5, after=24)
        self._trait()
        p = d.add_paragraph()
        _set_run_font(p.add_run(self.titre), bold=True)
        _para_fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.5, before=18, after=6)
        if sous_titre:
            p = d.add_paragraph()
            _set_run_font(p.add_run(sous_titre), italic=True)
            _para_fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.5, after=6)
        self._trait()
        for _ in range(4):
            d.add_paragraph()
        for lib, val in infos:
            p = d.add_paragraph()
            _set_run_font(p.add_run(f"{lib} : "), bold=True)
            _set_run_font(p.add_run(str(val)))
            _para_fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.5, after=2)
        for _ in range(6):
            d.add_paragraph()
        p = d.add_paragraph()
        _set_run_font(p.add_run(f"Réalisé avec {self.auteur}"), italic=True)
        _para_fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.0, after=2)
        p = d.add_paragraph()
        _set_run_font(p.add_run(datetime.now().strftime('%d/%m/%Y')))
        _para_fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.0)
        self.saut_page()

    def _trait(self):
        p = self.doc.add_paragraph()
        pPr = p._p.get_or_add_pPr()
        b = OxmlElement('w:pBdr')
        e = OxmlElement('w:bottom')
        e.set(qn('w:val'), 'single')
        e.set(qn('w:sz'), '8')
        e.set(qn('w:space'), '1')
        e.set(qn('w:color'), '000000')
        b.append(e)
        pPr.append(b)

    def reserver_sommaire(self):
        """Repère l'emplacement du sommaire (rempli en fin de construction)."""
        p = self.doc.add_paragraph()
        _set_run_font(p.add_run('SOMMAIRE'), bold=True)
        _para_fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.15, after=12)
        self._toc_anchor = self.doc.add_paragraph()
        self.saut_page()

    def remplir_sommaire(self):
        anchor = self._toc_anchor
        # champ TOC (mise à jour possible dans Word) avec entrées pré-remplies
        first = True
        prev = anchor
        entries = [(n, t) for n, t in self.toc if n <= 2]
        for idx, (niv, texte) in enumerate(entries):
            p = prev if idx == 0 else self._insert_after(prev)
            if idx == 0:
                self._fld_begin(p)
            r = p.add_run(texte)
            _set_run_font(r, bold=(niv == 1))
            p.paragraph_format.left_indent = Cm(0.8 * (niv - 1))
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.15
            if idx == len(entries) - 1:
                self._fld_end(p)
            prev = p

    def _insert_after(self, para):
        new = OxmlElement('w:p')
        para._p.addnext(new)
        from docx.text.paragraph import Paragraph
        return Paragraph(new, para._parent)

    def _fld_begin(self, p):
        for t, txt in (('begin', None), ('instr', ' TOC \\o "1-2" \\h \\z \\u '), ('separate', None)):
            r = p.add_run()
            _set_run_font(r)
            if t == 'instr':
                it = OxmlElement('w:instrText')
                it.set(qn('xml:space'), 'preserve')
                it.text = txt
                r._element.append(it)
            else:
                fc = OxmlElement('w:fldChar')
                fc.set(qn('w:fldCharType'), t)
                r._element.append(fc)

    def _fld_end(self, p):
        r = p.add_run()
        _set_run_font(r)
        fc = OxmlElement('w:fldChar')
        fc.set(qn('w:fldCharType'), 'end')
        r._element.append(fc)


# ---------------------------------------------------------------- rapport complet
_LABELS = {'R2': 'R²', 'RMSE': 'RMSE', 'MAE': 'MAE', 'Accuracy': 'Exactitude', 'AUC': 'AUC', 'F1': 'F1', 'AIC': 'AIC', 'BIC': 'BIC'}


def _bloc_section(R, sec, num):
    R.titre_n(f"{num}. {sec['title']}", 1)
    for t in sec.get('text', []):
        R.para(t)
    k = 0
    for t in sec.get('tables', []):
        k += 1
        R.tableau(t['columns'], t['rows'], t['title'])
    for c in sec.get('charts', []):
        R.figure(c['img'], c['title'])


def _bloc_robustesse(R, rb, prefix):
    R.titre_n(f"{prefix} Tests de robustesse" + (f" (verdict : {rb['verdict']})" if rb.get('verdict') else ''), 3)
    if rb.get('status') != 'ok':
        R.para(rb.get('error', 'Non disponible.'))
        return
    for t in rb.get('text', []):
        R.para(t)
    if rb.get('checks'):
        R.tableau(['Test', 'Résultat', 'Détail'], [[c['label'], 'Satisfait' if c['ok'] else 'À surveiller', c['detail']] for c in rb['checks']],
                  'Synthèse des tests de robustesse')
    for t in rb.get('tables', []):
        R.tableau(t['columns'], t['rows'], t['title'])
    for c in rb.get('charts', []):
        R.figure(c['img'], c['title'])


def build_word(dataset_name, target, features, ctx, recs, results, time_col, entity_col, dr):
    titre = dr.get('title') or f"Analyse de {target}"
    R = Rapport(titre)
    structure = {'cross_section': 'Données en coupe transversale', 'time_series': 'Série temporelle', 'panel': 'Données de panel'}.get(ctx.get('structure'), '')
    infos = [('Jeu de données', dataset_name), ('Variable étudiée', target)]
    if features:
        infos.append(('Variables explicatives', ', '.join(features) if len(features) <= 6 else f"{len(features)} variables"))
    if structure:
        infos.append(('Structure des données', structure))
    R.page_garde(None, infos)
    R.reserver_sommaire()

    n = 0
    for sec in dr['sections']:
        n += 1
        _bloc_section(R, sec, n)
        if sec['id'] == 'preliminaires':
            R.titre_n('Diagnostic automatique de la structure des données', 2)
            R.tableau(['Diagnostic', 'Résultat'], [[d['label'], d['value']] for d in ctx.get('diagnostics', [])], 'Diagnostic de la structure des données')

    n += 1
    R.titre_n(f"{n}. Méthodologie et choix des modèles", 1)
    R.para("Les modèles ont été sélectionnés en fonction de la nature de la variable cible, de la structure des données et des tests préliminaires. "
           "Chaque modèle est estimé sur les données préparées ; les modèles de prévision et d'apprentissage automatique sont évalués sur des échantillons "
           "d'apprentissage, de validation et de test distincts.")
    ids = {x['id'] for x in results}
    R.tableau(['Modèle', 'Famille', 'Score', 'Niveau'], [[r['name'], r['family_label'], r['score'], r['level']] for r in recs if r['available'] and r['id'] in ids],
              'Modèles retenus et score de pertinence')

    n += 1
    R.titre_n(f"{n}. Résultats des modèles", 1)
    ok = [r for r in results if r['status'] == 'ok']
    keys = []
    for r in ok:
        for m in r['metrics']:
            if m['key'] in _LABELS and m['key'] not in keys:
                keys.append(m['key'])
    rows = []
    for r in ok:
        mm = {m['key']: m['value'] for m in r['metrics']}
        rows.append([r['name']] + [mm.get(k, '-') for k in keys])
    if rows:
        R.titre_n(f"{n}.1 Comparaison des modèles", 2)
        R.tableau(['Modèle'] + [_LABELS[k] for k in keys], rows, 'Comparaison des indicateurs de performance')
    for i, r in enumerate(results, 1):
        base = f"{n}.{i + (1 if rows else 0)}"
        R.titre_n(f"{base} {r['name']}", 2)
        if r['status'] != 'ok':
            R.para(r.get('error', 'Erreur'))
            continue
        R.tableau(['Indicateur', 'Valeur'], [[m['label'], m['value']] for m in r['metrics']], f"Indicateurs du modèle {r['name']}")
        for t in r['tables']:
            R.tableau(t['columns'], t['rows'], t['title'])
        for c in r['charts']:
            R.figure(c['img'], c['title'])
        if r['interpretation']:
            R.titre_n(f"{base}.1 Interprétation", 3)
            R.puces(r['interpretation'])
        if r['warnings']:
            R.titre_n(f"{base}.2 Points d'attention", 3)
            R.puces(r['warnings'])
        if r.get('robustness'):
            _bloc_robustesse(R, r['robustness'], f"{base}.3")

    n += 1
    _bloc_section(R, dr['conclusion'], n)

    R.titre_n('Avertissement', 1)
    R.para("Ce rapport est produit automatiquement à titre d'aide à l'analyse. Les résultats dépendent de la qualité des données et des hypothèses "
           "propres à chaque modèle ; ils doivent être interprétés par l'utilisateur avant toute décision.", italic=True)
    R.remplir_sommaire()
    return R.doc
