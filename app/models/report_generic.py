#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rapports Word et LaTeX générés à partir des résultats standardisés de models.runners."""

import base64
import io
from datetime import datetime

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

NAVY = RGBColor(0x0B, 0x2A, 0x4A)


def _heading(doc, text, level):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = NAVY
    return h


def _table(doc, columns, rows):
    t = doc.add_table(rows=1, cols=len(columns))
    t.style = 'Light Grid Accent 1'
    for i, c in enumerate(columns):
        cell = t.rows[0].cells[i]
        cell.text = str(c)
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.size = Pt(9)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v)
            for p in cells[i].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    doc.add_paragraph()


def _picture(doc, b64, caption=None, width=15.5):
    try:
        doc.add_picture(io.BytesIO(base64.b64decode(b64)), width=Cm(width))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        if caption:
            c = doc.add_paragraph(caption)
            c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in c.runs:
                r.italic = True
                r.font.size = Pt(8.5)
    except Exception:
        pass


def _section_block(doc, sec, num):
    _heading(doc, f"{num}. {sec['title']}", 1)
    for t in sec.get('text', []):
        doc.add_paragraph(t)
    for t in sec.get('tables', []):
        _heading(doc, t['title'], 3)
        _table(doc, t['columns'], t['rows'])
    for c in sec.get('charts', []):
        _picture(doc, c['img'], c['title'])


def _robustness_block(doc, rb):
    _heading(doc, 'Tests de robustesse' + (f" - verdict : {rb['verdict']}" if rb.get('verdict') else ''), 3)
    if rb.get('status') != 'ok':
        doc.add_paragraph(rb.get('error', 'Non disponible.'))
        return
    for t in rb.get('text', []):
        doc.add_paragraph(t)
    if rb.get('checks'):
        _table(doc, ['Test', 'Résultat', 'Détail'], [[c['label'], 'Satisfait' if c['ok'] else 'À surveiller', c['detail']] for c in rb['checks']])
    for t in rb.get('tables', []):
        _heading(doc, t['title'], 4)
        _table(doc, t['columns'], t['rows'])
    for c in rb.get('charts', []):
        _picture(doc, c['img'], c['title'])


def create_report(dataset_name, target, features, ctx, recs, results, time_col=None, entity_col=None, data_report=None):
    if data_report:
        from models.report_word import build_word
        return build_word(dataset_name, target, features, ctx, recs, results, time_col, entity_col, data_report)
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2)
    title = doc.add_heading('Rapport d\'analyse économétrique', 0)
    for run in title.runs:
        run.font.color.rgb = NAVY
    p = doc.add_paragraph()
    p.add_run(f"Jeu de données : {dataset_name}\n").bold = True
    p.add_run(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} avec DataEcon.Ci")

    _heading(doc, '1. Données et problème', 1)
    doc.add_paragraph(f"Variable cible : {target}")
    if features:
        doc.add_paragraph("Variables explicatives : " + ', '.join(features))
    if time_col:
        doc.add_paragraph(f"Colonne de temps : {time_col}")
    if entity_col:
        doc.add_paragraph(f"Colonne d'entité : {entity_col}")
    _heading(doc, '2. Diagnostic des données', 2)
    _table(doc, ['Diagnostic', 'Résultat'], [[d['label'], d['value']] for d in ctx.get('diagnostics', [])])

    _heading(doc, '3. Modèles recommandés', 1)
    _table(doc, ['Modèle', 'Famille', 'Score', 'Niveau'],
           [[r['name'], r['family_label'], r['score'], r['level']] for r in recs if r['available']][:15])

    _heading(doc, '4. Comparaison des modèles estimés', 1)
    ok = [r for r in results if r['status'] == 'ok']
    keys = []
    for r in ok:
        for m in r['metrics']:
            if m['key'] in ('R2', 'RMSE', 'MAE', 'Accuracy', 'AUC', 'F1', 'AIC', 'BIC') and m['key'] not in keys:
                keys.append(m['key'])
    labels = {'R2': 'R²', 'RMSE': 'RMSE', 'MAE': 'MAE', 'Accuracy': 'Exactitude', 'AUC': 'AUC', 'F1': 'F1', 'AIC': 'AIC', 'BIC': 'BIC'}
    rows = []
    for r in ok:
        mm = {m['key']: m['value'] for m in r['metrics']}
        rows.append([r['name']] + [mm.get(k, '—') for k in keys])
    if rows:
        _table(doc, ['Modèle'] + [labels[k] for k in keys], rows)

    for i, r in enumerate(results, 1):
        _heading(doc, f"5.{i} {r['name']}", 1)
        if r['status'] != 'ok':
            doc.add_paragraph(r.get('error', 'Erreur'))
            continue
        _table(doc, ['Indicateur', 'Valeur'], [[m['label'], m['value']] for m in r['metrics']])
        for t in r['tables']:
            _heading(doc, t['title'], 3)
            _table(doc, t['columns'], t['rows'])
        for c in r['charts']:
            try:
                doc.add_picture(io.BytesIO(base64.b64decode(c['img'])), width=Cm(15.5))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            except Exception:
                pass
        if r['interpretation']:
            _heading(doc, 'Interprétation', 3)
            for t in r['interpretation']:
                doc.add_paragraph(t, style='List Bullet')
        if r['warnings']:
            _heading(doc, 'Points d\'attention', 3)
            for t in r['warnings']:
                doc.add_paragraph(t, style='List Bullet')
    doc.add_paragraph()
    note = doc.add_paragraph("Ces résultats sont fournis à titre d'aide à l'analyse. Ils dépendent de la qualité des données et des hypothèses de chaque modèle.")
    note.runs[0].italic = True
    return doc


