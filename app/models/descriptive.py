# -*- coding: utf-8 -*-
"""
Partie « données » du rapport : contexte, problématique, statistiques descriptives,
graphiques adaptés aux données et tests préliminaires.

build_data_report(...) renvoie
  {'sections': [{'id', 'title', 'text': [str], 'tables': [{title, columns, rows}], 'charts': [{title, img}]}],
   'context': str, 'problem': str}
"""
import warnings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from models.analysis import (prepare_xy, prepare_series, stationarity, detect_seasonality,
                             arch_effect, column_kind)
from models.runners import fmt, fmt_p, to_b64, NAVY, STEEL, GOLD, GREY, RED, GREEN

warnings.filterwarnings('ignore')
plt.rcParams['axes.axisbelow'] = True

PALETTE = [NAVY, STEEL, GOLD, '#5b8c85', '#8a94a3', '#a23b3b', '#6a5d9a', '#b87a3d']


def _section(sid, title):
    return {'id': sid, 'title': title, 'text': [], 'tables': [], 'charts': []}


def _tbl(sec, title, columns, rows):
    sec['tables'].append({'title': title, 'columns': columns, 'rows': [[str(c) for c in r] for r in rows]})


def _chart(sec, title, fig):
    sec['charts'].append({'title': title, 'img': to_b64(fig)})


# ----------------------------------------------------------------------------------------------
def _target_kind(ctx):
    return ctx.get('target_kind', 'continuous')


def _auto_context(dataset_name, target, features, ctx, time_col, entity_col):
    struct = {'cross_section': 'en coupe transversale', 'time_series': 'sous forme de série temporelle',
              'panel': 'en panel (individus suivis dans le temps)'}.get(ctx.get('structure'), '')
    kind = {'continuous': 'quantitative continue', 'binary': 'binaire', 'multiclass': 'qualitative à plusieurs modalités'}.get(
        _target_kind(ctx), '')
    txt = (f"Cette étude exploite le jeu de données « {dataset_name} », organisé {struct}, qui comporte {ctx.get('n', 0)} observations "
           f"({ctx.get('n_used', ctx.get('n', 0))} utilisables après retrait des valeurs manquantes). La variable étudiée, « {target} », est {kind}.")
    if features:
        txt += " Les variables mobilisées pour l'expliquer sont : " + ', '.join(features) + '.'
    if time_col:
        txt += f" La dimension temporelle est portée par « {time_col} »."
    if entity_col:
        txt += f" Les unités d'observation sont identifiées par « {entity_col} »."
    return txt


def _auto_problem(target, features, ctx):
    st = ctx.get('structure')
    kind = _target_kind(ctx)
    if st == 'time_series' and not features:
        return (f"Comment évolue « {target} » dans le temps ? La série est-elle stationnaire, présente-t-elle une saisonnalité ou des "
                f"phases de forte volatilité, et quelle trajectoire peut-on anticiper à court terme ?")
    if st == 'panel':
        return (f"Dans quelle mesure les variables {', '.join(features)} expliquent-elles « {target} » une fois contrôlée l'hétérogénéité "
                f"propre à chaque unité, et l'effet estimé est-il robuste au choix de la spécification (MCO empilés, effets fixes, effets aléatoires) ?")
    if kind in ('binary', 'multiclass'):
        return (f"Quels facteurs, parmi {', '.join(features)}, déterminent la modalité de « {target} » et avec quelle capacité de "
                f"prédiction hors échantillon ?")
    return (f"Quelle est l'influence de {', '.join(features) if features else 'la dynamique propre de la série'} sur « {target} », "
            f"et la relation mise en évidence est-elle stable lorsque l'on change de méthode ou d'échantillon ?")


# ----------------------------------------------------------------------------------------------
def _numeric_cols(df, cols):
    out = []
    for c in cols:
        if c in df.columns and pd.api.types.is_numeric_dtype(df[c]) and df[c].dtype != bool and df[c].nunique() > 2:
            out.append(c)
    return out


def _cat_cols(df, cols):
    out = []
    for c in cols:
        if c not in df.columns:
            continue
        s = df[c]
        if (not pd.api.types.is_numeric_dtype(s)) or s.dtype == bool or s.nunique() <= 8:
            if 1 < s.nunique() <= 30:
                out.append(c)
    return out


