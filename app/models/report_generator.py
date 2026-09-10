#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Générateur de rapports Word pour les analyses économétriques
"""

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from datetime import datetime
import os
import base64
from io import BytesIO
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

class ReportGenerator:
    """Générateur de rapports Word structurés"""
    
    def __init__(self, title="Rapport d'Analyse Économétrique"):
        self.doc = Document()
        self.title = title
        
        # Configuration des styles
        self._setup_styles()
    
    def _setup_styles(self):
        """Configurer les styles du document"""
        style = self.doc.styles['Normal']
        style.font.name = 'Arial'
        style.font.size = Pt(11)
    
    def add_title_page(self, title, subtitle, author, date=None):
        """Ajouter une page de titre"""
        if date is None:
            date = datetime.now().strftime('%d/%m/%Y')
        
        # Titre principal
        title_para = self.doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_para.add_run(title)
        run.font.size = Pt(24)
        run.font.bold = True
        run.font.color.rgb = RGBColor(26, 42, 108)
        
        # Sous-titre
        self.doc.add_paragraph()
        subtitle_para = self.doc.add_paragraph()
        subtitle_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = subtitle_para.add_run(subtitle)
        run.font.size = Pt(14)
        run.font.italic = True
        
        # Auteur
        self.doc.add_paragraph()
        author_para = self.doc.add_paragraph()
        author_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = author_para.add_run(f"Auteur : {author}")
        run.font.size = Pt(12)
        
        # Date
        date_para = self.doc.add_paragraph()
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = date_para.add_run(f"Date : {date}")
        run.font.size = Pt(12)
        
        self.doc.add_page_break()
    
    def add_section(self, title, level=1):
        """Ajouter une section"""
        if level == 1:
            heading = self.doc.add_heading(title, level=1)
            heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
        elif level == 2:
            heading = self.doc.add_heading(title, level=2)
        else:
            heading = self.doc.add_heading(title, level=3)
        
        return heading
    
    def add_paragraph(self, text, style='Normal'):
        """Ajouter un paragraphe"""
        return self.doc.add_paragraph(text, style=style)
    
    def add_table(self, data, headers=None, title=None):
        """Ajouter un tableau"""
        if title:
            self.doc.add_paragraph(title, style='Heading 3')
        
        rows = len(data)
        cols = len(data[0]) if data else 0
        
        table = self.doc.add_table(rows=rows, cols=cols)
        table.style = 'Table Grid'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        
        for i, row in enumerate(data):
            for j, cell in enumerate(row):
                table.cell(i, j).text = str(cell)
                if i == 0:  # En-tête
                    for paragraph in table.cell(i, j).paragraphs:
                        for run in paragraph.runs:
                            run.font.bold = True
        
        return table
    
    def add_figure(self, fig, title=None, caption=None):
        """Ajouter une figure matplotlib"""
        if title:
            self.doc.add_paragraph(title, style='Heading 3')
        
        # Sauvegarder l'image en mémoire
        img_buffer = BytesIO()
        fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        
        # Ajouter à Word
        self.doc.add_picture(img_buffer, width=Inches(6))
        
        if caption:
            cap = self.doc.add_paragraph(caption)
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in cap.runs:
                run.font.italic = True
                run.font.size = Pt(10)
        
        plt.close(fig)
    
    def add_interpretation(self, text, type_='economic'):
        """Ajouter une interprétation avec mise en forme"""
        colors = {
            'economic': (26, 42, 108),   # Bleu
            'financial': (0, 128, 0),     # Vert
            'strategic': (192, 0, 0),     # Rouge
            'statistical': (128, 0, 128)  # Violet
        }
        
        color = colors.get(type_, (0, 0, 0))
        
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # Ajouter l'icône
        icons = {
            'economic': ' ',
            'financial': ' ',
            'strategic': ' ',
            'statistical': ' '
        }
        
        run = p.add_run(icons.get(type_, ' '))
        run.font.bold = True
        
        run = p.add_run(text)
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(*color)
    
    def add_model_summary(self, model_name, params, metrics, interpretation):
        """Ajouter un résumé de modèle"""
        self.add_section(f" {model_name}", level=2)
        
        # Paramètres
        self.add_paragraph(" Paramètres du modèle :", style='Heading 3')
        param_text = ", ".join([f"{k}: {v}" for k, v in params.items()])
        self.add_paragraph(param_text)
        
        # Métriques
        self.add_paragraph(" Métriques d'évaluation :", style='Heading 3')
        for key, value in metrics.items():
            self.add_paragraph(f"• {key}: {value}")
        
        # Interprétation
        self.add_paragraph(" Interprétation :", style='Heading 3')
        self.add_interpretation(interpretation['economic'], 'economic')
        if 'financial' in interpretation:
            self.add_interpretation(interpretation['financial'], 'financial')
        if 'strategic' in interpretation:
            self.add_interpretation(interpretation['strategic'], 'strategic')
    
    def save(self, filename):
        """Sauvegarder le document"""
        self.doc.save(filename)
        return filename

def create_econometric_report(data, model_results, model_type, variable_names):
    """
    Créer un rapport complet pour un modèle économétrique
    
    Args:
        data: DataFrame des données
        model_results: Résultats du modèle
        model_type: Type de modèle ('regression', 'timeseries', 'ml', 'dl')
        variable_names: Noms des variables
    """
    report = ReportGenerator(f"Rapport d'Analyse {model_type}")
    
    # Page de titre
    report.add_title_page(
        title=f"Rapport d'Analyse {model_type}",
        subtitle="Analyse économétrique et machine learning",
        author="DataEcon.Ci",
        date=datetime.now().strftime('%d/%m/%Y')
    )
    
    # 1. Introduction
    report.add_section("1. Introduction", level=1)
    report.add_paragraph(f"""
    Ce rapport présente les résultats de l'analyse {model_type} réalisée sur les données fournies.
    L'objectif est d'identifier les relations statistiques significatives et d'en tirer des
    conclusions économiques, financières et stratégiques.
    """)
    
    # 2. Statistiques descriptives
    report.add_section("2. Statistiques Descriptives", level=1)
    
    # Créer un tableau des statistiques
    stats_data = [['Variable', 'Moyenne', 'Écart-type', 'Min', 'Max', 'N']]
    for var in variable_names:
        if var in data.columns:
            stats = data[var].describe()
            stats_data.append([
                var,
                f"{stats['mean']:.2f}",
                f"{stats['std']:.2f}",
                f"{stats['min']:.2f}",
                f"{stats['max']:.2f}",
                int(stats['count'])
            ])
    
    report.add_table(stats_data, title="Tableau des statistiques descriptives")
    
    # 3. Résultats du modèle
    report.add_section("3. Résultats du Modèle", level=1)
    
    # Ajouter les résultats spécifiques au modèle
    if 'summary' in model_results:
        report.add_paragraph(model_results['summary'])
    
    # 4. Interprétation économique
    report.add_section("4. Interprétation Économique", level=1)
    
    if 'economic_interpretation' in model_results:
        for interp in model_results['economic_interpretation']:
            report.add_interpretation(interp, 'economic')
    
    # 5. Interprétation financière
    if 'financial_interpretation' in model_results:
        report.add_section("5. Interprétation Financière", level=1)
        for interp in model_results['financial_interpretation']:
            report.add_interpretation(interp, 'financial')
    
    # 6. Décisions stratégiques
    if 'strategic_decisions' in model_results:
        report.add_section("6. Décisions Stratégiques", level=1)
        for interp in model_results['strategic_decisions']:
            report.add_interpretation(interp, 'strategic')
    
    # 7. Conclusion
    report.add_section("7. Conclusion", level=1)
    report.add_paragraph("""
    L'analyse réalisée permet de dégager des conclusions importantes pour la prise de décision.
    Les résultats obtenus sont statistiquement significatifs et permettent d'orienter les
    choix stratégiques à venir.
    """)
    
    return report