def _create_detailed_report(dataset_name, target, features, ctx, recs, results, time_col, entity_col, dr):
    doc = Document()
    for sct in doc.sections:
        sct.left_margin = sct.right_margin = Cm(2)
    title = doc.add_heading(dr.get('title') or "Rapport d'analyse", 0)
    for run in title.runs:
        run.font.color.rgb = NAVY
    p = doc.add_paragraph()
    p.add_run(f"Jeu de données : {dataset_name}\n").bold = True
    p.add_run(f"Variable étudiée : {target}\n")
    p.add_run(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} avec DataEcon.Ci")
    n = 0
    for sec in dr['sections']:
        n += 1
        _section_block(doc, sec, n)
        if sec['id'] == 'preliminaires':
            # diagnostic de structure et recommandations juste après les tests préliminaires
            _heading(doc, 'Diagnostic automatique de la structure des données', 3)
            _table(doc, ['Diagnostic', 'Résultat'], [[d['label'], d['value']] for d in ctx.get('diagnostics', [])])
    n += 1
    _heading(doc, f"{n}. Choix des modèles", 1)
    doc.add_paragraph("Les modèles ont été sélectionnés en fonction de la nature de la variable cible, de la structure des données et des tests préliminaires.")
    _table(doc, ['Modèle', 'Famille', 'Score', 'Niveau'],
           [[r['name'], r['family_label'], r['score'], r['level']] for r in recs if r['available'] and r['id'] in {x['id'] for x in results}])
    n += 1
    _heading(doc, f"{n}. Résultats des modèles", 1)
    ok = [r for r in results if r['status'] == 'ok']
    keys = []
    for r in ok:
        for m in r['metrics']:
            if m['key'] in ('R2', 'RMSE', 'MAE', 'Accuracy', 'AUC', 'F1', 'AIC', 'BIC') and m['key'] not in keys:
                keys.append(m['key'])
    labels = {'R2': 'R²', 'RMSE': 'RMSE', 'MAE': 'MAE', 'Accuracy': 'Exactitude', 'AUC': 'AUC', 'F1': 'F1', 'AIC': 'AIC', 'BIC': 'BIC'}
    rows = []
    for r in ok:
        mm = {m['key']: m['value'] for m in r['metrics']}
        rows.append([r['name']] + [mm.get(k, '—') for k in keys])
    if rows:
        _heading(doc, 'Comparaison', 2)
        _table(doc, ['Modèle'] + [labels[k] for k in keys], rows)
    for i, r in enumerate(results, 1):
        _heading(doc, f"{n}.{i} {r['name']}", 2)
        if r['status'] != 'ok':
            doc.add_paragraph(r.get('error', 'Erreur'))
            continue
        _table(doc, ['Indicateur', 'Valeur'], [[m['label'], m['value']] for m in r['metrics']])
        for t in r['tables']:
            _heading(doc, t['title'], 3)
            _table(doc, t['columns'], t['rows'])
        for c in r['charts']:
            _picture(doc, c['img'], c['title'])
        if r['interpretation']:
            _heading(doc, 'Interprétation', 3)
            for t in r['interpretation']:
                doc.add_paragraph(t, style='List Bullet')
        if r['warnings']:
            _heading(doc, "Points d'attention", 3)
            for t in r['warnings']:
                doc.add_paragraph(t, style='List Bullet')
        if r.get('robustness'):
            _robustness_block(doc, r['robustness'])
    n += 1
    _section_block(doc, dr['conclusion'], n)
    doc.add_paragraph()
    note = doc.add_paragraph("Ce rapport est fourni à titre d'aide à l'analyse. Les résultats dépendent de la qualité des données et des hypothèses de chaque modèle.")
    note.runs[0].italic = True
    return doc