def _describe_numeric(df, cols):
    rows = []
    for c in cols:
        x = pd.to_numeric(df[c], errors='coerce').dropna()
        if len(x) == 0:
            continue
        q1, med, q3 = x.quantile([.25, .5, .75])
        rows.append([c, len(x), fmt(x.mean(), 3), fmt(x.std(), 3), fmt(x.min(), 3), fmt(q1, 3), fmt(med, 3), fmt(q3, 3),
                     fmt(x.max(), 3), fmt(stats.skew(x), 2) if len(x) > 2 else '—', fmt(stats.kurtosis(x), 2) if len(x) > 3 else '—'])
    return rows


def _shape_sentence(c, x):
    sk = stats.skew(x)
    ku = stats.kurtosis(x)
    parts = []
    if abs(sk) < .5:
        parts.append('distribution à peu près symétrique')
    else:
        parts.append('asymétrie ' + ('à droite (queue de valeurs élevées)' if sk > 0 else 'à gauche (queue de valeurs faibles)'))
    if ku > 1:
        parts.append('queues épaisses (valeurs extrêmes fréquentes)')
    elif ku < -1:
        parts.append('distribution aplatie')
    return f"« {c} » : moyenne {fmt(x.mean(), 2)}, écart-type {fmt(x.std(), 2)} ; " + ' et '.join(parts) + '.'


