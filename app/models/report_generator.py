#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Générateur de rapports Word professionnels pour analyses économétriques
Version 2.0 : Rapport de 20+ pages avec graphiques adaptés
"""

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from datetime import datetime
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO


class ReportGenerator:
    """Générateur de rapports Word professionnels"""

    def __init__(self, title="Rapport d'Analyse Économétrique"):
        self.doc = Document()
        self.title = title
        self._setup_styles()
        self._setup_page()

    def _setup_styles(self):
        """Configurer les styles du document"""
        # Style normal
        style = self.doc.styles['Normal']
        style.font.name = 'Calibri'
        style.font.size = Pt(11)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.line_spacing = 1.15

        # Style Heading 1
        h1 = self.doc.styles['Heading 1']
        h1.font.name = 'Calibri'
        h1.font.size = Pt(18)
        h1.font.bold = True
        h1.font.color.rgb = RGBColor(26, 42, 108)

        # Style Heading 2
        h2 = self.doc.styles['Heading 2']
        h2.font.name = 'Calibri'
        h2.font.size = Pt(14)
        h2.font.bold = True
        h2.font.color.rgb = RGBColor(45, 53, 97)

    def _setup_page(self):
        """Configurer les marges"""
        for section in self.doc.sections:
            section.top_margin = Cm(2.5)
            section.bottom_margin = Cm(2.5)
            section.left_margin = Cm(2.5)
            section.right_margin = Cm(2.5)

    def _add_page_break(self):
        """Ajouter un saut de page"""
        self.doc.add_page_break()

    def _add_horizontal_line(self):
        """Ajouter une ligne horizontale"""
        p = self.doc.add_paragraph()
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single')
        bottom.set(qn('w:sz'), '6')
        bottom.set(qn('w:space'), '1')
        bottom.set(qn('w:color'), '1a2a6c')
        pBdr.append(bottom)
        pPr.append(pBdr)

    # ==================== PAGE DE COUVERTURE ====================
    def add_cover_page(self, subtitle, author="DataEcon.Ci"):
        """Ajouter la page de couverture"""
        # Espacement en haut
        for _ in range(4):
            self.doc.add_paragraph()

        # Titre
        title_p = self.doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_p.add_run("📊 DataEcon.Ci")
        run.font.size = Pt(28)
        run.font.bold = True
        run.font.color.rgb = RGBColor(26, 42, 108)

        # Espacement
        self.doc.add_paragraph()

        # Titre du rapport
        r_title = self.doc.add_paragraph()
        r_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = r_title.add_run(self.title)
        run.font.size = Pt(24)
        run.font.bold = True
        run.font.color.rgb = RGBColor(26, 42, 108)

        # Sous-titre
        self.doc.add_paragraph()
        r_sub = self.doc.add_paragraph()
        r_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = r_sub.add_run(subtitle)
        run.font.size = Pt(14)
        run.font.italic = True
        run.font.color.rgb = RGBColor(90, 106, 154)

        # Espacement
        for _ in range(8):
            self.doc.add_paragraph()

        # Informations
        info_p = self.doc.add_paragraph()
        info_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = info_p.add_run(f"Auteur : {author}\n")
        run.font.size = Pt(12)

        date_p = self.doc.add_paragraph()
        date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = date_p.add_run(f"Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
        run.font.size = Pt(12)

        self._add_page_break()

    # ==================== TABLE DES MATIÈRES ====================
    def add_toc(self, sections):
        """Ajouter une table des matières manuelle"""
        self.doc.add_heading("Table des matières", level=1)
        self._add_horizontal_line()

        for i, section in enumerate(sections, 1):
            p = self.doc.add_paragraph()
            run = p.add_run(f"{i}. {section}")
            run.font.size = Pt(12)
            p.paragraph_format.space_after = Pt(8)

        self._add_page_break()

    # ==================== SECTIONS ====================
    def add_section(self, title, level=1):
        """Ajouter une section avec titre"""
        return self.doc.add_heading(title, level=level)

    def add_paragraph(self, text, bold=False, italic=False, size=11, align=None):
        """Ajouter un paragraphe"""
        p = self.doc.add_paragraph()
        run = p.add_run(text)
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        if align == 'center':
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align == 'right':
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        elif align == 'justify':
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        return p

    def add_bullet(self, text, level=0):
        """Ajouter une puce"""
        p = self.doc.add_paragraph(style='List Bullet')
        if level > 0:
            p.paragraph_format.left_indent = Cm(1 * (level + 1))
        p.add_run(text)
        return p

    def add_numbered(self, text):
        """Ajouter une liste numérotée"""
        p = self.doc.add_paragraph(style='List Number')
        p.add_run(text)
        return p

    # ==================== TABLEAUX ====================
    def add_table(self, data, headers, title=None):
        """Ajouter un tableau formaté"""
        if title:
            self.doc.add_heading(title, level=3)

        rows = len(data)
        cols = len(data[0]) if data else 0

        table = self.doc.add_table(rows=rows + 1, cols=cols)
        table.style = 'Light Grid Accent 1'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # En-têtes
        hdr_cells = table.rows[0].cells
        for i, header in enumerate(headers):
            hdr_cells[i].text = str(header)
            for paragraph in hdr_cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
                    run.font.size = Pt(10)
                    run.font.color.rgb = RGBColor(255, 255, 255)

        # Données
        for i, row in enumerate(data, start=1):
            for j, cell in enumerate(row):
                table.rows[i].cells[j].text = str(cell)
                for paragraph in table.rows[i].cells[j].paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(10)

        return table

    # ==================== GRAPHIQUES ====================
    def add_figure(self, fig, caption=None, width=6):
        """Ajouter une figure matplotlib"""
        img_buffer = BytesIO()
        fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close(fig)

        self.doc.add_picture(img_buffer, width=Inches(width))
        # Centrer l'image
        last_p = self.doc.paragraphs[-1]
        last_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        if caption:
            cap = self.doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = cap.add_run(f"Figure : {caption}")
            run.font.italic = True
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(90, 106, 154)

    # ==================== INTERPRÉTATIONS ====================
    def add_interpretation(self, title, content, color='economic'):
        """Ajouter une interprétation colorée"""
        colors = {
            'economic': RGBColor(26, 42, 108),
            'financial': RGBColor(0, 128, 0),
            'strategic': RGBColor(192, 0, 0),
            'statistical': RGBColor(128, 0, 128)
        }
        icons = {
            'economic': '📊',
            'financial': '💰',
            'strategic': '🎯',
            'statistical': '📈'
        }

        h = self.doc.add_heading(f"{icons.get(color, '📌')} {title}", level=3)
        for run in h.runs:
            run.font.color.rgb = colors.get(color, RGBColor(0, 0, 0))

        self.add_paragraph(content, align='justify')

    def save(self, path):
        """Sauvegarder le document"""
        self.doc.save(path)
        return path


# ==================== GRAPHIQUES ADAPTÉS ====================

def create_data_distribution_chart(df, numeric_cols):
    """Créer un graphique de distribution des données"""
    n_cols = min(6, len(numeric_cols))
    if n_cols == 0:
        return None

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes = axes.flatten()

    for i, col in enumerate(numeric_cols[:6]):
        axes[i].hist(df[col].dropna(), bins=20, color='#1a2a6c', alpha=0.7, edgecolor='white')
        axes[i].set_title(f'Distribution de {col}', fontsize=10, fontweight='bold')
        axes[i].set_xlabel(col, fontsize=9)
        axes[i].set_ylabel('Fréquence', fontsize=9)
        axes[i].grid(True, alpha=0.3)

    for i in range(n_cols, 6):
        axes[i].axis('off')

    plt.tight_layout()
    return fig


def create_correlation_heatmap(df, numeric_cols):
    """Créer une matrice de corrélation"""
    if len(numeric_cols) < 2:
        return None

    fig, ax = plt.subplots(figsize=(10, 8))
    corr = df[numeric_cols].corr()
    sns.heatmap(corr, annot=True, cmap='coolwarm', center=0,
                square=True, fmt='.2f', cbar_kws={'shrink': 0.8}, ax=ax)
    ax.set_title('Matrice de corrélation', fontsize=13, fontweight='bold', pad=15)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    return fig


def create_boxplots(df, numeric_cols):
    """Créer des boîtes à moustaches"""
    if len(numeric_cols) == 0:
        return None

    n_cols = min(6, len(numeric_cols))
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes = axes.flatten()

    for i, col in enumerate(numeric_cols[:6]):
        axes[i].boxplot(df[col].dropna(), patch_artist=True,
                       boxprops=dict(facecolor='#fdbb2d', alpha=0.7))
        axes[i].set_title(f'Boxplot de {col}', fontsize=10, fontweight='bold')
        axes[i].set_ylabel(col, fontsize=9)
        axes[i].grid(True, alpha=0.3)

    for i in range(n_cols, 6):
        axes[i].axis('off')

    plt.tight_layout()
    return fig


def create_scatter_matrix(df, numeric_cols, target_col=None):
    """Créer une matrice de nuages de points"""
    if len(numeric_cols) < 2:
        return None

    cols_to_use = numeric_cols[:4]
    n = len(cols_to_use)

    fig, axes = plt.subplots(n, n, figsize=(12, 12))

    for i in range(n):
        for j in range(n):
            if i == j:
                axes[i, j].hist(df[cols_to_use[i]].dropna(), bins=15,
                              color='#1a2a6c', alpha=0.7)
                axes[i, j].set_ylabel('Fréquence', fontsize=8)
            else:
                axes[i, j].scatter(df[cols_to_use[j]], df[cols_to_use[i]],
                                   alpha=0.5, s=15, color='#2d3561')
            if i == n - 1:
                axes[i, j].set_xlabel(cols_to_use[j], fontsize=9)
            if j == 0:
                axes[i, j].set_ylabel(cols_to_use[i], fontsize=9)

    plt.suptitle('Matrice de nuages de points', fontsize=13, fontweight='bold', y=0.995)
    plt.tight_layout()
    return fig


def create_residuals_plot(df, target_col, predictions=None):
    """Créer un graphique des résidus"""
    if predictions is None:
        return None

    residuals = df[target_col].values - predictions

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Résidus vs valeurs prédites
    axes[0].scatter(predictions, residuals, alpha=0.5, s=20, color='#1a2a6c')
    axes[0].axhline(y=0, color='red', linestyle='--', linewidth=2)
    axes[0].set_xlabel('Valeurs prédites', fontsize=10)
    axes[0].set_ylabel('Résidus', fontsize=10)
    axes[0].set_title('Résidus vs Valeurs prédites', fontsize=11, fontweight='bold')
    axes[0].grid(True, alpha=0.3)

    # QQ plot
    from scipy import stats
    stats.probplot(residuals, dist="norm", plot=axes[1])
    axes[1].set_title('Q-Q Plot des résidus', fontsize=11, fontweight='bold')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def create_time_series_plot(df, col):
    """Créer un graphique de série temporelle"""
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # Série originale
    axes[0].plot(df.index, df[col], color='#1a2a6c', linewidth=1.5)
    axes[0].set_title(f'Évolution de {col}', fontsize=12, fontweight='bold')
    axes[0].set_xlabel('Temps', fontsize=10)
    axes[0].set_ylabel(col, fontsize=10)
    axes[0].grid(True, alpha=0.3)
    axes[0].fill_between(df.index, df[col], alpha=0.2, color='#1a2a6c')

    # Moyenne mobile
    rolling = df[col].rolling(window=12).mean()
    axes[1].plot(df.index, df[col], color='#2d3561', linewidth=1, alpha=0.5, label='Série')
    axes[1].plot(df.index, rolling, color='#fdbb2d', linewidth=2, label='Moyenne mobile (12)')
    axes[1].set_title(f'Tendance de {col}', fontsize=12, fontweight='bold')
    axes[1].set_xlabel('Temps', fontsize=10)
    axes[1].set_ylabel(col, fontsize=10)
    axes[1].legend(loc='best')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def create_model_comparison_chart(models_results):
    """Créer un graphique de comparaison des modèles"""
    if not models_results:
        return None

    models = []
    r2_scores = []
    rmse_scores = []

    for name, metrics in models_results.items():
        if metrics.get('r2') is not None:
            models.append(name.replace('_', ' ').title())
            r2_scores.append(metrics['r2'])
            rmse_scores.append(metrics.get('rmse', 0))

    if not models:
        return None

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # R²
    colors = ['#fdbb2d' if r == max(r2_scores) else '#1a2a6c' for r in r2_scores]
    bars1 = axes[0].barh(models, r2_scores, color=colors, edgecolor='white', linewidth=2)
    axes[0].set_xlabel('R² (coefficient de détermination)', fontsize=10)
    axes[0].set_title('Comparaison des R²', fontsize=12, fontweight='bold')
    axes[0].set_xlim(0, 1)
    for i, v in enumerate(r2_scores):
        axes[0].text(v + 0.01, i, f'{v:.4f}', va='center', fontsize=9, fontweight='bold')

    # RMSE
    bars2 = axes[1].barh(models, rmse_scores, color='#2d3561', edgecolor='white', linewidth=2)
    axes[1].set_xlabel('RMSE (plus petit = meilleur)', fontsize=10)
    axes[1].set_title('Comparaison des RMSE', fontsize=12, fontweight='bold')
    for i, v in enumerate(rmse_scores):
        axes[1].text(v + 0.01, i, f'{v:.4f}', va='center', fontsize=9, fontweight='bold')

    plt.tight_layout()
    return fig


def create_coefficients_chart(coefficients):
    """Créer un graphique des coefficients"""
    if not coefficients:
        return None

    vars_list = list(coefficients.keys())
    coefs = list(coefficients.values())

    # Trier par valeur absolue
    sorted_pairs = sorted(zip(vars_list, coefs), key=lambda x: abs(x[1]), reverse=True)
    vars_list, coefs = zip(*sorted_pairs)

    fig, ax = plt.subplots(figsize=(10, max(5, len(vars_list) * 0.4)))

    colors = ['#28a745' if c > 0 else '#dc3545' for c in coefs]
    bars = ax.barh(vars_list, coefs, color=colors, edgecolor='white', linewidth=1.5)
    ax.axvline(x=0, color='black', linewidth=0.8, linestyle='-')
    ax.set_xlabel('Coefficient', fontsize=10)
    ax.set_title('Importance des variables (coefficients)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')

    for bar, v in zip(bars, coefs):
        width = bar.get_width()
        ax.text(width + (0.01 if width >= 0 else -0.01), bar.get_y() + bar.get_height() / 2,
                f'{v:.4f}', va='center', ha='left' if width >= 0 else 'right',
                fontsize=9, fontweight='bold')

    plt.tight_layout()
    return fig


def create_forecast_chart(forecast_values):
    """Créer un graphique de prévisions"""
    if not forecast_values:
        return None

    fig, ax = plt.subplots(figsize=(12, 5))
    periods = list(range(1, len(forecast_values) + 1))
    ax.plot(periods, forecast_values, marker='o', color='#1a2a6c',
            linewidth=2, markersize=8, markerfacecolor='#fdbb2d')
    ax.fill_between(periods, forecast_values, alpha=0.2, color='#1a2a6c')
    ax.set_xlabel('Période', fontsize=11)
    ax.set_ylabel('Valeur prévue', fontsize=11)
    ax.set_title('Prévisions', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


# ==================== FONCTION PRINCIPALE ====================

def create_econometric_report(data, model_results, model_type, variable_names):
    """
    Créer un rapport complet de 20+ pages
    """
    model_type_labels = {
        'regression': "Analyse de Régression",
        'time_series': "Analyse de Séries Temporelles",
        'machine_learning': "Analyse par Machine Learning",
        'deep_learning': "Analyse par Deep Learning",
        'financial_series': "Analyse de Séries Financières"
    }

    report = ReportGenerator(
        title=model_type_labels.get(model_type, "Analyse Économétrique")
    )

    # ===== PAGE DE COUVERTURE =====
    report.add_cover_page(subtitle=model_type_labels.get(model_type, "Analyse"))

    # ===== TABLE DES MATIÈRES =====
    sections = [
        "Résumé exécutif",
        "Introduction et contexte",
        "Présentation des données",
        "Statistiques descriptives",
        "Méthodologie",
        "Analyse exploratoire",
        "Résultats du modèle",
        "Interprétation économique",
        "Interprétation financière",
        "Décisions stratégiques",
        "Limites et recommandations",
        "Conclusion",
        "Annexes"
    ]
    report.add_toc(sections)

    # ===== 1. RÉSUMÉ EXÉCUTIF =====
    report.add_section("1. Résumé exécutif", level=1)
    report.add_paragraph(
        f"Ce rapport présente les résultats d'une analyse {model_type_labels.get(model_type, '').lower()} "
        f"réalisée sur un jeu de données contenant {len(data)} observations et {len(data.columns)} variables. "
        f"L'objectif est d'identifier les relations statistiques significatives entre les variables étudiées "
        f"et d'en tirer des conclusions exploitables pour la prise de décision.",
        align='justify'
    )

    if model_results.get('comparison'):
        best_model = model_results['comparison'].get('best_model', 'N/A')
        best_r2 = model_results['comparison'].get('best_r2', 0)
        report.add_paragraph(
            f"Le meilleur modèle identifié est « {best_model} » avec un coefficient de détermination "
            f"R² = {best_r2:.4f}, indiquant que ce modèle explique {best_r2 * 100:.1f}% de la variance "
            f"de la variable cible.",
            align='justify'
        )

    report.add_paragraph("Principaux résultats :", bold=True)
    if model_results.get('economic_interpretation'):
        for interp in model_results['economic_interpretation'][:3]:
            report.add_bullet(interp)

    report._add_page_break()

    # ===== 2. INTRODUCTION =====
    report.add_section("2. Introduction et contexte", level=1)
    report.add_paragraph(
        "L'économétrie est une discipline qui combine la théorie économique, les mathématiques "
        "et l'inférence statistique pour analyser des données économiques et tester des hypothèses "
        "théoriques. Elle est largement utilisée dans la recherche académique, l'analyse de politiques "
        "publiques et la prise de décision en entreprise.",
        align='justify'
    )

    report.add_section("2.1 Objectifs de l'analyse", level=2)
    report.add_paragraph("Cette analyse poursuit les objectifs suivants :", align='justify')
    report.add_numbered("Identifier les relations statistiques entre les variables du jeu de données.")
    report.add_numbered("Quantifier l'impact de chaque variable explicative sur la variable cible.")
    report.add_numbered("Évaluer la qualité et la robustesse du modèle estimé.")
    report.add_numbered("Fournir des recommandations exploitables pour la prise de décision.")

    report.add_section("2.2 Variables étudiées", level=2)
    report.add_paragraph(
        f"Le jeu de données contient {len(data.columns)} variables : {', '.join(variable_names[:10])}"
        f"{'...' if len(variable_names) > 10 else ''}.",
        align='justify'
    )

    report._add_page_break()

    # ===== 3. PRÉSENTATION DES DONNÉES =====
    report.add_section("3. Présentation des données", level=1)
    report.add_paragraph(
        f"Le jeu de données analysé contient {len(data)} observations. "
        f"Voici un aperçu des premières lignes :",
        align='justify'
    )

    # Tableau des 10 premières lignes
    preview_data = data.head(10).values.tolist()
    preview_headers = list(data.columns)
    # Limiter à 6 colonnes pour la lisibilité
    if len(preview_headers) > 6:
        preview_headers = preview_headers[:6]
        preview_data = [row[:6] for row in preview_data]

    report.add_table(preview_data, preview_headers,
                    title="Aperçu des 10 premières lignes")

    report._add_page_break()

    # ===== 4. STATISTIQUES DESCRIPTIVES =====
    report.add_section("4. Statistiques descriptives", level=1)
    report.add_paragraph(
        "Les statistiques descriptives fournissent un résumé quantitatif des principales "
        "caractéristiques de chaque variable :",
        align='justify'
    )

    # Tableau des statistiques
    numeric_data = data.select_dtypes(include=[np.number])
    if len(numeric_data.columns) > 0:
        stats_data = []
        for col in numeric_data.columns[:10]:
            stats_data.append([
                col,
                f"{numeric_data[col].mean():.2f}",
                f"{numeric_data[col].std():.2f}",
                f"{numeric_data[col].min():.2f}",
                f"{numeric_data[col].max():.2f}",
                f"{numeric_data[col].median():.2f}"
            ])

        report.add_table(
            stats_data,
            ["Variable", "Moyenne", "Écart-type", "Min", "Max", "Médiane"],
            title="Statistiques descriptives des variables numériques"
        )

    # Graphique de distribution
    numeric_cols = numeric_data.columns.tolist()
    if len(numeric_cols) > 0:
        fig = create_data_distribution_chart(data, numeric_cols)
        if fig:
            report.add_figure(fig, "Distribution des variables numériques")

    report._add_page_break()

    # ===== 5. MÉTHODOLOGIE =====
    report.add_section("5. Méthodologie", level=1)

    if model_type == 'regression':
        report.add_paragraph(
            "La régression linéaire multiple est utilisée pour modéliser la relation entre "
            "une variable dépendante (Y) et plusieurs variables indépendantes (X₁, X₂, ..., Xₖ).",
            align='justify'
        )
        report.add_paragraph("Équation du modèle :", bold=True)
        report.add_paragraph(
            "Y = β₀ + β₁X₁ + β₂X₂ + ... + βₖXₖ + ε",
            align='center', italic=True, size=12
        )
        report.add_paragraph(
            "Les coefficients βᵢ sont estimés par la méthode des Moindres Carrés Ordinaires (MCO), "
            "qui minimise la somme des carrés des résidus (écarts entre valeurs observées et prédites).",
            align='justify'
        )
    elif model_type == 'time_series':
        report.add_paragraph(
            "L'analyse de séries temporelles étudie l'évolution d'une variable au cours du temps. "
            "Le modèle ARIMA (AutoRegressive Integrated Moving Average) est utilisé pour capturer "
            "les dépendances temporelles.",
            align='justify'
        )
    elif model_type in ['machine_learning', 'deep_learning']:
        report.add_paragraph(
            "Les modèles de machine learning sont utilisés pour capturer des relations complexes "
            "et non-linéaires entre les variables. Plusieurs algorithmes sont comparés.",
            align='justify'
        )

    report._add_page_break()

    # ===== 6. ANALYSE EXPLORATOIRE =====
    report.add_section("6. Analyse exploratoire", level=1)

    if len(numeric_cols) >= 2:
        # Matrice de corrélation
        fig = create_correlation_heatmap(data, numeric_cols[:10])
        if fig:
            report.add_figure(fig, "Matrice de corrélation entre les variables")

        report.add_paragraph(
            "La matrice de corrélation révèle les relations linéaires entre les variables. "
            "Les coefficients proches de +1 indiquent une forte corrélation positive, "
            "ceux proches de -1 une forte corrélation négative, et ceux proches de 0 "
            "l'absence de relation linéaire.",
            align='justify'
        )

        # Boxplots
        fig = create_boxplots(data, numeric_cols[:6])
        if fig:
            report.add_figure(fig, "Boîtes à moustaches des variables")

    report._add_page_break()

    # ===== 7. RÉSULTATS DU MODÈLE =====
    report.add_section("7. Résultats du modèle", level=1)

    if model_results.get('models'):
        # Tableau comparatif
        comparison_data = []
        for name, metrics in model_results['models'].items():
            comparison_data.append([
                name.replace('_', ' ').title(),
                f"{metrics.get('r2', 0):.4f}" if metrics.get('r2') is not None else '-',
                f"{metrics.get('rmse', 0):.4f}" if metrics.get('rmse') is not None else '-',
                f"{metrics.get('mae', 0):.4f}" if metrics.get('mae') is not None else '-'
            ])

        report.add_table(
            comparison_data,
            ["Modèle", "R²", "RMSE", "MAE"],
            title="Comparaison des performances des modèles"
        )

        # Graphique de comparaison
        fig = create_model_comparison_chart(model_results['models'])
        if fig:
            report.add_figure(fig, "Comparaison visuelle des modèles")

    # Coefficients du meilleur modèle
    if model_results.get('models'):
        best_model = model_results.get('comparison', {}).get('best_model', '')
        for name, metrics in model_results['models'].items():
            if metrics.get('coefficients'):
                # Équation
                report.add_section(f"7.1 Équation du modèle : {name.title()}", level=2)
                coefs = metrics['coefficients']
                intercept = metrics.get('intercept', 0)

                equation = f"Y = {intercept:.4f}"
                for var, coef in coefs.items():
                    if coef != 0:
                        sign = "+" if coef >= 0 else "-"
                        equation += f" {sign} {abs(coef):.4f} × {var}"

                report.add_paragraph(equation, align='center', italic=True, size=12)

                # Tableau des coefficients
                coef_data = []
                for var, coef in coefs.items():
                    effect = "Positif" if coef > 0.01 else ("Négatif" if coef < -0.01 else "Neutre")
                    coef_data.append([
                        var,
                        f"{coef:.4f}",
                        effect
                    ])

                report.add_table(
                    coef_data,
                    ["Variable", "Coefficient", "Effet"],
                    title="Coefficients du modèle"
                )

                # Graphique des coefficients
                fig = create_coefficients_chart(coefs)
                if fig:
                    report.add_figure(fig, "Importance relative des variables")

                break

    report._add_page_break()

    # ===== 8. INTERPRÉTATION ÉCONOMIQUE =====
    report.add_section("8. Interprétation économique", level=1)
    report.add_paragraph(
        "L'interprétation économique des résultats permet de comprendre la signification "
        "pratique des relations statistiques identifiées.",
        align='justify'
    )

    if model_results.get('economic_interpretation'):
        for interp in model_results['economic_interpretation']:
            report.add_bullet(interp)
    else:
        report.add_paragraph("Aucune interprétation économique disponible.")

    report._add_page_break()

    # ===== 9. INTERPRÉTATION FINANCIÈRE =====
    report.add_section("9. Interprétation financière", level=1)
    report.add_paragraph(
        "L'analyse financière permet d'évaluer les implications économiques et les risques "
        "associés aux résultats obtenus.",
        align='justify'
    )

    if model_results.get('financial_interpretation'):
        for interp in model_results['financial_interpretation']:
            report.add_bullet(interp)
    else:
        report.add_paragraph("Aucune interprétation financière disponible.")

    report._add_page_break()

    # ===== 10. DÉCISIONS STRATÉGIQUES =====
    report.add_section("10. Décisions stratégiques", level=1)
    report.add_paragraph(
        "Sur la base des résultats obtenus, les recommandations stratégiques suivantes "
        "peuvent être formulées :",
        align='justify'
    )

    if model_results.get('strategic_decisions'):
        for decision in model_results['strategic_decisions']:
            if decision.startswith('•'):
                report.add_bullet(decision[1:].strip())
            else:
                report.add_paragraph(decision, bold=True)

    report._add_page_break()

    # ===== 11. LIMITES ET RECOMMANDATIONS =====
    report.add_section("11. Limites et recommandations", level=1)

    report.add_section("11.1 Limites de l'analyse", level=2)
    report.add_bullet("Les résultats dépendent de la qualité et de la représentativité des données.")
    report.add_bullet("Les relations identifiées sont des corrélations, pas nécessairement des causalités.")
    report.add_bullet("Le modèle peut être sensible aux valeurs aberrantes (outliers).")
    report.add_bullet("L'extrapolation à d'autres populations doit être faite avec prudence.")

    report.add_section("11.2 Recommandations", level=2)
    report.add_numbered("Collecter davantage de données pour améliorer la robustesse du modèle.")
    report.add_numbered("Tester d'autres spécifications de modèle (log-log, semi-log, etc.).")
    report.add_numbered("Vérifier les hypothèses du modèle (homoscédasticité, normalité des résidus).")
    report.add_numbered("Mettre à jour régulièrement le modèle avec de nouvelles données.")

    report._add_page_break()

    # ===== 12. CONCLUSION =====
    report.add_section("12. Conclusion", level=1)
    report.add_paragraph(
        f"Cette analyse a permis d'identifier les principales relations statistiques dans le "
        f"jeu de données étudié. Les résultats obtenus fournissent une base solide pour la "
        f"prise de décision et peuvent être utilisés pour orienter les choix stratégiques.",
        align='justify'
    )
    report.add_paragraph(
        "Les recommandations formulées dans ce rapport doivent être considérées comme un "
        "point de départ pour des analyses plus approfondies. L'utilisation régulière de ces "
        "outils analytiques permettra d'améliorer progressivement la qualité des décisions.",
        align='justify'
    )

    report._add_page_break()

    # ===== 13. ANNEXES =====
    report.add_section("13. Annexes", level=1)

    report.add_section("Annexe A : Dictionnaire des variables", level=2)
    var_data = []
    for col in data.columns:
        dtype = str(data[col].dtype)
        missing = data[col].isnull().sum()
        var_data.append([col, dtype, str(missing)])

    report.add_table(
        var_data,
        ["Variable", "Type", "Valeurs manquantes"],
        title="Détail des variables du jeu de données"
    )

    report.add_section("Annexe B : Informations techniques", level=2)
    report.add_bullet(f"Nombre total d'observations : {len(data)}")
    report.add_bullet(f"Nombre de variables : {len(data.columns)}")
    report.add_bullet(f"Variables numériques : {len(numeric_data.columns)}")
    report.add_bullet(f"Type d'analyse : {model_type_labels.get(model_type, 'N/A')}")
    report.add_bullet(f"Date de génération : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    report.add_bullet(f"Outil : DataEcon.Ci")

    return report


# ==================== GÉNÉRATEUR LATEX ====================

def create_latex_report(data, model_results, model_type, variable_names):
    """Générer un rapport LaTeX complet"""
    model_type_labels = {
        'regression': "Analyse de Régression",
        'time_series': "Analyse de Séries Temporelles",
        'machine_learning': "Analyse par Machine Learning",
        'deep_learning': "Analyse par Deep Learning",
        'financial_series': "Analyse de Séries Financières"
    }

    title = model_type_labels.get(model_type, "Analyse Économétrique")
    numeric_data = data.select_dtypes(include=[np.number])

    latex = []

    # Préambule
    latex.append(r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[french]{babel}
\usepackage{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{float}
\usepackage{caption}
\usepackage{fancyhdr}

\geometry{margin=2.5cm}
\definecolor{primary}{RGB}{26,42,108}
\definecolor{accent}{RGB}{253,187,45}

\hypersetup{
    colorlinks=true,
    linkcolor=primary,
    urlcolor=primary,
}

\pagestyle{fancy}
\fancyhf{}
\rhead{\textcolor{primary}{DataEcon.Ci}}
\lhead{\textcolor{primary}{""" + title + r"""}}
\rfoot{\thepage}

\title{\textbf{\textcolor{primary}{""" + title + r"""}}}
\author{DataEcon.Ci}
\date{""" + datetime.now().strftime('%d/%m/%Y') + r"""}

\begin{document}

\maketitle

\begin{abstract}
Ce rapport présente les résultats d'une analyse """ + title.lower() + r""" réalisée sur un jeu de données contenant """ + str(len(data)) + r""" observations et """ + str(len(data.columns)) + r""" variables. L'objectif est d'identifier les relations statistiques significatives et d'en tirer des conclusions exploitables.
\end{abstract}

\newpage
\tableofcontents
\newpage
""")

    # Section 1 : Introduction
    latex.append(r"""
\section{Introduction et contexte}

L'économétrie est une discipline qui combine la théorie économique, les mathématiques et l'inférence statistique pour analyser des données économiques et tester des hypothèses théoriques.

\subsection{Objectifs}

\begin{enumerate}
    \item Identifier les relations statistiques entre les variables.
    \item Quantifier l'impact de chaque variable explicative.
    \item Évaluer la qualité du modèle estimé.
    \item Fournir des recommandations exploitables.
\end{enumerate}
""")

    # Section 2 : Données
    latex.append(r"""
\section{Présentation des données}

Le jeu de données analysé contient """ + str(len(data)) + r""" observations.

\subsection{Aperçu}

\begin{table}[H]
\centering
\caption{Aperçu des premières lignes}
\begin{tabular}{""" + "l" * min(6, len(data.columns)) + r"""}
\toprule
""")

    # En-têtes
    headers = list(data.columns)[:6]
    latex.append(" & ".join([r"\textbf{" + str(h) + "}" for h in headers]) + r" \\")
    latex.append(r"\midrule")

    # Données
    for _, row in data.head(5).iterrows():
        row_vals = [str(v)[:15] for v in row.values[:6]]
        latex.append(" & ".join(row_vals) + r" \\")

    latex.append(r"""
\bottomrule
\end{tabular}
\end{table}
""")

    # Section 3 : Statistiques descriptives
    latex.append(r"""
\section{Statistiques descriptives}

\begin{table}[H]
\centering
\caption{Statistiques descriptives}
\begin{longtable}{lrrrrr}
\toprule
\textbf{Variable} & \textbf{Moyenne} & \textbf{Écart-type} & \textbf{Min} & \textbf{Max} & \textbf{Médiane} \\
\midrule
\endhead
""")

    for col in numeric_data.columns[:10]:
        latex.append(
            f"{col} & {numeric_data[col].mean():.2f} & {numeric_data[col].std():.2f} & "
            f"{numeric_data[col].min():.2f} & {numeric_data[col].max():.2f} & "
            f"{numeric_data[col].median():.2f} \\\\"
        )

    latex.append(r"""
\bottomrule
\end{longtable}
\end{table}
""")

    # Section 4 : Résultats
    latex.append(r"""
\section{Résultats du modèle}
""")

    if model_results.get('models'):
        latex.append(r"""
\begin{table}[H]
\centering
\caption{Comparaison des modèles}
\begin{tabular}{lrrr}
\toprule
\textbf{Modèle} & \textbf{R²} & \textbf{RMSE} & \textbf{MAE} \\
\midrule
""")

        for name, metrics in model_results['models'].items():
            r2 = f"{metrics.get('r2', 0):.4f}" if metrics.get('r2') is not None else "-"
            rmse = f"{metrics.get('rmse', 0):.4f}" if metrics.get('rmse') is not None else "-"
            mae = f"{metrics.get('mae', 0):.4f}" if metrics.get('mae') is not None else "-"
            latex.append(f"{name.replace('_', ' ').title()} & {r2} & {rmse} & {mae} \\\\")

        latex.append(r"""
\bottomrule
\end{tabular}
\end{table}
""")

    # Coefficients
    if model_results.get('models'):
        for name, metrics in model_results['models'].items():
            if metrics.get('coefficients'):
                latex.append(r"""
\subsection{Équation du modèle : """ + name.title() + r"""}

\begin{equation}
Y = """ + f"{metrics.get('intercept', 0):.4f}")

                for var, coef in metrics['coefficients'].items():
                    if coef != 0:
                        sign = "+" if coef >= 0 else "-"
                        latex.append(f" {sign} {abs(coef):.4f} \\times \\text{{{var}}}")

                latex.append(r"""
\end{equation}

\begin{table}[H]
\centering
\caption{Coefficients}
\begin{tabular}{lrl}
\toprule
\textbf{Variable} & \textbf{Coefficient} & \textbf{Effet} \\
\midrule
""")

                for var, coef in metrics['coefficients'].items():
                    effect = "Positif" if coef > 0.01 else ("Négatif" if coef < -0.01 else "Neutre")
                    latex.append(f"{var} & {coef:.4f} & {effect} \\\\")

                latex.append(r"""
\bottomrule
\end{tabular}
\end{table}
""")
                break

    # Section 5 : Interprétations
    latex.append(r"""
\section{Interprétation économique}
""")

    if model_results.get('economic_interpretation'):
        latex.append(r"\begin{itemize}" + "\n")
        for interp in model_results['economic_interpretation']:
            latex.append(r"\item " + interp.replace('_', r'\_') + "\n")
        latex.append(r"\end{itemize}" + "\n")

    latex.append(r"""
\section{Interprétation financière}
""")

    if model_results.get('financial_interpretation'):
        latex.append(r"\begin{itemize}" + "\n")
        for interp in model_results['financial_interpretation']:
            latex.append(r"\item " + interp.replace('_', r'\_') + "\n")
        latex.append(r"\end{itemize}" + "\n")

    latex.append(r"""
\section{Décisions stratégiques}
""")

    if model_results.get('strategic_decisions'):
        latex.append(r"\begin{itemize}" + "\n")
        for decision in model_results['strategic_decisions']:
            d = decision.replace('_', r'\_').replace('•', '').strip()
            if d:
                latex.append(r"\item " + d + "\n")
        latex.append(r"\end{itemize}" + "\n")

    # Conclusion
    latex.append(r"""
\section{Conclusion}

Cette analyse a permis d'identifier les principales relations statistiques dans le jeu de données étudié. Les résultats fournissent une base solide pour la prise de décision.

\section*{Annexe : Informations techniques}
\begin{itemize}
    \item Observations : """ + str(len(data)) + r"""
    \item Variables : """ + str(len(data.columns)) + r"""
    \item Type d'analyse : """ + title + r"""
    \item Date : """ + datetime.now().strftime('%d/%m/%Y %H:%M') + r"""
\end{itemize}

\end{document}
""")

    return "\n".join(latex)