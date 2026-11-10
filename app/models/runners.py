#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exécution des modèles : régression, panel, séries temporelles, volatilité,
classification, machine learning et deep learning (perceptron multicouche).

Chaque fonction renvoie un dictionnaire standardisé (voir Res) affiché par la page de résultats
et utilisé pour générer les rapports Word et LaTeX.
"""

import base64
import io
import itertools
import traceback
import warnings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from models.analysis import (prepare_series, prepare_xy, stationarity, detect_seasonality,
                             volatility_input, arch_effect, _is_datetime_like)

warnings.filterwarnings('ignore')

NAVY, STEEL, GOLD, GREY, RED, GREEN = '#0b2a4a', '#1f5f99', '#c2a15a', '#8a94a3', '#a23b3b', '#2e7d5b'
plt.rcParams.update({
    'font.size': 9, 'axes.edgecolor': '#c9d1dc', 'axes.labelcolor': '#334155', 'axes.titleweight': 'bold',
    'axes.titlecolor': NAVY, 'xtick.color': '#475569', 'ytick.color': '#475569', 'axes.spines.top': False,
    'axes.spines.right': False, 'axes.grid': True, 'grid.color': '#e8edf3', 'grid.linewidth': .8,
    'figure.facecolor': 'white', 'axes.facecolor': 'white',
})


# ----------------------------------------------------------------------------
# Outils communs
# ----------------------------------------------------------------------------
def fmt(x, d=4):
    if x is None:
        return '—'
    try:
        if isinstance(x, (int, np.integer)):
            return f'{int(x):,}'.replace(',', ' ')
        x = float(x)
    except Exception:
        return str(x)
    if not np.isfinite(x):
        return '—'
    if abs(x) >= 1e7 or (0 < abs(x) < 1e-4):
        return f'{x:.3e}'
    return f'{x:,.{d}f}'.replace(',', ' ').replace('.', ',')


def fmt_p(p):
    if p is None or not np.isfinite(p):
        return '—'
    return '< 0,001' if p < 0.001 else f'{p:.3f}'.replace('.', ',')


def stars(p):
    if p is None or not np.isfinite(p):
        return ''
    return '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else ''))


def to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=110, bbox_inches='tight')
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


class Res:
    def __init__(self, mid, family, name):
        self.d = {'id': mid, 'family': family, 'name': name, 'status': 'ok', 'metrics': [], 'tables': [],
                  'charts': [], 'interpretation': [], 'warnings': [], 'raw': {}}

    def metric(self, key, label, value, digits=4, hint=''):
        raw = None
        try:
            raw = float(value) if value is not None else None
        except Exception:
            raw = None
        self.d['metrics'].append({'key': key, 'label': label, 'value': fmt(value, digits) if not isinstance(value, str) else value,
                                  'raw': raw, 'hint': hint})
        if raw is not None and np.isfinite(raw):
            self.d['raw'][key] = raw

    def table(self, title, columns, rows):
        self.d['tables'].append({'title': title, 'columns': columns, 'rows': [[str(c) for c in r] for r in rows]})

    def chart(self, title, fig):
        self.d['charts'].append({'title': title, 'img': to_b64(fig)})

    def say(self, t):
        self.d['interpretation'].append(t)

    def warn(self, t):
        if t and t not in self.d['warnings']:
            self.d['warnings'].append(t)


def error_result(mid, family, name, exc):
    traceback.print_exc()
    r = Res(mid, family, name)
    r.d['status'] = 'error'
    r.d['error'] = f"Ce modèle n'a pas pu être estimé sur ces données : {exc}"
    return r.d


def _split(X, y, test=0.2, stratify=None, seed=42):
    from sklearn.model_selection import train_test_split
    return train_test_split(X, y, test_size=test, random_state=seed, stratify=stratify)


def _coef_rows(params, se, pv, ci=None, extra=None):
    rows = []
    for name in params.index:
        row = [name, fmt(params[name]), fmt(se[name]) if se is not None else '—',
               fmt_p(pv[name]) + ' ' + stars(pv[name]) if pv is not None else '—']
        if ci is not None:
            row += [fmt(ci.loc[name, 0]), fmt(ci.loc[name, 1])]
        if extra is not None:
            row.append(fmt(extra[name]))
        rows.append(row)
    return rows


def _significance_sentences(res, params, pv, target, kind='coef'):
    out = []
    names = [n for n in params.index if n != 'const']
    sig = [n for n in names if pv[n] < 0.05]
    sig.sort(key=lambda n: pv[n])
    for n in sig[:6]:
        b = params[n]
        if kind == 'coef':
            out.append(f"« {n} » a un effet {'positif' if b > 0 else 'négatif'} et significatif (coefficient = {fmt(b, 3)}, p = {fmt_p(pv[n])}) : "
                       f"une hausse d'une unité de {n} est associée à une variation de {fmt(b, 3)} de {target}, toutes choses égales par ailleurs.")
        elif kind == 'odds':
            o = float(np.exp(b))
            out.append(f"« {n} » est significatif (p = {fmt_p(pv[n])}) : odds ratio = {fmt(o, 3)}, soit "
                       f"{'une hausse' if o > 1 else 'une baisse'} de {fmt(abs(o - 1) * 100, 1)} % des chances de la modalité positive pour une unité supplémentaire.")
        elif kind == 'irr':
            o = float(np.exp(b))
            out.append(f"« {n} » est significatif (p = {fmt_p(pv[n])}) : une unité de plus multiplie le nombre attendu de {target} par {fmt(o, 3)}.")
    ns = [n for n in names if pv[n] >= 0.05]
    if ns:
        out.append("Variables non significatives au seuil de 5 % : " + ", ".join(ns[:8]) + ('…' if len(ns) > 8 else '') + '.')
    if not sig:
        out.append("Aucune variable explicative n'est significative au seuil de 5 %.")
    return out


# ----------------------------------------------------------------------------
# Régression
# ----------------------------------------------------------------------------
def run_ols(df, target, features, **kw):
    import statsmodels.api as sm
    from statsmodels.stats.diagnostic import het_breuschpagan
    from statsmodels.stats.stattools import durbin_watson, jarque_bera
    r = Res('ols', 'regression', 'Régression linéaire (MCO)')
    X, y, notes, _ = prepare_xy(df, target, features)
    for t in notes:
        r.warn(t)
    if len(X) < X.shape[1] + 5:
        raise ValueError("Pas assez d'observations par rapport au nombre de variables.")
    Xc = sm.add_constant(X, has_constant='add')
    res = sm.OLS(y, Xc).fit(cov_type='HC3')
    ci = res.conf_int()
    r.metric('R2', 'R²', res.rsquared, hint='Part de variance expliquée')
    r.metric('R2adj', 'R² ajusté', res.rsquared_adj)
    r.metric('AIC', 'AIC', res.aic, 2)
    r.metric('BIC', 'BIC', res.bic, 2)
    r.metric('n', 'Observations', int(res.nobs))
    r.metric('Fp', 'p-value du test F', res.f_pvalue if res.f_pvalue is not None else None)
    r.table('Coefficients (erreurs standard robustes HC3)', ['Variable', 'Coefficient', 'Erreur std', 'p-value', 'IC 95 % bas', 'IC 95 % haut'],
            _coef_rows(res.params, res.bse, res.pvalues, pd.DataFrame(ci.values, index=ci.index)))
    try:
        bp = het_breuschpagan(res.resid, res.model.exog)[1]
        jb = jarque_bera(res.resid)[1]
        dw = durbin_watson(res.resid)
        r.table('Tests de diagnostic', ['Test', 'Statistique / p-value', 'Lecture'], [
            ['Breusch-Pagan (hétéroscédasticité)', fmt_p(bp), 'Variance non constante' if bp < 0.05 else 'Variance constante acceptable'],
            ['Jarque-Bera (normalité des résidus)', fmt_p(jb), 'Résidus non normaux' if jb < 0.05 else 'Normalité acceptable'],
            ['Durbin-Watson (autocorrélation)', fmt(dw, 2), 'Proche de 2 : pas d\'autocorrélation' if 1.5 < dw < 2.5 else 'Autocorrélation possible'],
        ])
        if bp < 0.05:
            r.warn("Hétéroscédasticité détectée : les erreurs standard robustes (HC3) sont utilisées.")
    except Exception:
        pass
    r.say(f"Le modèle explique {fmt(res.rsquared * 100, 1)} % de la variance de {target} (R² ajusté = {fmt(res.rsquared_adj, 3)}).")
    for s in _significance_sentences(res, res.params, res.pvalues, target):
        r.say(s)
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
    ax[0].scatter(res.fittedvalues, y, s=14, color=STEEL, alpha=.6)
    lo, hi = float(min(y.min(), res.fittedvalues.min())), float(max(y.max(), res.fittedvalues.max()))
    ax[0].plot([lo, hi], [lo, hi], color=GOLD, lw=1.6)
    ax[0].set_xlabel('Valeurs ajustées'); ax[0].set_ylabel('Valeurs observées'); ax[0].set_title('Observé et ajusté')
    ax[1].scatter(res.fittedvalues, res.resid, s=14, color=NAVY, alpha=.6)
    ax[1].axhline(0, color=GOLD, lw=1.4)
    ax[1].set_xlabel('Valeurs ajustées'); ax[1].set_ylabel('Résidus'); ax[1].set_title('Résidus')
    fig.tight_layout()
    r.chart('Qualité d\'ajustement', fig)
    return r.d


def _penalized(mid, name, est_factory, df, target, features, label_penalty):
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    r = Res(mid, 'regression', name)
    X, y, notes, _ = prepare_xy(df, target, features)
    for t in notes:
        r.warn(t)
    Xtr, Xte, ytr, yte = _split(X, y)
    sc = StandardScaler().fit(Xtr)
    est = est_factory()
    est.fit(sc.transform(Xtr), ytr)
    pred = est.predict(sc.transform(Xte))
    r2 = r2_score(yte, pred)
    r.metric('R2', 'R² (test)', r2)
    r.metric('RMSE', 'RMSE (test)', float(np.sqrt(mean_squared_error(yte, pred))))
    r.metric('MAE', 'MAE (test)', mean_absolute_error(yte, pred))
    r.metric('n', 'Observations', int(len(X)))
    alpha = getattr(est, 'alpha_', None)
    if alpha is not None:
        r.metric('alpha', f'Pénalisation choisie ({label_penalty})', float(alpha), 4)
    coefs = pd.Series(est.coef_, index=X.columns)
    r.table('Coefficients standardisés (variables centrées-réduites)', ['Variable', 'Coefficient'],
            [[k, fmt(v)] for k, v in coefs.reindex(coefs.abs().sort_values(ascending=False).index).items()])
    nz = int((coefs.abs() > 1e-8).sum())
    r.say(f"Sur l'échantillon de test, le modèle obtient un R² de {fmt(r2, 3)} et une erreur quadratique moyenne de {fmt(np.sqrt(mean_squared_error(yte, pred)), 3)}.")
    if mid in ('lasso', 'elasticnet'):
        r.say(f"{nz} variable(s) sur {len(coefs)} ont un coefficient non nul : les autres sont écartées par la pénalisation.")
    top = coefs.abs().sort_values(ascending=False).head(3).index.tolist()
    r.say("Variables les plus influentes (coefficient standardisé) : " + ", ".join(top) + '.')
    fig, ax = plt.subplots(figsize=(6.5, max(2.6, 0.32 * len(coefs) + 1)))
    c = coefs.reindex(coefs.abs().sort_values().index).tail(15)
    ax.barh(c.index, c.values, color=[STEEL if v >= 0 else RED for v in c.values])
    ax.set_title('Coefficients standardisés'); ax.axvline(0, color=GREY, lw=.8)
    fig.tight_layout()
    r.chart('Coefficients', fig)
    return r.d


def run_ridge(df, target, features, **kw):
    from sklearn.linear_model import RidgeCV
    return _penalized('ridge', 'Régression Ridge', lambda: RidgeCV(alphas=np.logspace(-3, 3, 30)), df, target, features, 'α')


def run_lasso(df, target, features, **kw):
    from sklearn.linear_model import LassoCV
    return _penalized('lasso', 'Régression Lasso', lambda: LassoCV(cv=5, random_state=42, max_iter=5000), df, target, features, 'α')


def run_elasticnet(df, target, features, **kw):
    from sklearn.linear_model import ElasticNetCV
    return _penalized('elasticnet', 'Elastic Net', lambda: ElasticNetCV(l1_ratio=[.2, .5, .8], cv=5, random_state=42, max_iter=5000), df, target, features, 'α')


def run_count(df, target, features, kind='poisson', **kw):
    import statsmodels.api as sm
    name = 'Régression de Poisson (comptage)' if kind == 'poisson' else 'Binomiale négative (comptage)'
    r = Res(kind, 'regression', name)
    X, y, notes, _ = prepare_xy(df, target, features)
    for t in notes:
        r.warn(t)
    if (y < 0).any():
        raise ValueError("La cible contient des valeurs négatives : modèle de comptage impossible.")
    Xc = sm.add_constant(X, has_constant='add')
    if kind == 'poisson':
        res = sm.GLM(y, Xc, family=sm.families.Poisson()).fit()
        over = float(res.pearson_chi2 / res.df_resid)
        r.metric('AIC', 'AIC', res.aic, 2)
        r.metric('over', 'Surdispersion (khi² de Pearson / ddl)', over, 2)
        if over > 1.5:
            r.warn("Surdispersion détectée (> 1,5) : préférez la binomiale négative.")
    else:
        res = sm.NegativeBinomial(y, Xc).fit(disp=0, maxiter=200)
        r.metric('AIC', 'AIC', res.aic, 2)
    r.metric('n', 'Observations', int(len(y)))
    pv = res.pvalues
    pr = res.params.drop('alpha', errors='ignore')
    ci = res.conf_int()
    rows = []
    for n_ in pr.index:
        rows.append([n_, fmt(pr[n_]), fmt(res.bse[n_]), fmt_p(pv[n_]) + ' ' + stars(pv[n_]), fmt(np.exp(pr[n_]))])
    r.table('Coefficients et rapports de taux d\'incidence (IRR = exp(coef))', ['Variable', 'Coefficient', 'Erreur std', 'p-value', 'IRR'], rows)
    for s in _significance_sentences(res, pr, pv, target, kind='irr'):
        r.say(s)
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    ax.scatter(res.fittedvalues if hasattr(res, 'fittedvalues') else res.predict(Xc), y, s=14, color=STEEL, alpha=.6)
    ax.set_xlabel('Comptage prédit'); ax.set_ylabel('Comptage observé'); ax.set_title('Observé et prédit')
    fig.tight_layout()
    r.chart('Observé et prédit', fig)
    return r.d


# ----------------------------------------------------------------------------
# Machine learning et deep learning (tabulaire)
# ----------------------------------------------------------------------------
def _reg_estimator(mid):
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.neural_network import MLPRegressor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVR
    from sklearn.tree import DecisionTreeRegressor
    return {
        'rf_reg': ('ml', 'Forêt aléatoire (régression)', lambda: RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=1)),
        'gb_reg': ('ml', 'Gradient Boosting (régression)', lambda: GradientBoostingRegressor(random_state=42)),
        'svr': ('ml', 'Machine à vecteurs de support (SVR)', lambda: make_pipeline(StandardScaler(), SVR(C=10))),
        'knn_reg': ('ml', 'k plus proches voisins (régression)', lambda: make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=7))),
        'tree_reg': ('ml', 'Arbre de décision (régression)', lambda: DecisionTreeRegressor(max_depth=6, random_state=42)),
        'mlp_reg': ('deep', 'Réseau de neurones (perceptron multicouche)', lambda: make_pipeline(
            StandardScaler(), MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=600, early_stopping=True, random_state=42))),
    }[mid]


def _importance(est, Xte, yte, cols, scoring):
    from sklearn.inspection import permutation_importance
    inner = est
    if hasattr(est, 'steps'):
        inner = est.steps[-1][1]
    if hasattr(inner, 'feature_importances_'):
        return pd.Series(inner.feature_importances_, index=cols), 'Importance (réduction d\'impureté)'
    sub = Xte.iloc[:500]
    ysub = yte.iloc[:500]
    pi = permutation_importance(est, sub, ysub, n_repeats=5, random_state=42, n_jobs=1, scoring=scoring)
    return pd.Series(pi.importances_mean, index=cols), 'Importance par permutation'


def _importance_chart(r, imp, label):
    imp = imp.sort_values().tail(12)
    fig, ax = plt.subplots(figsize=(6.5, max(2.6, .32 * len(imp) + 1)))
    ax.barh(imp.index, imp.values, color=STEEL)
    ax.set_title(label)
    fig.tight_layout()
    r.chart('Importance des variables', fig)


def run_sk_regressor(mid, df, target, features, **kw):
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import cross_val_score
    fam, name, factory = _reg_estimator(mid)
    r = Res(mid, fam, name)
    X, y, notes, _ = prepare_xy(df, target, features, max_rows=5000 if mid in ('svr', 'mlp_reg') else 20000)
    for t in notes:
        r.warn(t)
    if len(X) < 30:
        raise ValueError("Moins de 30 observations : estimation peu fiable.")
    Xtr, Xte, ytr, yte = _split(X, y)
    est = factory().fit(Xtr, ytr)
    pred = est.predict(Xte)
    r2 = r2_score(yte, pred)
    rmse = float(np.sqrt(mean_squared_error(yte, pred)))
    r.metric('R2', 'R² (test)', r2)
    r.metric('RMSE', 'RMSE (test)', rmse)
    r.metric('MAE', 'MAE (test)', mean_absolute_error(yte, pred))
    try:
        cv = cross_val_score(factory(), X, y, cv=5, scoring='r2')
        r.metric('R2cv', 'R² (validation croisée 5 blocs)', float(cv.mean()), 4, f"± {cv.std():.3f}")
    except Exception:
        pass
    r.metric('n', 'Observations', int(len(X)))
    r.say(f"Sur 20 % d'observations mises de côté, le modèle explique {fmt(r2 * 100, 1)} % de la variance de {target} (RMSE = {fmt(rmse, 3)}).")
    if r2 < 0.2:
        r.warn("Pouvoir prédictif faible : les variables retenues expliquent peu la cible.")
    if mid == 'mlp_reg' and len(X) < 300:
        r.warn("Échantillon petit pour un réseau de neurones : risque de surapprentissage.")
    imp, lab = _importance(est, Xte, yte, X.columns, 'r2')
    top = imp.sort_values(ascending=False).head(3)
    r.say("Variables les plus influentes : " + ", ".join(top.index) + '.')
    r.table('Importance des variables', ['Variable', 'Importance'], [[k, fmt(v)] for k, v in imp.sort_values(ascending=False).head(15).items()])
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.5))
    ax[0].scatter(yte, pred, s=14, color=STEEL, alpha=.6)
    lo, hi = float(min(yte.min(), pred.min())), float(max(yte.max(), pred.max()))
    ax[0].plot([lo, hi], [lo, hi], color=GOLD, lw=1.6)
    ax[0].set_xlabel('Observé'); ax[0].set_ylabel('Prédit'); ax[0].set_title('Prédiction sur l\'échantillon test')
    s = imp.sort_values().tail(10)
    ax[1].barh(s.index, s.values, color=STEEL); ax[1].set_title(lab)
    fig.tight_layout()
    r.chart('Prédiction et importance', fig)
    return r.d


def _clf_estimator(mid, imbalance):
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import GaussianNB
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC
    from sklearn.tree import DecisionTreeClassifier
    cw = 'balanced' if imbalance > 4 else None
    return {
        'mlogit': ('classification', 'Régression logistique multinomiale', lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight=cw))),
        'rf_clf': ('ml', 'Forêt aléatoire (classification)', lambda: RandomForestClassifier(n_estimators=200, max_depth=12, class_weight=cw, random_state=42, n_jobs=1)),
        'gb_clf': ('ml', 'Gradient Boosting (classification)', lambda: GradientBoostingClassifier(random_state=42)),
        'svm_clf': ('ml', 'Machine à vecteurs de support (SVM)', lambda: make_pipeline(StandardScaler(), SVC(C=3, probability=True, class_weight=cw, random_state=42))),
        'knn_clf': ('ml', 'k plus proches voisins', lambda: make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=7))),
        'tree_clf': ('ml', 'Arbre de décision', lambda: DecisionTreeClassifier(max_depth=5, class_weight=cw, random_state=42)),
        'nb_clf': ('ml', 'Naive Bayes', lambda: GaussianNB()),
        'mlp_clf': ('deep', 'Réseau de neurones (perceptron multicouche)', lambda: make_pipeline(
            StandardScaler(), MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=600, early_stopping=True, random_state=42))),
    }[mid]


def _classification_report(r, y_true, pred, proba, classes, binary):
    from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_score,
                                 recall_score, roc_auc_score, roc_curve)
    acc = accuracy_score(y_true, pred)
    avg = 'binary' if binary else 'weighted'
    pos = 1 if binary else None
    kw = {'average': avg, 'zero_division': 0}
    if binary:
        kw['pos_label'] = 1
    r.metric('Accuracy', 'Exactitude (test)', acc)
    r.metric('Precision', 'Précision', precision_score(y_true, pred, **kw))
    r.metric('Recall', 'Rappel', recall_score(y_true, pred, **kw))
    r.metric('F1', 'F1-score', f1_score(y_true, pred, **kw))
    auc = None
    if proba is not None:
        try:
            if binary:
                auc = roc_auc_score(y_true, proba[:, 1])
            else:
                auc = roc_auc_score(y_true, proba, multi_class='ovr', average='weighted', labels=list(range(len(classes))))
            r.metric('AUC', 'AUC', auc)
        except Exception:
            auc = None
    cm = confusion_matrix(y_true, pred, labels=list(range(len(classes))))
    r.table('Matrice de confusion (lignes : réel, colonnes : prédit)', ['Réel \\ Prédit'] + [str(c) for c in classes],
            [[str(classes[i])] + [int(v) for v in cm[i]] for i in range(len(classes))])
    base = max(np.bincount(np.asarray(y_true, dtype=int))) / len(y_true)
    r.say(f"Le modèle classe correctement {fmt(acc * 100, 1)} % des observations test (référence « toujours la classe majoritaire » : {fmt(base * 100, 1)} %).")
    if acc <= base + 0.02:
        r.warn("L'exactitude ne dépasse pas la classe majoritaire : le modèle apporte peu d'information.")
    if auc is not None:
        qual = 'excellent' if auc >= .9 else ('bon' if auc >= .8 else ('moyen' if auc >= .7 else 'faible'))
        r.say(f"L'AUC de {fmt(auc, 3)} indique un pouvoir discriminant {qual}.")
    figs = 2 if (binary and proba is not None) else 1
    fig, ax = plt.subplots(1, figs, figsize=(4.6 * figs, 3.6))
    ax = np.atleast_1d(ax)
    ax[0].imshow(cm, cmap='Blues')
    ax[0].set_xticks(range(len(classes))); ax[0].set_yticks(range(len(classes)))
    ax[0].set_xticklabels([str(c) for c in classes], rotation=30); ax[0].set_yticklabels([str(c) for c in classes])
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax[0].text(j, i, int(cm[i, j]), ha='center', va='center', color='white' if cm[i, j] > cm.max() / 2 else NAVY)
    ax[0].set_title('Matrice de confusion'); ax[0].grid(False)
    if figs == 2:
        fpr, tpr, _ = roc_curve(y_true, proba[:, 1])
        ax[1].plot(fpr, tpr, color=STEEL, lw=2, label=f'AUC = {auc:.3f}' if auc is not None else '')
        ax[1].plot([0, 1], [0, 1], color=GREY, ls='--')
        ax[1].set_xlabel('Faux positifs'); ax[1].set_ylabel('Vrais positifs'); ax[1].set_title('Courbe ROC'); ax[1].legend(loc='lower right')
    fig.tight_layout()
    r.chart('Performance de classification', fig)


def _clf_data(df, target, features):
    from sklearn.preprocessing import LabelEncoder
    X, y, notes, _ = prepare_xy(df, target, features, max_rows=20000)
    le = LabelEncoder()
    yy = pd.Series(le.fit_transform(y.astype(str)), index=y.index)
    classes = list(le.classes_)
    if len(classes) == 2 and set(classes) <= {'0', '1', '0.0', '1.0', 'False', 'True'}:
        pass
    return X, yy, classes, notes


def run_logit(df, target, features, **kw):
    import statsmodels.api as sm
    r = Res('logit', 'classification', 'Régression logistique (Logit)')
    X, y, classes, notes = _clf_data(df, target, features)
    for t in notes:
        r.warn(t)
    if len(classes) != 2:
        raise ValueError("Le Logit binaire nécessite exactement deux modalités.")
    r.warn(f"Modalité positive (1) : « {classes[1]} » ; référence (0) : « {classes[0]} ».")
    Xtr, Xte, ytr, yte = _split(X, y, stratify=y)
    Xc = sm.add_constant(Xtr, has_constant='add')
    try:
        res = sm.Logit(ytr, Xc).fit(disp=0, maxiter=200)
        pr = res.params; pv = res.pvalues; se = res.bse
        proba1 = res.predict(sm.add_constant(Xte, has_constant='add')).values
        r.metric('AIC', 'AIC', res.aic, 2)
        r.metric('PseudoR2', 'Pseudo-R² de McFadden', res.prsquared)
        rows = [[k, fmt(pr[k]), fmt(se[k]), fmt_p(pv[k]) + ' ' + stars(pv[k]), fmt(np.exp(pr[k]))] for k in pr.index]
        r.table('Coefficients et odds ratios', ['Variable', 'Coefficient', 'Erreur std', 'p-value', 'Odds ratio'], rows)
        for s in _significance_sentences(res, pr, pv, target, kind='odds'):
            r.say(s)
    except Exception as e:
        from sklearn.linear_model import LogisticRegression
        r.warn(f"Estimation statsmodels impossible ({e}) : régression logistique pénalisée utilisée.")
        lr = LogisticRegression(max_iter=1000).fit(Xtr, ytr)
        proba1 = lr.predict_proba(Xte)[:, 1]
    pred = (proba1 >= 0.5).astype(int)
    proba = np.column_stack([1 - proba1, proba1])
    r.metric('n', 'Observations', int(len(X)))
    _classification_report(r, yte, pred, proba, classes, True)
    return r.d


def run_sk_classifier(mid, df, target, features, **kw):
    from sklearn.model_selection import cross_val_score
    X, y, classes, notes = _clf_data(df, target, features)
    imb = float(y.value_counts().max() / max(y.value_counts().min(), 1))
    fam, name, factory = _clf_estimator(mid, imb)
    r = Res(mid, fam, name)
    for t in notes:
        r.warn(t)
    if mid in ('svm_clf', 'mlp_clf') and len(X) > 5000:
        idx = np.random.RandomState(42).choice(len(X), 5000, replace=False)
        X, y = X.iloc[idx], y.iloc[idx]
        r.warn("Échantillon limité à 5 000 observations pour ce modèle.")
    if len(X) < 30:
        raise ValueError("Moins de 30 observations : estimation peu fiable.")
    binary = len(classes) == 2
    r.warn(f"Classes : {', '.join(str(c) for c in classes)}.")
    strat = y if y.value_counts().min() >= 2 else None
    Xtr, Xte, ytr, yte = _split(X, y, stratify=strat)
    est = factory().fit(Xtr, ytr)
    pred = est.predict(Xte)
    proba = est.predict_proba(Xte) if hasattr(est, 'predict_proba') else None
    r.metric('n', 'Observations', int(len(X)))
    _classification_report(r, yte, pred, proba, classes, binary)
    try:
        cv = cross_val_score(factory(), X, y, cv=min(5, int(y.value_counts().min())) if y.value_counts().min() >= 2 else 3, scoring='accuracy')
        r.metric('Acccv', 'Exactitude (validation croisée)', float(cv.mean()), 4, f"± {cv.std():.3f}")
    except Exception:
        pass
    if mid == 'mlp_clf' and len(X) < 300:
        r.warn("Échantillon petit pour un réseau de neurones : risque de surapprentissage.")
    try:
        imp, lab = _importance(est, Xte, yte, X.columns, 'accuracy')
        r.say("Variables les plus influentes : " + ", ".join(imp.sort_values(ascending=False).head(3).index) + '.')
        r.table('Importance des variables', ['Variable', 'Importance'], [[k, fmt(v)] for k, v in imp.sort_values(ascending=False).head(15).items()])
        _importance_chart(r, imp, lab)
    except Exception:
        pass
    return r.d


# ----------------------------------------------------------------------------
# Panel
# ----------------------------------------------------------------------------
def _panel_frame(df, target, features, entity_col, time_col):
    X, y, notes, d = prepare_xy(df, target, features, max_rows=10 ** 9, keep_index=True, extra_cols=[entity_col, time_col])
    ent = d.loc[X.index, entity_col]
    t = d.loc[X.index, time_col]
    if _is_datetime_like(t):
        t = pd.to_datetime(t, errors='coerce')
    else:
        tn = pd.to_numeric(t, errors='coerce')
        t = tn if tn.notna().all() else pd.Series(pd.factorize(t)[0], index=t.index)
    idx = pd.MultiIndex.from_arrays([ent.astype(str).values, t.values], names=[entity_col, time_col])
    X = X.copy(); y = y.copy()
    X.index = idx; y.index = idx
    keep = ~idx.duplicated()
    return X[keep], y[keep], notes


def _fit_panel(df, target, features, entity_col, time_col, which, cov='clustered'):
    from linearmodels.panel import PanelOLS, PooledOLS, RandomEffects
    import statsmodels.api as sm
    X, y, notes = _panel_frame(df, target, features, entity_col, time_col)
    if which == 'fe':
        within_std = X.groupby(level=0).std().fillna(0).sum()
        invariant = [c for c in X.columns if within_std[c] == 0]
        if invariant:
            notes.append("Variables constantes dans le temps (absorbées par les effets fixes, retirées) : " + ", ".join(invariant))
            X = X.drop(columns=invariant)
        if X.shape[1] == 0:
            raise ValueError("Toutes les variables explicatives sont constantes dans le temps : effets fixes impossibles.")
        mod = PanelOLS(y, X, entity_effects=True)
    elif which == 're':
        mod = RandomEffects(y, sm.add_constant(X, has_constant='add'))
    else:
        mod = PooledOLS(y, sm.add_constant(X, has_constant='add'))
    if cov == 'clustered':
        res = mod.fit(cov_type='clustered', cluster_entity=True)
    else:
        res = mod.fit(cov_type='unadjusted')
    return res, notes, X, y


def hausman_test(df, target, features, entity_col, time_col):
    """Test de Hausman ; si la statistique classique est négative, test de Mundlak (robuste)."""
    from linearmodels.panel import RandomEffects
    import statsmodels.api as sm
    fe, _, X, y = _fit_panel(df, target, features, entity_col, time_col, 'fe', cov='unadjusted')
    re_, _, _, _ = _fit_panel(df, target, features, entity_col, time_col, 're', cov='unadjusted')
    common = [c for c in fe.params.index if c in re_.params.index and c != 'const']
    if not common:
        return None
    diff = (fe.params[common] - re_.params[common]).values
    cov = (fe.cov.loc[common, common] - re_.cov.loc[common, common]).values
    stat = float(diff @ np.linalg.pinv(cov) @ diff)
    if stat >= 0:
        return {'stat': stat, 'p': float(1 - stats.chi2.cdf(stat, len(common))), 'dof': len(common), 'method': 'Hausman'}
    # Mundlak : moyennes par entité ajoutées au modèle à effets aléatoires
    means = X[common].groupby(level=0).transform('mean')
    means.columns = [c + '__moy' for c in common]
    Xm = pd.concat([X, means], axis=1)
    res = RandomEffects(y, sm.add_constant(Xm, has_constant='add')).fit(cov_type='unadjusted')
    b = res.params[means.columns].values
    V = res.cov.loc[means.columns, means.columns].values
    st = float(b @ np.linalg.pinv(V) @ b)
    return {'stat': st, 'p': float(1 - stats.chi2.cdf(st, len(common))), 'dof': len(common), 'method': 'Mundlak (variante robuste du Hausman)'}


def run_panel(which, df, target, features, entity_col=None, time_col=None, **kw):
    names = {'pooled': 'Panel : MCO empilés (Pooled OLS)', 'fe': 'Panel : effets fixes (Within)', 're': 'Panel : effets aléatoires'}
    mid = {'pooled': 'panel_pooled', 'fe': 'panel_fe', 're': 'panel_re'}[which]
    r = Res(mid, 'panel', names[which])
    if not entity_col or not time_col:
        raise ValueError("Indiquez la colonne entité et la colonne temps.")
    res, notes, X, y = _fit_panel(df, target, features, entity_col, time_col, which)
    for t in notes:
        r.warn(t)
    r.metric('R2', 'R² (intra)' if which == 'fe' else 'R²', getattr(res, 'rsquared_within', res.rsquared) if which == 'fe' else res.rsquared)
    for k, lab in (('rsquared_within', 'R² intra (within)'), ('rsquared_between', 'R² inter (between)'), ('rsquared_overall', 'R² global')):
        v = getattr(res, k, None)
        if v is not None and np.isfinite(v):
            r.metric(k, lab, float(v))
    r.metric('n', 'Observations', int(res.nobs))
    try:
        r.metric('entities', 'Entités', int(res.entity_info['total']))
        r.metric('T', 'Périodes par entité (moyenne)', float(res.nobs / res.entity_info['total']), 1)
    except Exception:
        pass
    ci = res.conf_int()
    r.table('Coefficients (erreurs standard groupées par entité)', ['Variable', 'Coefficient', 'Erreur std', 'p-value', 'IC 95 % bas', 'IC 95 % haut'],
            _coef_rows(res.params, res.std_errors, res.pvalues, pd.DataFrame(ci.values, index=ci.index)))
    if which == 'fe':
        try:
            fp = res.f_pooled
            r.table('Test de significativité des effets individuels', ['Test', 'Statistique', 'p-value'], [['F (effets fixes = 0)', fmt(fp.stat, 3), fmt_p(fp.pval)]])
            r.say("Les effets individuels sont " + ("significatifs : l'hétérogénéité entre entités doit être prise en compte (le pooled OLS est rejeté)." if fp.pval < 0.05
                                                  else "non significatifs : le modèle empilé est acceptable."))
        except Exception:
            pass
        try:
            h = hausman_test(df, target, features, entity_col, time_col)
            if h and h['p'] is not None:
                r.table('Test de spécification (effets fixes contre aléatoires)', ['Test', 'Statistique', 'ddl', 'p-value'], [[h.get('method', 'Hausman'), fmt(h['stat'], 3), h['dof'], fmt_p(h['p'])]])
                r.say("Test de Hausman : " + ("les effets fixes sont préférables aux effets aléatoires." if h['p'] < 0.05
                                              else "on ne rejette pas la cohérence des effets aléatoires, plus efficaces."))
        except Exception:
            pass
    if which == 're':
        r.say("Les effets aléatoires supposent que les effets individuels ne sont pas corrélés aux variables explicatives (à vérifier avec le test de Hausman dans le modèle à effets fixes).")
    pv = res.pvalues
    for s in _significance_sentences(res, res.params, pv, target):
        r.say(s)
    p = res.params.drop('const', errors='ignore')
    e = res.std_errors.drop('const', errors='ignore')
    fig, ax = plt.subplots(figsize=(6.5, max(2.4, .38 * len(p) + 1)))
    ypos = np.arange(len(p))
    ax.errorbar(p.values, ypos, xerr=1.96 * e.values, fmt='o', color=STEEL, ecolor=GOLD, capsize=3)
    ax.axvline(0, color=GREY, lw=.8)
    ax.set_yticks(ypos); ax.set_yticklabels(p.index); ax.set_title('Coefficients et IC à 95 %')
    fig.tight_layout()
    r.chart('Coefficients', fig)
    return r.d


# ----------------------------------------------------------------------------
# Séries temporelles
# ----------------------------------------------------------------------------
def _ts_setup(df, target, time_col, features=None):
    series, meta = prepare_series(df, target, time_col)
    if len(series) < 20:
        raise ValueError("Série trop courte (moins de 20 observations).")
    st = stationarity(series)
    return series, meta, st


def _forecast_dates(series, meta, steps):
    last = series.index[-1]
    if isinstance(series.index, pd.DatetimeIndex) and series.index.freq is not None:
        return pd.date_range(start=last + series.index.freq, periods=steps, freq=series.index.freq)
    if meta.get('dates') is not None and meta.get('step') is not None:
        return pd.DatetimeIndex([meta['dates'][-1] + meta['step'] * (i + 1) for i in range(steps)])
    return pd.RangeIndex(len(series), len(series) + steps)


def _axis_index(series, meta):
    if meta.get('dates') is not None and len(meta['dates']) == len(series):
        return pd.DatetimeIndex(meta['dates'])
    return series.index


def _fit_sarimax(y, order, seasonal=(0, 0, 0, 0), exog=None):
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    mod = SARIMAX(y, exog=exog, order=order, seasonal_order=seasonal, enforce_stationarity=False, enforce_invertibility=False)
    return mod.fit(disp=False, maxiter=100)


def _search(y, d, kind, m=None, seasonal=False, exog=None, D=0):
    best = None
    if kind == 'ar':
        grid = [(p, d, 0) for p in range(1, 6)]
    elif kind == 'ma':
        grid = [(0, d, q) for q in range(1, 6)]
    elif kind == 'arma':
        grid = [(p, d, q) for p in range(0, 4) for q in range(0, 4) if p + q > 0]
    else:
        grid = [(p, d, q) for p in range(0, 4) for q in range(0, 4)]
    if seasonal and m:
        grid = [(p, d, q) for p in range(0, 3) for q in range(0, 3)]
        sgrid = [(P, D, Q, m) for P in range(0, 2) for Q in range(0, 2)]
    else:
        sgrid = [(0, 0, 0, 0)]
    for o in grid:
        for so in sgrid:
            try:
                res = _fit_sarimax(y, o, so, exog)
                if not np.isfinite(res.aic):
                    continue
                if best is None or res.aic < best[0]:
                    best = (res.aic, o, so)
            except Exception:
                continue
    if best is None:
        raise ValueError("Aucun ordre n'a pu être estimé.")
    return best[1], best[2]


def run_arima_family(kind, df, target, features, time_col=None, forecast_steps=12, **kw):
    names = {'ar': 'AR (autorégressif)', 'ma': 'MA (moyenne mobile)', 'arma': 'ARMA', 'arima': 'ARIMA',
             'sarima': 'SARIMA (saisonnier)', 'arimax': 'ARIMAX (avec variables explicatives)'}
    r = Res(kind, 'timeseries', names[kind])
    series, meta, st = _ts_setup(df, target, time_col)
    for t in meta['notes']:
        r.warn(t)
    exog = None
    exog_cols = []
    if kind == 'arimax':
        # alignement des variables exogènes sur la série
        Xe, ye, notes, dd = prepare_xy(df, target, features, max_rows=10 ** 9, keep_index=True, extra_cols=[time_col] if time_col else [])
        if len(Xe) != len(series):
            raise ValueError("Les variables explicatives doivent être renseignées sur toute la période (valeurs manquantes détectées).")
        order_idx = np.argsort(pd.to_numeric(dd[time_col], errors='coerce').values) if (time_col and not _is_datetime_like(dd[time_col])) else (
            np.argsort(pd.to_datetime(dd[time_col], errors='coerce').values) if time_col else np.arange(len(dd)))
        Xe = Xe.iloc[order_idx].reset_index(drop=True)
        exog_cols = list(Xe.columns)
        exog = Xe.values
        for t in notes:
            r.warn(t)
    y = series.copy()
    if len(y) > 600:
        y = y.iloc[-600:]
        if exog is not None:
            exog = exog[-600:]
        r.warn("Seules les 600 dernières observations sont utilisées.")
    d = st['d']
    per = None
    D = 0
    seasonal = kind == 'sarima'
    if seasonal:
        cands = [meta['period']] if meta['period'] else [4, 7, 12, 24, 52]
        per, force = detect_seasonality(y.diff(d).dropna().values if d else y.values, cands)
        per = per or meta['period']
        if not per:
            r.warn("Aucune période saisonnière claire : période 12 supposée par défaut." if len(y) >= 36 else "Aucune période saisonnière claire détectée.")
            per = 12 if len(y) >= 36 else None
        if not per or len(y) < 3 * per:
            raise ValueError("Série trop courte pour estimer un SARIMA saisonnier.")
        # une différenciation saisonnière si la saisonnalité reste forte après différenciation simple
        base = y.diff(d).dropna() if d else y
        p2, f2 = detect_seasonality(base.values, [per])
        D = 1 if (p2 and f2 > 0.4) else 0
    if kind in ('ar', 'ma', 'arma', 'arima', 'arimax', 'sarima'):
        order, sorder = _search(y, d, 'arima' if kind in ('arimax', 'sarima') else kind, m=per, seasonal=seasonal, exog=exog, D=D)
    # évaluation hors échantillon
    k = int(max(2, min(int(0.2 * len(y)), 24)))
    ytr, yte = y.iloc[:-k], y.iloc[-k:]
    ex_tr = exog[:-k] if exog is not None else None
    ex_te = exog[-k:] if exog is not None else None
    rmse = mae = mape = naive = None
    try:
        rt = _fit_sarimax(ytr, order, sorder, ex_tr)
        fc = rt.get_forecast(steps=k, exog=ex_te).predicted_mean
        fc = np.asarray(fc, dtype=float)
        err = yte.values - fc
        rmse = float(np.sqrt(np.mean(err ** 2)))
        mae = float(np.mean(np.abs(err)))
        nz = np.abs(yte.values) > 1e-9
        mape = float(np.mean(np.abs(err[nz] / yte.values[nz])) * 100) if nz.any() else None
        naive = float(np.sqrt(np.mean((yte.values - ytr.values[-1]) ** 2)))
    except Exception:
        fc = None
    res = _fit_sarimax(y, order, sorder, exog)
    spec = f"({order[0]}, {order[1]}, {order[2]})" + (f"({sorder[0]}, {sorder[1]}, {sorder[2]}){sorder[3]}" if sorder[3] else '')
    r.d['name'] = names[kind] + ' ' + spec if kind not in ('ar', 'ma', 'arma') else (names[kind].split(' ')[0] + ' ' + spec)
    r.metric('Spec', 'Spécification retenue', 'SARIMAX' + spec)
    r.metric('AIC', 'AIC', res.aic, 2)
    r.metric('BIC', 'BIC', res.bic, 2)
    if rmse is not None:
        r.metric('RMSE', 'RMSE (hors échantillon)', rmse, 4, f"Sur les {k} dernières observations")
        r.metric('MAE', 'MAE (hors échantillon)', mae)
        if mape is not None:
            r.metric('MAPE', 'MAPE (%)', mape, 2)
        if naive is not None:
            r.metric('RMSE_naif', 'RMSE prévision naïve', naive, 4, 'Dernière valeur répétée')
    r.metric('n', 'Observations', int(len(y)))
    # coefficients
    pr = res.params
    rows = [[n, fmt(pr[n]), fmt(res.bse[n]), fmt_p(res.pvalues[n]) + ' ' + stars(res.pvalues[n])] for n in pr.index if n != 'sigma2']
    if exog is not None:
        rename = {f'x{i + 1}': c for i, c in enumerate(exog_cols)}
        rows = [[rename.get(a[0], a[0])] + a[1:] for a in rows]
    r.table('Paramètres estimés', ['Paramètre', 'Valeur', 'Erreur std', 'p-value'], rows)
    unstable = [n for n in pr.index if 'ma.' in n and abs(pr[n]) > 0.98]
    if unstable:
        r.warn("Un paramètre de moyenne mobile est proche de -1 ou 1 (" + ", ".join(unstable) + ") : risque de sur-différenciation ; les erreurs standard de ces paramètres ne sont pas fiables. Comparez avec un autre ordre.")
    # diagnostics
    from statsmodels.stats.diagnostic import acorr_ljungbox
    resid = pd.Series(res.resid).iloc[max(d, 1) + (sorder[3] * sorder[1] if sorder[3] else 0):]
    try:
        lb = acorr_ljungbox(resid, lags=[min(10, len(resid) // 5)], return_df=True)['lb_pvalue'].iloc[0]
        jb = stats.jarque_bera(resid.dropna())[1]
        r.table('Diagnostic des résidus', ['Test', 'p-value', 'Lecture'], [
            ['Ljung-Box (autocorrélation)', fmt_p(lb), 'Résidus non corrélés (bon)' if lb > 0.05 else 'Autocorrélation résiduelle : modèle à enrichir'],
            ['Jarque-Bera (normalité)', fmt_p(jb), 'Normalité acceptable' if jb > 0.05 else 'Résidus non normaux'],
        ])
        if lb < 0.05:
            r.warn("Il reste de l'autocorrélation dans les résidus : essayez un autre ordre ou un modèle saisonnier.")
    except Exception:
        pass
    # tests de stationnarité
    r.table('Tests de stationnarité de la série', ['Test', 'p-value', 'Lecture'], [
        ['ADF (H0 : racine unitaire)', fmt_p(st['adf_p']), 'Stationnaire' if (st['adf_p'] or 1) < 0.05 else 'Non stationnaire'],
        ['KPSS (H0 : stationnarité)', fmt_p(st['kpss_p']), 'Stationnaire' if (st['kpss_p'] or 0) > 0.05 else 'Non stationnaire'],
    ])
    # prévision
    steps = int(forecast_steps)
    ex_f = None
    if exog is not None:
        ex_f = np.repeat(exog[-1:].astype(float), steps, axis=0)
        r.warn("Prévision ARIMAX : les variables explicatives sont supposées constantes à leur dernière valeur.")
    fres = res.get_forecast(steps=steps, exog=ex_f)
    mean = np.asarray(fres.predicted_mean, dtype=float)
    cint = np.asarray(fres.conf_int(), dtype=float)
    fdates = _forecast_dates(series, meta, steps)
    r.table(f'Prévisions sur {steps} périodes', ['Période', 'Prévision', 'IC 95 % bas', 'IC 95 % haut'],
            [[str(fdates[i].date()) if hasattr(fdates[i], 'date') else str(fdates[i]), fmt(mean[i]), fmt(cint[i, 0]), fmt(cint[i, 1])] for i in range(steps)])
    xs = _axis_index(series, meta)
    if len(xs) != len(y):
        xs = xs[-len(y):]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.plot(xs, y.values, color=NAVY, lw=1.6, label='Observé')
    if fc is not None:
        ax.plot(xs[-k:], fc, color=STEEL, lw=1.6, ls='--', label='Prévision test')
    ax.plot(fdates, mean, color=GOLD, lw=2, label='Prévision')
    ax.fill_between(fdates, cint[:, 0], cint[:, 1], color=GOLD, alpha=.2, label='IC 95 %')
    ax.set_title(f'{r.d["name"]}'); ax.legend(loc='best', fontsize=8)
    fig.autofmt_xdate() if isinstance(xs, pd.DatetimeIndex) else None
    fig.tight_layout()
    r.chart('Série, ajustement et prévisions', fig)
    # interprétation
    if d:
        r.say(f"La série n'est pas stationnaire : elle a été différenciée {d} fois (ADF p = {fmt_p(st['adf_p'])}).")
    else:
        r.say(f"La série est stationnaire (ADF p = {fmt_p(st['adf_p'])}) : aucune différenciation nécessaire.")
    r.say(f"Ordre retenu par minimisation de l'AIC : {spec}.")
    if rmse is not None and naive is not None:
        better = rmse < naive
        r.say(f"Hors échantillon, l'erreur (RMSE = {fmt(rmse, 3)}) est {'inférieure' if better else 'supérieure'} à celle d'une prévision naïve ({fmt(naive, 3)}) : "
              + ("le modèle apporte de l'information." if better else "le modèle n'améliore pas la prévision naïve."))
    r.say(f"À l'horizon {steps}, la prévision est de {fmt(mean[-1], 3)} (intervalle à 95 % : {fmt(cint[-1, 0], 3)} à {fmt(cint[-1, 1], 3)}).")
    if kind == 'arimax':
        pv = res.pvalues
        rename = {f'x{i + 1}': c for i, c in enumerate(exog_cols)}
        for i, c in enumerate(exog_cols):
            key = f'x{i + 1}'
            if key in pv.index and pv[key] < 0.05:
                r.say(f"La variable « {c} » est significative (p = {fmt_p(pv[key])}, coefficient = {fmt(res.params[key], 3)}).")
    return r.d


def run_holtwinters(df, target, features, time_col=None, forecast_steps=12, **kw):
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    r = Res('holtwinters', 'timeseries', 'Lissage exponentiel (Holt-Winters)')
    series, meta, st = _ts_setup(df, target, time_col)
    for t in meta['notes']:
        r.warn(t)
    y = series.iloc[-600:] if len(series) > 600 else series
    cands = [meta['period']] if meta['period'] else [4, 7, 12, 24, 52]
    per, _ = detect_seasonality(y.diff().dropna().values, cands)
    per = per or meta['period']
    use_seas = bool(per) and len(y) >= 2 * (per or 1) + 2
    positive = bool((y > 0).all())
    k = int(max(2, min(int(0.2 * len(y)), 24)))
    ytr, yte = y.iloc[:-k], y.iloc[-k:]

    def fit(v):
        kwargs = dict(trend='add', damped_trend=True, seasonal='mul' if (use_seas and positive) else ('add' if use_seas else None),
                      seasonal_periods=per if use_seas else None)
        return ExponentialSmoothing(v, **kwargs).fit(optimized=True)
    rt = fit(ytr)
    fc = np.asarray(rt.forecast(k), dtype=float)
    err = yte.values - fc
    rmse = float(np.sqrt(np.mean(err ** 2)))
    naive = float(np.sqrt(np.mean((yte.values - ytr.values[-1]) ** 2)))
    res = fit(y)
    steps = int(forecast_steps)
    mean = np.asarray(res.forecast(steps), dtype=float)
    fdates = _forecast_dates(series, meta, steps)
    r.metric('RMSE', 'RMSE (hors échantillon)', rmse, 4, f"Sur les {k} dernières observations")
    r.metric('MAE', 'MAE (hors échantillon)', float(np.mean(np.abs(err))))
    r.metric('RMSE_naif', 'RMSE prévision naïve', naive)
    r.metric('AIC', 'AIC', res.aic, 2)
    r.metric('n', 'Observations', int(len(y)))
    r.table('Paramètres de lissage', ['Paramètre', 'Valeur'], [['alpha (niveau)', fmt(res.params.get('smoothing_level'))],
                                                           ['beta (tendance)', fmt(res.params.get('smoothing_trend'))],
                                                           ['gamma (saisonnalité)', fmt(res.params.get('smoothing_seasonal'))]])
    r.table(f'Prévisions sur {steps} périodes', ['Période', 'Prévision'],
            [[str(fdates[i].date()) if hasattr(fdates[i], 'date') else str(fdates[i]), fmt(mean[i])] for i in range(steps)])
    xs = _axis_index(series, meta)[-len(y):]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.plot(xs, y.values, color=NAVY, lw=1.6, label='Observé')
    ax.plot(xs[-k:], fc, color=STEEL, ls='--', lw=1.6, label='Prévision test')
    ax.plot(fdates, mean, color=GOLD, lw=2, label='Prévision')
    ax.set_title('Holt-Winters'); ax.legend(fontsize=8)
    fig.tight_layout()
    r.chart('Série et prévisions', fig)
    r.say(f"Tendance amortie {'et saisonnalité ' + ('multiplicative' if positive else 'additive') + f' de période {per}' if use_seas else 'sans saisonnalité'}.")
    r.say(f"Hors échantillon, RMSE = {fmt(rmse, 3)} contre {fmt(naive, 3)} pour la prévision naïve : " + ("meilleur que la référence." if rmse < naive else "pas meilleur que la référence naïve."))
    r.say(f"Prévision à l'horizon {steps} : {fmt(mean[-1], 3)}.")
    return r.d


def run_var(df, target, features, time_col=None, forecast_steps=12, **kw):
    from statsmodels.tsa.api import VAR
    r = Res('var', 'timeseries', 'VAR + causalité de Granger')
    cols = [target] + [f for f in features if pd.api.types.is_numeric_dtype(df[f])][:4]
    if len(cols) < 2:
        raise ValueError("Le VAR nécessite au moins une variable explicative numérique.")
    d = df[cols + ([time_col] if time_col else [])].copy().dropna()
    if time_col:
        d = d.sort_values(time_col)
    data = d[cols].astype(float).reset_index(drop=True)
    diffd = False
    for c in cols:
        if len(data) >= 20 and not stationarity(data[c])['stationary']:
            diffd = True
    if diffd:
        data = data.diff().dropna().reset_index(drop=True)
        r.warn("Certaines séries sont non stationnaires : le VAR est estimé sur leurs différences premières.")
    if len(data) < 30:
        raise ValueError("Pas assez d'observations pour un VAR.")
    maxl = int(max(1, min(8, len(data) // (4 * len(cols)))))
    mod = VAR(data)
    sel = mod.fit(maxlags=maxl, ic='aic')
    lag = max(sel.k_ar, 1)
    res = mod.fit(lag)
    r.metric('Lags', 'Retards retenus (AIC)', lag, 0)
    r.metric('AIC', 'AIC', res.aic, 3)
    r.metric('BIC', 'BIC', res.bic, 3)
    r.metric('n', 'Observations', int(res.nobs))
    rows = []
    for c in cols[1:]:
        try:
            g = res.test_causality(target, [c], kind='f')
            rows.append([f'{c} → {target}', fmt(g.test_statistic, 3), fmt_p(g.pvalue), 'Cause au sens de Granger' if g.pvalue < 0.05 else 'Pas de causalité'])
        except Exception:
            continue
    r.table('Test de causalité de Granger', ['Relation', 'Statistique F', 'p-value', 'Lecture'], rows)
    for row in rows:
        if 'Cause' in row[3]:
            r.say(f"{row[0].split(' → ')[0]} aide à prédire {target} (Granger, p = {row[2]}).")
    if not any('Cause' in x[3] for x in rows):
        r.say("Aucune variable explicative ne cause {t} au sens de Granger au seuil de 5 %.".format(t=target))
    steps = int(forecast_steps)
    fc = res.forecast(data.values[-lag:], steps=steps)[:, 0]
    r.table(f'Prévision de {target} sur {steps} périodes' + (' (en variations)' if diffd else ''), ['Pas', 'Prévision'],
            [[i + 1, fmt(fc[i])] for i in range(steps)])
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(range(len(data)), data[target].values, color=NAVY, lw=1.4, label='Observé' + (' (différence)' if diffd else ''))
    ax.plot(range(len(data), len(data) + steps), fc, color=GOLD, lw=2, label='Prévision')
    ax.set_title(f'VAR({lag}) : {target}'); ax.legend(fontsize=8)
    fig.tight_layout()
    r.chart('Prévision VAR', fig)
    r.say(f"VAR estimé avec {lag} retard(s) sur {len(cols)} variables ({', '.join(cols)}).")
    return r.d


def run_mlp_ts(df, target, features, time_col=None, forecast_steps=12, **kw):
    from sklearn.neural_network import MLPRegressor
    from sklearn.preprocessing import StandardScaler
    r = Res('mlp_ts', 'deep', 'Réseau de neurones autorégressif (retards)')
    series, meta, st = _ts_setup(df, target, time_col)
    for t in meta['notes']:
        r.warn(t)
    y = series.values[-1500:].astype(float)
    p = int(min(12, max(3, len(y) // 10)))
    mu, sd = y.mean(), y.std() or 1.0
    z = (y - mu) / sd
    Xm = np.array([z[i - p:i] for i in range(p, len(z))])
    ym = z[p:]
    k = int(max(2, min(int(0.2 * len(ym)), 50)))
    Xtr, ytr, Xte, yte = Xm[:-k], ym[:-k], Xm[-k:], ym[-k:]
    mlp = MLPRegressor(hidden_layer_sizes=(32, 16), max_iter=1500, random_state=42, early_stopping=len(Xtr) > 100)
    mlp.fit(Xtr, ytr)
    pred = mlp.predict(Xte) * sd + mu
    act = yte * sd + mu
    rmse = float(np.sqrt(np.mean((act - pred) ** 2)))
    naive = float(np.sqrt(np.mean((act[1:] - act[:-1]) ** 2))) if len(act) > 1 else None
    mlp.fit(Xm, ym)
    steps = int(forecast_steps)
    hist = list(z[-p:])
    out = []
    for _ in range(steps):
        v = float(mlp.predict(np.array(hist[-p:]).reshape(1, -1))[0])
        out.append(v)
        hist.append(v)
    out = np.array(out) * sd + mu
    fdates = _forecast_dates(series, meta, steps)
    r.metric('RMSE', 'RMSE (1 pas, hors échantillon)', rmse, 4, f"Sur les {k} dernières observations")
    r.metric('MAE', 'MAE (hors échantillon)', float(np.mean(np.abs(act - pred))))
    if naive is not None:
        r.metric('RMSE_naif', 'RMSE prévision naïve', naive)
    r.metric('Lags', 'Retards utilisés', p, 0)
    r.metric('n', 'Observations', int(len(y)))
    r.table(f'Prévisions sur {steps} périodes (récursives)', ['Période', 'Prévision'],
            [[str(fdates[i].date()) if hasattr(fdates[i], 'date') else str(fdates[i]), fmt(out[i])] for i in range(steps)])
    xs = _axis_index(series, meta)[-len(y):]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(xs, y, color=NAVY, lw=1.4, label='Observé')
    ax.plot(xs[-k:], pred, color=STEEL, ls='--', lw=1.5, label='Prévision test (1 pas)')
    ax.plot(fdates, out, color=GOLD, lw=2, label='Prévision')
    ax.set_title('Réseau de neurones autorégressif'); ax.legend(fontsize=8)
    fig.tight_layout()
    r.chart('Série et prévisions', fig)
    r.say(f"Un perceptron multicouche prédit la valeur suivante à partir des {p} dernières valeurs (retards).")
    if naive is not None:
        r.say(f"Erreur hors échantillon : {fmt(rmse, 3)} contre {fmt(naive, 3)} pour la prévision naïve : " + ("le réseau fait mieux." if rmse < naive else "le réseau ne fait pas mieux que la prévision naïve."))
    r.warn("Les prévisions récursives à plusieurs pas deviennent vite incertaines ; comparez avec ARIMA ou SARIMA.")
    return r.d


# ----------------------------------------------------------------------------
# Volatilité
# ----------------------------------------------------------------------------
def run_volatility(kind, df, target, features, time_col=None, forecast_steps=12, **kw):
    from arch import arch_model
    names = {'garch': 'GARCH(1,1)', 'arch': 'ARCH(q)', 'egarch': 'EGARCH(1,1)', 'gjr': 'GJR-GARCH(1,1,1)'}
    r = Res(kind, 'volatility', names[kind])
    series, meta = prepare_series(df, target, time_col)
    if len(series) < 100:
        raise ValueError("Au moins 100 observations sont nécessaires.")
    ret, desc = volatility_input(series)
    for t in meta['notes']:
        r.warn(t)
    r.warn(desc)
    ret = ret.iloc[-3000:]
    ap = arch_effect(ret)
    if ap is not None:
        r.table('Test ARCH-LM sur la série', ['Statistique', 'p-value', 'Lecture'], [['ARCH-LM', fmt_p(ap), 'Effets ARCH présents' if ap < 0.05 else 'Pas d\'effet ARCH net']])
        if ap >= 0.05:
            r.warn("Pas d'effet ARCH net : la volatilité semble constante, un modèle de volatilité est peu utile ici.")

    def build(dist, q=None):
        if kind == 'arch':
            return arch_model(ret, mean='Constant', vol='ARCH', p=q, dist=dist)
        if kind == 'garch':
            return arch_model(ret, mean='Constant', vol='GARCH', p=1, q=1, dist=dist)
        if kind == 'egarch':
            return arch_model(ret, mean='Constant', vol='EGARCH', p=1, o=1, q=1, dist=dist)
        return arch_model(ret, mean='Constant', vol='GARCH', p=1, o=1, q=1, dist=dist)
    best = None
    for dist in ('normal', 't'):
        for q in ([1, 2, 3, 4, 5] if kind == 'arch' else [None]):
            try:
                res = build(dist, q).fit(disp='off', show_warning=False)
                if best is None or res.bic < best[0].bic:
                    best = (res, dist, q)
            except Exception:
                continue
    if best is None:
        raise ValueError("Estimation impossible.")
    res, dist, q = best
    if kind == 'arch':
        r.d['name'] = f'ARCH({q})'
    P = res.params
    r.metric('AIC', 'AIC', res.aic, 2)
    r.metric('BIC', 'BIC', res.bic, 2)
    r.metric('LogL', 'Log-vraisemblance', res.loglikelihood, 2)
    r.metric('n', 'Observations', int(len(ret)))
    r.metric('dist', 'Loi des innovations', 'Student' if dist == 't' else 'Normale')
    alpha = sum(P[k] for k in P.index if k.startswith('alpha['))
    beta = sum(P[k] for k in P.index if k.startswith('beta['))
    gamma = sum(P[k] for k in P.index if k.startswith('gamma['))
    if kind == 'gjr':
        pers = alpha + beta + gamma / 2
    elif kind == 'egarch':
        pers = beta
    else:
        pers = alpha + beta
    r.metric('Persistence', 'Persistance de la volatilité', pers)
    if 0 < pers < 1:
        r.metric('HalfLife', 'Demi-vie d\'un choc (périodes)', float(np.log(0.5) / np.log(pers)), 1)
    rows = [[k, fmt(P[k]), fmt(res.std_err[k]), fmt_p(res.pvalues[k]) + ' ' + stars(res.pvalues[k])] for k in P.index]
    r.table('Paramètres estimés', ['Paramètre', 'Valeur', 'Erreur std', 'p-value'], rows)
    # prévision
    steps = int(forecast_steps)
    try:
        fc = res.forecast(horizon=steps, reindex=False) if kind != 'egarch' else res.forecast(horizon=steps, method='simulation', simulations=500, reindex=False)
    except Exception:
        fc = res.forecast(horizon=steps, method='simulation', simulations=500, reindex=False)
    vol_fc = np.sqrt(fc.variance.values[-1])
    r.table(f'Volatilité prévue sur {steps} périodes (en %)', ['Pas', 'Volatilité prévue'], [[i + 1, fmt(vol_fc[i], 3)] for i in range(steps)])
    # VaR à un pas
    mu = float(P.get('mu', 0))
    s1 = float(vol_fc[0])
    if dist == 't' and 'nu' in P.index:
        nu = float(P['nu'])
        z95, z99 = stats.t.ppf(0.05, nu) * np.sqrt((nu - 2) / nu), stats.t.ppf(0.01, nu) * np.sqrt((nu - 2) / nu)
    else:
        z95, z99 = stats.norm.ppf(0.05), stats.norm.ppf(0.01)
    var95, var99 = -(mu + z95 * s1), -(mu + z99 * s1)
    r.metric('VaR95', 'VaR 95 % à 1 pas (en %)', var95, 3)
    r.metric('VaR99', 'VaR 99 % à 1 pas (en %)', var99, 3)
    # graphique
    cv = res.conditional_volatility
    xs = _axis_index(series, meta)
    xs = xs[-len(cv):] if len(xs) >= len(cv) else np.arange(len(cv))
    fig, ax = plt.subplots(2, 1, figsize=(9, 5.2), sharex=False)
    ax[0].plot(range(len(ret)), ret.values, color=GREY, lw=.8); ax[0].set_title('Rendements (%)')
    ax[1].plot(range(len(cv)), cv.values, color=NAVY, lw=1.2, label='Volatilité conditionnelle')
    ax[1].plot(range(len(cv), len(cv) + steps), vol_fc, color=GOLD, lw=2, label='Prévision')
    ax[1].set_title('Volatilité conditionnelle estimée et prévue'); ax[1].legend(fontsize=8)
    fig.tight_layout()
    r.chart('Rendements et volatilité', fig)
    # interprétation
    r.say(f"La persistance est de {fmt(pers, 3)} : " + ("les chocs de volatilité sont très durables (volatilité groupée)." if pers > 0.95 else
          "les chocs de volatilité se dissipent assez vite." if pers < 0.8 else "les chocs de volatilité sont persistants."))
    if 0 < pers < 1:
        r.say(f"Un choc de volatilité perd la moitié de son effet en environ {fmt(np.log(0.5) / np.log(pers), 1)} périodes.")
    if kind in ('egarch', 'gjr'):
        g = [k for k in P.index if k.startswith('gamma[')]
        if g:
            gp = res.pvalues[g[0]]
            sign = P[g[0]]
            if gp < 0.05 and sign > 0 and kind == 'gjr':
                r.say("Effet de levier significatif : les chocs négatifs augmentent plus la volatilité que les chocs positifs de même taille.")
            elif gp < 0.05 and sign < 0 and kind == 'egarch':
                r.say("Effet de levier significatif : les chocs négatifs augmentent plus la volatilité que les chocs positifs.")
            else:
                r.say("Pas d'asymétrie significative entre chocs positifs et négatifs.")
    r.say(f"Pour la prochaine période, la perte maximale attendue est de {fmt(var95, 2)} % avec 95 % de confiance et {fmt(var99, 2)} % à 99 %.")
    return r.d


def run_risk(df, target, features, time_col=None, **kw):
    r = Res('risk', 'volatility', 'Mesures de risque (VaR, ES, Sharpe)')
    series, meta = prepare_series(df, target, time_col)
    ret, desc = volatility_input(series)
    r.warn(desc)
    x = ret.values / 100.0
    if len(x) < 60:
        raise ValueError("Au moins 60 observations sont nécessaires.")
    ppy = {12: 12, 4: 4, 7: 252, 52: 52, 5: 252, 24: 252}.get(meta.get('period'), 252)
    mu, sd = x.mean(), x.std(ddof=1)
    sharpe = mu / sd * np.sqrt(ppy) if sd > 0 else None
    var95, var99 = -np.quantile(x, 0.05), -np.quantile(x, 0.01)
    es95 = -x[x <= np.quantile(x, 0.05)].mean()
    es99 = -x[x <= np.quantile(x, 0.01)].mean()
    pvar95 = -(mu + stats.norm.ppf(0.05) * sd)
    cum = np.cumsum(x)
    mdd = float((cum - np.maximum.accumulate(cum)).min())
    jb = stats.jarque_bera(x)[1]
    r.metric('Mean', 'Rendement moyen (%)', mu * 100, 3)
    r.metric('Std', 'Écart-type (%)', sd * 100, 3)
    r.metric('Sharpe', 'Ratio de Sharpe annualisé', sharpe, 2, f"Annualisation sur {ppy} périodes/an")
    r.metric('VaR95', 'VaR historique 95 % (%)', var95 * 100, 3)
    r.metric('ES95', 'Expected Shortfall 95 % (%)', es95 * 100, 3)
    r.metric('MDD', 'Perte maximale cumulée (%)', mdd * 100, 2)
    r.table('Statistiques de risque', ['Mesure', 'Valeur'], [
        ['Asymétrie (skewness)', fmt(stats.skew(x), 3)], ['Aplatissement en excès (kurtosis)', fmt(stats.kurtosis(x), 3)],
        ['Jarque-Bera (normalité), p-value', fmt_p(jb)], ['VaR historique 99 %', fmt(var99 * 100, 3) + ' %'],
        ['VaR paramétrique normale 95 %', fmt(pvar95 * 100, 3) + ' %'], ['Expected Shortfall 99 %', fmt(es99 * 100, 3) + ' %'],
        ['Rendement cumulé', fmt(cum[-1] * 100, 2) + ' %']])
    r.say(f"Avec 95 % de confiance, la perte sur une période ne dépasse pas {fmt(var95 * 100, 2)} % ; en cas de dépassement, la perte moyenne attendue (ES) est de {fmt(es95 * 100, 2)} %.")
    if stats.kurtosis(x) > 1:
        r.say(f"Queues épaisses (kurtosis en excès = {fmt(stats.kurtosis(x), 2)}) : la VaR normale sous-estime le risque extrême.")
    if sharpe is not None:
        r.say(f"Le ratio de Sharpe annualisé est de {fmt(sharpe, 2)} (" + ("bonne performance ajustée au risque" if sharpe > 1 else "performance ajustée au risque modeste") + ").")
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.4))
    ax[0].hist(x * 100, bins=40, color=STEEL, alpha=.85)
    ax[0].axvline(-var95 * 100, color=GOLD, lw=2, label='VaR 95 %'); ax[0].axvline(-es95 * 100, color=RED, lw=2, label='ES 95 %')
    ax[0].set_title('Distribution des rendements (%)'); ax[0].legend(fontsize=8)
    ax[1].plot(cum * 100, color=NAVY, lw=1.4); ax[1].set_title('Rendement cumulé (%)')
    fig.tight_layout()
    r.chart('Risque', fig)
    return r.d


# ----------------------------------------------------------------------------
# Répartition
# ----------------------------------------------------------------------------
FAMILY_OF = {**{k: 'regression' for k in ('ols', 'ridge', 'lasso', 'elasticnet', 'poisson', 'negbin')},
             **{k: 'panel' for k in ('panel_pooled', 'panel_fe', 'panel_re')},
             **{k: 'timeseries' for k in ('ar', 'ma', 'arma', 'arima', 'sarima', 'arimax', 'holtwinters', 'var')},
             **{k: 'volatility' for k in ('garch', 'arch', 'egarch', 'gjr', 'risk')},
             **{k: 'classification' for k in ('logit', 'mlogit')},
             **{k: 'ml' for k in ('rf_reg', 'gb_reg', 'svr', 'knn_reg', 'tree_reg', 'rf_clf', 'gb_clf', 'svm_clf', 'knn_clf', 'tree_clf', 'nb_clf')},
             **{k: 'deep' for k in ('mlp_reg', 'mlp_clf', 'mlp_ts')}}


def run_model(mid, df, target, features, time_col=None, entity_col=None, forecast_steps=12):
    """Exécute un modèle par identifiant ; ne lève jamais d'exception."""
    reg = {
        'ols': lambda: run_ols(df, target, features),
        'ridge': lambda: run_ridge(df, target, features),
        'lasso': lambda: run_lasso(df, target, features),
        'elasticnet': lambda: run_elasticnet(df, target, features),
        'poisson': lambda: run_count(df, target, features, kind='poisson'),
        'negbin': lambda: run_count(df, target, features, kind='negbin'),
        'panel_pooled': lambda: run_panel('pooled', df, target, features, entity_col, time_col),
        'panel_fe': lambda: run_panel('fe', df, target, features, entity_col, time_col),
        'panel_re': lambda: run_panel('re', df, target, features, entity_col, time_col),
        'logit': lambda: run_logit(df, target, features),
        'holtwinters': lambda: run_holtwinters(df, target, features, time_col, forecast_steps),
        'var': lambda: run_var(df, target, features, time_col, forecast_steps),
        'mlp_ts': lambda: run_mlp_ts(df, target, features, time_col, forecast_steps),
        'risk': lambda: run_risk(df, target, features, time_col),
    }
    for k in ('ar', 'ma', 'arma', 'arima', 'sarima', 'arimax'):
        reg[k] = (lambda kk: (lambda: run_arima_family(kk, df, target, features, time_col, forecast_steps)))(k)
    for k in ('garch', 'arch', 'egarch', 'gjr'):
        reg[k] = (lambda kk: (lambda: run_volatility(kk, df, target, features, time_col, forecast_steps)))(k)
    for k in ('rf_reg', 'gb_reg', 'svr', 'knn_reg', 'tree_reg', 'mlp_reg'):
        reg[k] = (lambda kk: (lambda: run_sk_regressor(kk, df, target, features)))(k)
    for k in ('mlogit', 'rf_clf', 'gb_clf', 'svm_clf', 'knn_clf', 'tree_clf', 'nb_clf', 'mlp_clf'):
        reg[k] = (lambda kk: (lambda: run_sk_classifier(kk, df, target, features)))(k)
    if mid not in reg:
        return {'id': mid, 'name': mid, 'family': 'regression', 'status': 'error', 'error': 'Modèle inconnu.',
                'metrics': [], 'tables': [], 'charts': [], 'interpretation': [], 'warnings': [], 'raw': {}}
    try:
        return reg[mid]()
    except Exception as e:
        return error_result(mid, FAMILY_OF.get(mid, 'regression'), mid, e)