# ----------------------------------------------------------------------------------------------
def build_data_report(df, target, features, ctx, time_col=None, entity_col=None, dataset_name='',
                      context='', problem='', title=''):
    sections = []
    kind = _target_kind(ctx)
    structure = ctx.get('structure', 'cross_section')
    used = [target] + [f for f in features]
    num = _numeric_cols(df, used)
    cat = _cat_cols(df, used)
    ctx_text = (context or '').strip() or _auto_context(dataset_name, target, features, ctx, time_col, entity_col)
    prob_text = (problem or '').strip() or _auto_problem(target, features, ctx)

    # ---------------- 1. contexte et problématique
    s = _section('contexte', 'Contexte et problématique')
    s['text'] += [ctx_text, 'Problématique : ' + prob_text]
    objectifs = []
    if structure == 'time_series':
        objectifs = ["Caractériser la dynamique de la série (tendance, saisonnalité, stationnarité).",
                     "Estimer des modèles adaptés et comparer leur pouvoir prédictif.",
                     "Vérifier la robustesse des résultats (ordres alternatifs, prévision hors échantillon)."]
    elif structure == 'panel':
        objectifs = ["Décrire la structure du panel (individus, périodes, équilibre).",
                     "Comparer les estimateurs empilé, à effets fixes et à effets aléatoires, et arbitrer par le test de Hausman.",
                     "Contrôler la robustesse (erreurs groupées, validation en omettant chaque individu)."]
    elif kind in ('binary', 'multiclass'):
        objectifs = ["Décrire la répartition des classes et le profil des variables explicatives.",
                     "Estimer des modèles de classification et mesurer la qualité de prédiction.",
                     "Tester la stabilité des résultats (validation croisée, seuil de décision)."]
    else:
        objectifs = ["Décrire les variables et leurs relations.",
                     "Estimer des modèles de régression adaptés aux caractéristiques des données.",
                     "Tester la robustesse (erreurs standard alternatives, valeurs atypiques, rééchantillonnage)."]
    s['text'].append('Objectifs : ' + ' '.join(f'({i}) {o}' for i, o in enumerate(objectifs, 1)))
    sections.append(s)

    # ---------------- 2. statistiques descriptives
    s = _section('descriptives', 'Statistiques descriptives')
    n_tot = len(df)
    miss_rows = []
    for c in used + [x for x in (time_col, entity_col) if x]:
        if c in df.columns:
            m = int(df[c].isna().sum())
            miss_rows.append([c, column_kind(df[c]) if True else '', m, fmt(100 * m / max(n_tot, 1), 1) + ' %'])
    s['text'].append(f"Le jeu de données compte {n_tot} lignes ; {ctx.get('n_used', n_tot)} observations complètes sont utilisées pour l'estimation.")
    if num:
        rows = _describe_numeric(df, num)
        _tbl(s, 'Variables quantitatives', ['Variable', 'n', 'Moyenne', 'Écart-type', 'Min', 'Q1', 'Médiane', 'Q3', 'Max', 'Asymétrie', 'Aplatissement'], rows)
        for c in num[:6]:
            x = pd.to_numeric(df[c], errors='coerce').dropna()
            if len(x) > 3:
                s['text'].append(_shape_sentence(c, x))
    for c in cat[:5]:
        vc = df[c].value_counts(dropna=True)
        tot = vc.sum()
        rows = [[str(k), int(v), fmt(100 * v / tot, 1) + ' %'] for k, v in vc.head(12).items()]
        _tbl(s, f'Répartition de « {c} »', ['Modalité', 'Effectif', 'Fréquence'], rows)
    _tbl(s, 'Valeurs manquantes', ['Variable', 'Type', 'Manquantes', 'Part'], miss_rows)
    if len(num) >= 2:
        corr = df[num].apply(pd.to_numeric, errors='coerce').corr()
        _tbl(s, 'Matrice de corrélation (Pearson)', [''] + list(corr.columns),
             [[i] + [fmt(v, 2) for v in corr.loc[i]] for i in corr.index])
        if target in corr.columns:
            tc = corr[target].drop(target).dropna().sort_values(key=lambda v: -v.abs())
            if len(tc):
                best = tc.index[0]
                s['text'].append(f"La variable la plus corrélée à « {target} » est « {best} » (r = {fmt(tc.iloc[0], 2)}). "
                                 "Une corrélation n'établit pas une causalité ; elle oriente l'analyse.")
    if entity_col and entity_col in df.columns:
        per = df.groupby(entity_col).size()
        s['text'].append(f"Panel : {per.shape[0]} unités, {int(per.min())} à {int(per.max())} observations par unité"
                         + (' (panel équilibré).' if per.min() == per.max() else ' (panel déséquilibré).'))
    sections.append(s)

    # ---------------- 3. graphiques
    g = _section('graphiques', 'Représentations graphiques')
    tnum = pd.to_numeric(df[target], errors='coerce').dropna() if target in num else None

    # histogramme + densité de la cible, QQ-plot
    if tnum is not None and len(tnum) > 5:
        fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
        ax[0].hist(tnum, bins=min(30, max(8, int(np.sqrt(len(tnum))))), color=STEEL, alpha=.85, edgecolor='white', density=True)
        try:
            xs = np.linspace(tnum.min(), tnum.max(), 200)
            ax[0].plot(xs, stats.gaussian_kde(tnum)(xs), color=GOLD, lw=2, label='Densité estimée')
            ax[0].legend(frameon=False)
        except Exception:
            pass
        ax[0].set_title(f'Histogramme de {target}'); ax[0].set_xlabel(target); ax[0].set_ylabel('Densité')
        stats.probplot(tnum, dist='norm', plot=ax[1])
        ax[1].get_lines()[0].set_markerfacecolor(STEEL); ax[1].get_lines()[0].set_markeredgecolor(STEEL); ax[1].get_lines()[0].set_markersize(4)
        ax[1].get_lines()[1].set_color(GOLD)
        ax[1].set_title(f'QQ-plot de {target} (loi normale)'); ax[1].set_xlabel('Quantiles théoriques'); ax[1].set_ylabel('Quantiles observés')
        fig.tight_layout()
        _chart(g, f'Distribution de {target}', fig)

    # histogrammes des variables explicatives numériques
    xn = [c for c in num if c != target][:6]
    if xn:
        n = len(xn); cols = min(3, n); rows_ = int(np.ceil(n / cols))
        fig, axes = plt.subplots(rows_, cols, figsize=(3.2 * cols, 2.6 * rows_), squeeze=False)
        for i, c in enumerate(xn):
            a = axes[i // cols][i % cols]
            a.hist(pd.to_numeric(df[c], errors='coerce').dropna(), bins=20, color=PALETTE[i % len(PALETTE)], edgecolor='white', alpha=.9)
            a.set_title(c); a.set_ylabel('Effectif')
        for j in range(n, rows_ * cols):
            axes[j // cols][j % cols].axis('off')
        fig.suptitle('Histogrammes des variables explicatives', color=NAVY, fontweight='bold', y=1.02)
        fig.tight_layout()
        _chart(g, 'Distribution des variables explicatives', fig)

    # boîtes à moustaches
    bx = num[:6]
    if bx:
        fig, ax = plt.subplots(figsize=(max(5, 1.4 * len(bx) + 2), 3.6))
        data = [(pd.to_numeric(df[c], errors='coerce').dropna() - pd.to_numeric(df[c], errors='coerce').mean()) /
                (pd.to_numeric(df[c], errors='coerce').std() or 1) for c in bx]
        bp = ax.boxplot(data, labels=bx, patch_artist=True, showfliers=True, flierprops=dict(marker='o', markersize=3, markerfacecolor=RED, markeredgecolor=RED))
        for i, p in enumerate(bp['boxes']):
            p.set_facecolor(PALETTE[i % len(PALETTE)]); p.set_alpha(.75)
        for m in bp['medians']:
            m.set_color('white'); m.set_linewidth(1.6)
        ax.set_title('Boîtes à moustaches (variables centrées-réduites)'); ax.set_ylabel('Écarts-types')
        plt.setp(ax.get_xticklabels(), rotation=20)
        fig.tight_layout()
        _chart(g, 'Boîtes à moustaches et valeurs atypiques', fig)

    # barres + secteurs pour variable qualitative
    qual = ([target] if (target in cat) else []) + [c for c in cat if c != target]
    if qual:
        c = qual[0]
        vc = df[c].value_counts().head(8)
        fig, ax = plt.subplots(1, 2, figsize=(9, 3.6), gridspec_kw={'width_ratios': [1.2, 1]})
        ax[0].bar([str(i) for i in vc.index], vc.values, color=[PALETTE[i % len(PALETTE)] for i in range(len(vc))])
        for i, v in enumerate(vc.values):
            ax[0].text(i, v, str(int(v)), ha='center', va='bottom', fontsize=8)
        ax[0].set_title(f'Diagramme en barres : {c}'); ax[0].set_ylabel('Effectif')
        plt.setp(ax[0].get_xticklabels(), rotation=20)
        ax[1].pie(vc.values, labels=[str(i) for i in vc.index], autopct='%1.0f%%', startangle=90,
                  colors=[PALETTE[i % len(PALETTE)] for i in range(len(vc))], wedgeprops=dict(edgecolor='white'),
                  textprops=dict(fontsize=8))
        ax[1].set_title(f'Diagramme circulaire : {c}')
        ax[1].grid(False)
        fig.tight_layout()
        _chart(g, f'Répartition de {c}', fig)
    elif num and tnum is not None:
        # à défaut de variable qualitative : barres des moyennes par quartile de la cible
        pass

    # nuages de points + droite de régression
    if tnum is not None:
        sc = [c for c in xn][:4]
        if sc:
            n = len(sc); cols = min(2, n); rows_ = int(np.ceil(n / cols))
            fig, axes = plt.subplots(rows_, cols, figsize=(4.6 * cols, 3.3 * rows_), squeeze=False)
            for i, c in enumerate(sc):
                a = axes[i // cols][i % cols]
                d = df[[c, target]].apply(pd.to_numeric, errors='coerce').dropna()
                if len(d) > 2000:
                    d = d.sample(2000, random_state=1)
                a.scatter(d[c], d[target], s=12, color=STEEL, alpha=.55)
                if len(d) > 3 and d[c].nunique() > 1:
                    lr = stats.linregress(d[c], d[target])
                    xs = np.linspace(d[c].min(), d[c].max(), 50)
                    a.plot(xs, lr.intercept + lr.slope * xs, color=GOLD, lw=2)
                    a.set_title(f'{target} selon {c}\npente = {fmt(lr.slope, 3)} ; r = {fmt(lr.rvalue, 2)} ; p {fmt_p(lr.pvalue)}', fontsize=9)
                a.set_xlabel(c); a.set_ylabel(target)
            for j in range(n, rows_ * cols):
                axes[j // cols][j % cols].axis('off')
            fig.tight_layout()
            _chart(g, 'Nuages de points et droites de régression simple', fig)

    # boîtes à moustaches de la cible par modalité
    if tnum is not None:
        cq = [c for c in cat if c != target][:1]
        if cq:
            c = cq[0]
            groups = [(str(k), pd.to_numeric(v[target], errors='coerce').dropna().values) for k, v in df.groupby(c)]
            groups = [(k, v) for k, v in groups if len(v) > 1][:10]
            if len(groups) >= 2:
                fig, ax = plt.subplots(figsize=(max(5, .9 * len(groups) + 2.5), 3.5))
                bp = ax.boxplot([v for _, v in groups], labels=[k for k, _ in groups], patch_artist=True,
                                flierprops=dict(marker='o', markersize=3, markerfacecolor=RED, markeredgecolor=RED))
                for i, p in enumerate(bp['boxes']):
                    p.set_facecolor(PALETTE[i % len(PALETTE)]); p.set_alpha(.75)
                for m in bp['medians']:
                    m.set_color('white')
                ax.set_title(f'{target} selon {c}'); ax.set_ylabel(target)
                plt.setp(ax.get_xticklabels(), rotation=20)
                fig.tight_layout()
                _chart(g, f'Comparaison de {target} entre les modalités de {c}', fig)
                try:
                    f_, p_ = stats.f_oneway(*[v for _, v in groups])
                    s['text'].append(f"L'analyse de variance de « {target} » selon « {c} » donne F = {fmt(f_, 2)} (p {fmt_p(p_)}) : "
                                     + ("les moyennes diffèrent significativement entre modalités." if p_ < .05 else "pas de différence significative des moyennes."))
                except Exception:
                    pass

    # cible binaire / multiclasse : taux selon une variable continue
    if kind in ('binary', 'multiclass') and target in df.columns:
        for c in xn[:1]:
            d = df[[c, target]].dropna()
            groups = [(str(k), pd.to_numeric(v[c], errors='coerce').dropna().values) for k, v in d.groupby(target)]
            groups = [(k, v) for k, v in groups if len(v) > 1][:8]
            if len(groups) >= 2:
                fig, ax = plt.subplots(figsize=(5.5, 3.4))
                bp = ax.boxplot([v for _, v in groups], labels=[k for k, _ in groups], patch_artist=True)
                for i, p in enumerate(bp['boxes']):
                    p.set_facecolor(PALETTE[i % len(PALETTE)]); p.set_alpha(.75)
                ax.set_title(f'{c} selon {target}'); ax.set_ylabel(c); ax.set_xlabel(target)
                fig.tight_layout()
                _chart(g, f'Profil de {c} selon les classes', fig)

    # carte de chaleur des corrélations
    if len(num) >= 3:
        corr = df[num].apply(pd.to_numeric, errors='coerce').corr()
        fig, ax = plt.subplots(figsize=(max(4.5, .8 * len(num) + 2), max(3.8, .7 * len(num) + 1.5)))
        im = ax.imshow(corr.values, cmap='RdBu_r', vmin=-1, vmax=1)
        ax.set_xticks(range(len(num))); ax.set_xticklabels(num, rotation=35, ha='right')
        ax.set_yticks(range(len(num))); ax.set_yticklabels(num)
        ax.grid(False)
        for i in range(len(num)):
            for j in range(len(num)):
                ax.text(j, i, fmt(corr.values[i, j], 2), ha='center', va='center', fontsize=8,
                        color='white' if abs(corr.values[i, j]) > .6 else '#1f2937')
        fig.colorbar(im, ax=ax, fraction=.046)
        ax.set_title('Matrice de corrélation')
        fig.tight_layout()
        _chart(g, 'Corrélations entre variables', fig)

    # série temporelle
    if structure == 'time_series':
        try:
            series, meta = prepare_series(df, target, time_col)
            idx = pd.DatetimeIndex(meta['dates']) if meta.get('dates') is not None and len(meta['dates']) == len(series) else series.index
            fig, ax = plt.subplots(2, 1, figsize=(9, 5.2), gridspec_kw={'height_ratios': [2, 1]})
            ax[0].plot(idx, series.values, color=NAVY, lw=1.4)
            if len(series) > 12:
                w = max(3, min(12, len(series) // 8))
                ax[0].plot(idx, series.rolling(w).mean().values, color=GOLD, lw=2, label=f'Moyenne mobile ({w})')
                ax[0].legend(frameon=False)
            ax[0].set_title(f'Évolution de {target}'); ax[0].set_ylabel(target)
            from statsmodels.graphics.tsaplots import plot_acf
            plot_acf(series.dropna(), lags=min(36, len(series) // 2 - 1), ax=ax[1], color=STEEL, vlines_kwargs={'colors': STEEL})
            ax[1].set_title('Autocorrélations'); ax[1].set_xlabel('Retard')
            fig.tight_layout()
            _chart(g, 'Série temporelle et autocorrélations', fig)
        except Exception:
            pass
    # panel
    if structure == 'panel' and entity_col and time_col and tnum is not None:
        try:
            d = df[[entity_col, time_col, target]].dropna()
            ents = d[entity_col].astype(str).unique()
            fig, ax = plt.subplots(figsize=(8, 3.8))
            for i, e in enumerate(ents[:10]):
                z = d[d[entity_col].astype(str) == e].sort_values(time_col)
                ax.plot(z[time_col], pd.to_numeric(z[target]), lw=1.4, color=PALETTE[i % len(PALETTE)], label=str(e))
            ax.set_title(f'{target} par unité'); ax.set_xlabel(time_col); ax.set_ylabel(target)
            if len(ents) <= 10:
                ax.legend(frameon=False, ncol=2, fontsize=8)
            fig.tight_layout()
            _chart(g, 'Trajectoires par unité', fig)
            m = d.groupby(entity_col)[target].mean().sort_values(ascending=False).head(12)
            fig, ax = plt.subplots(figsize=(7, 3.4))
            ax.bar(m.index.astype(str), m.values, color=STEEL)
            ax.set_title(f'Moyenne de {target} par unité'); plt.setp(ax.get_xticklabels(), rotation=25)
            fig.tight_layout()
            _chart(g, 'Hétérogénéité entre unités', fig)
        except Exception:
            pass
    g['text'].append("Les graphiques ci-dessous aident à repérer la forme des distributions, les valeurs atypiques et la nature des relations "
                     "avant toute estimation.")
    sections.append(g)

    # ---------------- 4. tests préliminaires
    p = _section('preliminaires', 'Tests préliminaires')
    rows = []
    if tnum is not None and len(tnum) >= 8:
        x = tnum.values
        try:
            if len(x) <= 5000:
                w, pv = stats.shapiro(x)
                rows.append([f'Normalité de {target}', 'Shapiro-Wilk', fmt(w, 4), fmt_p(pv), 'Rejet de la normalité' if pv < .05 else 'Normalité non rejetée'])
            jb, pv = stats.jarque_bera(x)
            rows.append([f'Normalité de {target}', 'Jarque-Bera', fmt(jb, 3), fmt_p(pv), 'Rejet de la normalité' if pv < .05 else 'Normalité non rejetée'])
        except Exception:
            pass
        q1, q3 = np.percentile(x, [25, 75])
        iqr = q3 - q1
        out = int(((x < q1 - 1.5 * iqr) | (x > q3 + 1.5 * iqr)).sum())
        rows.append([f'Valeurs atypiques de {target}', 'Règle de Tukey (1,5 × IQR)', f'{out} valeur(s)', '—',
                     f'{fmt(100 * out / len(x), 1)} % des observations' + (' : à examiner' if out / len(x) > .05 else '')])
    # tests de la régression linéaire
    if kind == 'continuous' and features and structure != 'time_series':
        try:
            import statsmodels.api as sm
            from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset
            from statsmodels.stats.stattools import durbin_watson
            from statsmodels.stats.outliers_influence import variance_inflation_factor
            X, y, notes, _ = prepare_xy(df, target, features)
            Xc = sm.add_constant(X, has_constant='add')
            res = sm.OLS(y, Xc).fit()
            bp = het_breuschpagan(res.resid, Xc)
            rows.append(['Hétéroscédasticité', 'Breusch-Pagan', fmt(bp[0], 3), fmt_p(bp[1]), 'Variance non constante : erreurs robustes conseillées' if bp[1] < .05 else 'Variance constante acceptable'])
            jb, pv = stats.jarque_bera(res.resid)
            rows.append(['Normalité des résidus MCO', 'Jarque-Bera', fmt(jb, 3), fmt_p(pv), 'Résidus non normaux' if pv < .05 else 'Normalité non rejetée'])
            try:
                rs = linear_reset(res, power=2, use_f=True)
                rows.append(['Forme fonctionnelle', 'RESET de Ramsey', fmt(float(rs.fvalue), 3), fmt_p(float(rs.pvalue)), 'Spécification linéaire possiblement insuffisante' if rs.pvalue < .05 else 'Spécification linéaire acceptable'])
            except Exception:
                pass
            dw = durbin_watson(res.resid)
            rows.append(['Autocorrélation des résidus', 'Durbin-Watson', fmt(dw, 2), '—', 'Proche de 2 : pas d\'autocorrélation' if 1.5 < dw < 2.5 else 'Autocorrélation possible (surtout si ordre chronologique)'])
            if X.shape[1] >= 2:
                vifs = [(c, variance_inflation_factor(Xc.values, i + 1)) for i, c in enumerate(X.columns)]
                vmax = max(vifs, key=lambda t: t[1])
                rows.append(['Multicolinéarité', 'VIF maximal', f'{fmt(vmax[1], 2)} ({vmax[0]})', '—',
                             'Forte colinéarité (VIF > 10)' if vmax[1] > 10 else ('Colinéarité modérée (VIF > 5)' if vmax[1] > 5 else 'Pas de colinéarité préoccupante')])
        except Exception:
            pass
    # indépendance entre cible qualitative et explicatives
    if kind in ('binary', 'multiclass'):
        vc = df[target].value_counts(normalize=True)
        rows.append(['Équilibre des classes', 'Part de la classe minoritaire', fmt(100 * vc.min(), 1) + ' %', '—',
                     'Déséquilibre marqué : privilégier AUC / F1' if vc.min() < .2 else 'Classes équilibrées'])
        for c in xn[:4]:
            try:
                d = df[[c, target]].dropna()
                groups = [pd.to_numeric(v[c], errors='coerce').dropna().values for _, v in d.groupby(target)]
                groups = [v for v in groups if len(v) > 1]
                if len(groups) == 2:
                    t, pv = stats.ttest_ind(groups[0], groups[1], equal_var=False)
                    rows.append([f'{c} selon les classes', 'Test t de Welch', fmt(t, 3), fmt_p(pv), 'Moyennes différentes' if pv < .05 else 'Pas de différence nette'])
                elif len(groups) > 2:
                    f_, pv = stats.f_oneway(*groups)
                    rows.append([f'{c} selon les classes', 'ANOVA', fmt(f_, 3), fmt_p(pv), 'Moyennes différentes' if pv < .05 else 'Pas de différence nette'])
            except Exception:
                pass
    # séries temporelles
    if structure == 'time_series':
        try:
            series, meta = prepare_series(df, target, time_col)
            st = stationarity(series)
            rows.append(['Stationnarité', 'ADF (H0 : racine unitaire)', '—', fmt_p(st['adf_p']), 'Stationnaire' if (st['adf_p'] is not None and st['adf_p'] < .05) else 'Racine unitaire non rejetée'])
            rows.append(['Stationnarité', 'KPSS (H0 : stationnarité)', '—', fmt_p(st['kpss_p']), 'Stationnarité rejetée' if (st['kpss_p'] is not None and st['kpss_p'] < .05) else 'Stationnarité non rejetée'])
            rows.append(['Ordre d\'intégration conseillé', 'ADF + KPSS', f"d = {st['d']}", '—', 'Série à différencier' if st['d'] > 0 else 'Pas de différenciation nécessaire'])
            from statsmodels.stats.diagnostic import acorr_ljungbox
            lb = acorr_ljungbox(series.dropna(), lags=[10], return_df=True)
            rows.append(['Autocorrélation', 'Ljung-Box (10 retards)', fmt(lb['lb_stat'].iloc[0], 2), fmt_p(lb['lb_pvalue'].iloc[0]), 'Dépendance temporelle présente' if lb['lb_pvalue'].iloc[0] < .05 else 'Peu de dépendance temporelle'])
            ap = arch_effect(series.diff().dropna() if st['d'] else series)
            if ap is not None:
                rows.append(['Hétéroscédasticité conditionnelle', 'ARCH-LM', '—', fmt_p(ap), 'Effets ARCH : volatilité variable' if ap < .05 else 'Pas d\'effet ARCH net'])
            per = meta.get('period')
            if per:
                sea, force = detect_seasonality(series.diff().dropna() if st['d'] else series, [per])
                rows.append(['Saisonnalité', f'Autocorrélation au retard {per}', fmt(force, 2) if sea else '—', '—', 'Saisonnalité détectée' if sea else 'Pas de saisonnalité nette'])
        except Exception:
            pass
    # panel
    if structure == 'panel' and entity_col and time_col and kind == 'continuous':
        try:
            from models.runners import hausman_test
            h = hausman_test(df, target, features, entity_col, time_col)
            if isinstance(h, dict):
                rows.append(['Effets individuels corrélés aux variables', h['method'], fmt(h['stat'], 3), fmt_p(h['p']),
                             'Effets fixes préférables' if h['p'] < .05 else 'Effets aléatoires acceptables'])
        except Exception:
            pass
    if rows:
        _tbl(p, 'Résultats des tests préliminaires', ['Propriété testée', 'Test', 'Statistique', 'p-value', 'Lecture'], rows)
        reject = sum(1 for r in rows if ('non constante' in r[4] or 'non normaux' in r[4] or 'Rejet' in r[4] or 'Forte' in r[4]
                                         or 'possiblement' in r[4] or 'Déséquilibre' in r[4]))
        p['text'].append("Ces tests ne conditionnent pas l'estimation : ils servent à choisir les erreurs standard, les transformations et les modèles les plus "
                         "appropriés. Chaque signal d'alerte est repris dans l'analyse de robustesse." if reject else
                         "Aucun signal d'alerte majeur n'est détecté par ces tests préliminaires.")
    else:
        p['text'].append("Aucun test préliminaire n'a pu être calculé sur ces données.")
    sections.append(p)
    return {'sections': sections, 'context': ctx_text, 'problem': prob_text}


# ----------------------------------------------------------------------------------------------
def build_conclusion(results, ctx, target):
    """Synthèse automatique : meilleurs modèles, robustesse et limites."""
    sec = _section('conclusion', 'Conclusion, limites et recommandations')
    ok = [r for r in results if r.get('status') == 'ok']
    if not ok:
        sec['text'].append("Aucun modèle n'a pu être estimé : vérifiez la qualité des données et le choix des variables.")
        return sec
    rows = []
    for r in sorted(ok, key=lambda x: -x.get('score', 0)):
        rob = r.get('robustness') or {}
        rows.append([r['name'], r.get('family_label', ''), f"{r.get('score', '—')} / 100", rob.get('verdict') or '—'])
    _tbl(sec, 'Synthèse des modèles', ['Modèle', 'Famille', 'Score de recommandation', 'Robustesse'], rows)
    best = max(ok, key=lambda x: x.get('score', 0))
    sec['text'].append(f"Parmi les modèles estimés, « {best['name']} » obtient le meilleur score d'adéquation aux données ({best.get('score', '—')} / 100).")
    robust = [r['name'] for r in ok if (r.get('robustness') or {}).get('verdict') == 'Robuste']
    fragile = [r['name'] for r in ok if (r.get('robustness') or {}).get('verdict') == 'Fragile']
    if robust:
        sec['text'].append('Résultats robustes aux tests : ' + ', '.join(robust) + '.')
    if fragile:
        sec['text'].append('Résultats fragiles, à interpréter avec prudence : ' + ', '.join(fragile) + '.')
    for r in ok:
        for chk in (r.get('robustness') or {}).get('checks', []):
            if not chk['ok']:
                sec['text'].append(f"Point d'attention ({r['name']}) : {chk['label'].lower()} ({chk['detail']}).")
                break
    sec['text'].append("Limites : les résultats reposent sur les données fournies et sur les hypothèses propres à chaque modèle. Les associations statistiques "
                       "ne valent pas preuve de causalité ; une validation par un expert du domaine et, si possible, sur de nouvelles données reste indispensable.")
    if ctx.get('structure') == 'time_series':
        sec['text'].append("Les prévisions s'accompagnent d'une incertitude qui croît avec l'horizon ; elles supposent que la dynamique passée se prolonge.")
    return sec