_LATEX = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}


def tex(s):
    return ''.join(_LATEX.get(c, c) for c in str(s)).replace('²', '$^2$').replace('→', r'$\rightarrow$').replace('≥', r'$\geq$').replace('≤', r'$\leq$')


def _tex_table(columns, rows):
    col = 'l' + 'r' * (len(columns) - 1)
    out = [r'\begin{center}\small', r'\begin{tabular}{' + col + '}', r'\toprule',
           ' & '.join(tex(c) for c in columns) + r' \\', r'\midrule']
    for r in rows:
        out.append(' & '.join(tex(c) for c in r) + r' \\')
    out += [r'\bottomrule', r'\end{tabular}', r'\end{center}']
    return '\n'.join(out)


def create_latex(dataset_name, target, features, ctx, recs, results, time_col=None, entity_col=None, data_report=None):
    L = [r'\documentclass[11pt,a4paper]{article}', r'\usepackage[utf8]{inputenc}', r'\usepackage[T1]{fontenc}',
         r'\usepackage[french]{babel}', r'\usepackage{booktabs,geometry,graphicx}', r'\geometry{margin=2.2cm}',
         r"\title{Rapport d'analyse économétrique}", r'\author{DataEcon.Ci}', r'\date{' + datetime.now().strftime('%d/%m/%Y') + '}',
         r'\begin{document}', r'\maketitle',
         r'\section{Données et problème}',
         f"Jeu de données : {tex(dataset_name)}.\\\\", f"Variable cible : {tex(target)}.\\\\"]
    if features:
        L.append('Variables explicatives : ' + tex(', '.join(features)) + r'.\\')
    if time_col:
        L.append(f'Colonne de temps : {tex(time_col)}.\\\\')
    if entity_col:
        L.append(f"Colonne d'entité : {tex(entity_col)}.\\\\")
    if data_report:
        for sec in data_report['sections']:
            L.append(r'\section{' + tex(sec['title']) + '}')
            for t in sec['text']:
                L.append(tex(t) + '\n')
            for t in sec['tables']:
                if len(t['columns']) > 8:
                    continue
                L.append(r'\paragraph{' + tex(t['title']) + '}')
                L.append(_tex_table(t['columns'], t['rows']))
            if sec['charts']:
                L.append('\\emph{Figures : ' + tex(' ; '.join(c['title'] for c in sec['charts'])) + ' (voir le rapport Word).}\n')
    L.append(r'\subsection*{Diagnostic}')
    L.append(_tex_table(['Diagnostic', 'Résultat'], [[d['label'], d['value']] for d in ctx.get('diagnostics', [])]).replace('{lr}', '{p{5cm}p{9cm}}'))
    L.append(r'\section{Modèles estimés}')
    for i, r in enumerate(results, 1):
        L.append(r'\subsection{' + tex(r['name']) + '}')
        if r['status'] != 'ok':
            L.append(tex(r.get('error', 'Erreur')))
            continue
        L.append(_tex_table(['Indicateur', 'Valeur'], [[m['label'], m['value']] for m in r['metrics']]))
        for t in r['tables']:
            if len(t['rows']) > 40:
                continue
            L.append(r'\paragraph{' + tex(t['title']) + '}')
            L.append(_tex_table(t['columns'], t['rows']))
        rb = r.get('robustness')
        if rb and rb.get('status') == 'ok':
            L.append(r'\paragraph{Tests de robustesse' + (' : ' + tex(rb['verdict']) if rb.get('verdict') else '') + '}')
            L.append(_tex_table(['Test', 'Résultat', 'Détail'], [[c['label'], 'Satisfait' if c['ok'] else 'À surveiller', c['detail']] for c in rb['checks']]).replace('{lrr}', '{p{8cm}p{2.5cm}p{4cm}}'))
            for t in rb['tables']:
                if len(t['rows']) <= 25 and len(t['columns']) <= 8:
                    L.append(r'\paragraph{' + tex(t['title']) + '}')
                    L.append(_tex_table(t['columns'], t['rows']))
        if r['interpretation']:
            L.append(r'\paragraph{Interprétation}\begin{itemize}')
            L += [r'\item ' + tex(t) for t in r['interpretation']]
            L.append(r'\end{itemize}')
    if data_report and data_report.get('conclusion'):
        c = data_report['conclusion']
        L.append(r'\section{' + tex(c['title']) + '}')
        for t in c['text']:
            L.append(tex(t) + '\n')
    L.append(r'\end{document}')
    return '\n'.join(L)
