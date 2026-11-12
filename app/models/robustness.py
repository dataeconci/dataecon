# -*- coding: utf-8 -*-
"""
Tests de robustesse par modèle.

run_robustness(mid, df, target, features, time_col, entity_col) -> dict
  {'id', 'name', 'status', 'verdict', 'checks': [{label, ok, detail}], 'tables', 'charts', 'text'}
Ne lève jamais d'exception.
"""
import itertools
import traceback
import warnings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from models.analysis import prepare_xy, prepare_series, stationarity, detect_seasonality, volatility_input
from models.runners import (fmt, fmt_p, stars, to_b64, FAMILY_OF, NAVY, STEEL, GOLD, GREY, RED, GREEN,
                            _clf_data, _clf_estimator, _reg_estimator, _panel_frame, _fit_panel, hausman_test)

warnings.filterwarnings('ignore')
SEED = 42


class Rob:
    def __init__(self, mid, name):
        self.d = {'id': mid, 'name': name, 'status': 'ok', 'verdict': '', 'checks': [], 'tables': [], 'charts': [], 'text': []}

    def table(self, title, columns, rows):
        self.d['tables'].append({'title': title, 'columns': columns, 'rows': [[str(c) for c in r] for r in rows]})

    def chart(self, title, fig):
        self.d['charts'].append({'title': title, 'img': to_b64(fig)})

    def check(self, label, ok, detail=''):
        self.d['checks'].append({'label': label, 'ok': bool(ok), 'detail': detail})

    def say(self, t):
        self.d['text'].append(t)

    def finish(self):
        ch = self.d['checks']
        if ch:
            share = sum(c['ok'] for c in ch) / len(ch)
            self.d['verdict'] = 'Robuste' if share >= .8 else ('Globalement robuste' if share >= .5 else 'Fragile')
            self.d['score'] = round(100 * share)
            self.say(f"Bilan : {sum(c['ok'] for c in ch)} test(s) de robustesse sur {len(ch)} satisfaisants, soit un verdict « {self.d['verdict']} ».")
        return self.d


# ---------------------------------------------------------------------------------------------
# Régression linéaire
# ---------------------------------------------------------------------------------------------
def _ols_params(X, y, cov='nonrobust'):
    import statsmodels.api as sm
    return sm.OLS(y, sm.add_constant(X, has_constant='add')).fit(cov_type=cov) if cov != 'nonrobust' else sm.OLS(y, sm.add_constant(X, has_constant='add')).fit()


def _rob_linear(mid, name, df, target, features):
    import statsmodels.api as sm
    from statsmodels.stats.diagnostic import linear_reset
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import KFold, cross_val_score
    R = Rob(mid, name)
    X, y, notes, _ = prepare_xy(df, target, features)
    n, k = X.shape
    if n < k + 15:
        raise ValueError("Pas assez d'observations pour les tests de robustesse.")
    base = _ols_params(X, y, 'HC3')
    vars_ = list(X.columns)
    specs = {}
    specs['MCO classique'] = _ols_params(X, y)
    specs['Erreurs HC1'] = _ols_params(X, y, 'HC1')
    specs['Erreurs HC3 (référence)'] = base
    # winsorisation 1 % / 99 %
    Xw = X.apply(lambda c: c.clip(c.quantile(.01), c.quantile(.99)) if c.nunique() > 2 else c)
    yw = y.clip(y.quantile(.01), y.quantile(.99))
    specs['Winsorisation 1 %'] = _ols_params(Xw, yw, 'HC3')
    # observations influentes
    infl = sm.OLS(y, sm.add_constant(X, has_constant='add')).fit().get_influence()
    cook = infl.cooks_distance[0]
    mask = cook <= 4 / n
    n_drop = int((~mask).sum())
    if mask.sum() > k + 10:
        specs[f'Sans points influents ({n_drop})'] = _ols_params(X[mask], y[mask], 'HC3')
    # demi-échantillons
    rng = np.random.RandomState(SEED)
    perm = rng.permutation(n)
    h1, h2 = perm[: n // 2], perm[n // 2:]
    specs['Moitié A'] = _ols_params(X.iloc[h1], y.iloc[h1], 'HC3')
    specs['Moitié B'] = _ols_params(X.iloc[h2], y.iloc[h2], 'HC3')

    cols = ['Variable'] + list(specs.keys())
    rows = []
    for v in vars_:
        row = [v]
        for s, m in specs.items():
            row.append(f"{fmt(m.params[v], 3)}{stars(m.pvalues[v])}")
        rows.append(row)
    R.table('Coefficients selon la spécification (étoiles : * 10 %, ** 5 %, *** 1 %)', cols, rows)

    # stabilité de signe et de significativité
    sign_ok, sig_ok = [], []
    for v in vars_:
        b0 = base.params[v]
        sign_ok.append(all(np.sign(m.params[v]) == np.sign(b0) for m in specs.values()))
        s0 = base.pvalues[v] < .05
        sig_ok.append(all((m.pvalues[v] < .05) == s0 for m in specs.values()))
    ratio_sign, ratio_sig = np.mean(sign_ok), np.mean(sig_ok)
    R.table('Stabilité des résultats', ['Critère', 'Variables stables', 'Part'], [
        ['Signe identique dans toutes les spécifications', f'{sum(sign_ok)} / {k}', fmt(100 * ratio_sign, 0) + ' %'],
        ['Significativité (5 %) identique dans toutes les spécifications', f'{sum(sig_ok)} / {k}', fmt(100 * ratio_sig, 0) + ' %']])
    R.check('Stabilité du signe des coefficients', ratio_sign >= .9, f'{fmt(100 * ratio_sign, 0)} % des variables')
    R.check('Stabilité de la significativité', ratio_sig >= .7, f'{fmt(100 * ratio_sig, 0)} % des variables')

    # forest plot (variables centrées-réduites)
    sd = X.std().replace(0, 1)
    fig, ax = plt.subplots(figsize=(8, max(3, .55 * k * 1.2 + 1.5)))
    colors = [NAVY, STEEL, GOLD, '#5b8c85', GREY, RED, '#6a5d9a']
    ypos = np.arange(k)
    for j, (s, m) in enumerate(specs.items()):
        ax.scatter([m.params[v] * sd[v] for v in vars_], ypos + (j - len(specs) / 2) * .09, s=26, color=colors[j % len(colors)], label=s, zorder=3)
    ax.axvline(0, color='#94a3b8', lw=1)
    ax.set_yticks(ypos); ax.set_yticklabels(vars_)
    ax.set_xlabel(f'Effet sur {target} d\'un écart-type de la variable')
    ax.set_title('Stabilité des coefficients selon la spécification')
    ax.legend(frameon=False, fontsize=7, loc='center left', bbox_to_anchor=(1, .5))
    fig.tight_layout()
    R.chart('Stabilité des coefficients', fig)

    # bootstrap
    B = 300
    Xa = sm.add_constant(X, has_constant='add').values
    ya = y.values
    bs = np.empty((B, Xa.shape[1]))
    for b in range(B):
        i = rng.randint(0, n, n)
        bs[b] = np.linalg.lstsq(Xa[i], ya[i], rcond=None)[0]
    lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
    names = ['const'] + vars_
    rows, covers = [], 0
    for j, v in enumerate(names):
        if v == 'const':
            continue
        incl0 = lo[j] <= 0 <= hi[j]
        agree = (base.pvalues[v] < .05) == (not incl0)
        covers += agree
        rows.append([v, fmt(base.params[v], 3), f'[{fmt(lo[j], 3)} ; {fmt(hi[j], 3)}]', 'oui' if not incl0 else 'non', 'cohérent' if agree else 'divergent'])
    R.table(f'Intervalles de confiance par bootstrap ({B} tirages)', ['Variable', 'Coefficient', 'IC 95 % bootstrap', 'Exclut zéro', 'Avec le test t'], rows)
    R.check('Bootstrap cohérent avec les tests de significativité', covers / max(k, 1) >= .8, f'{covers}/{k} variables')

    # RESET et validation croisée
    try:
        rs = linear_reset(sm.OLS(y, sm.add_constant(X, has_constant='add')).fit(), power=2, use_f=True)
        R.check('Forme fonctionnelle (RESET de Ramsey)', rs.pvalue >= .05, f'p = {fmt_p(float(rs.pvalue))}')
    except Exception:
        pass
    kf = KFold(5, shuffle=True, random_state=SEED)
    cv = cross_val_score(LinearRegression(), X, y, cv=kf, scoring='r2')
    R.table('Validation croisée (5 blocs)', ['Indicateur', 'Valeur'], [['R² moyen', fmt(cv.mean(), 3)], ['Écart-type du R²', fmt(cv.std(), 3)],
                                                                         ['R² minimum', fmt(cv.min(), 3)], ['R² du modèle sur tout l\'échantillon', fmt(base.rsquared, 3)]])
    R.check('Capacité de généralisation (R² en validation croisée stable)', cv.std() < .1 and cv.mean() > .5 * base.rsquared,
            f'moyenne {fmt(cv.mean(), 3)} ± {fmt(cv.std(), 3)}')
    R.say("Les résultats sont comparés sous plusieurs hypothèses : erreurs standard classiques et robustes, retrait des valeurs extrêmes, "
          "points influents, demi-échantillons aléatoires et rééchantillonnage bootstrap.")
    nonrob = [v for v, ok in zip(vars_, sig_ok) if not ok]
    if nonrob:
        R.say("Variables dont la significativité dépend de la spécification (à interpréter avec prudence) : " + ', '.join(nonrob) + '.')
    else:
        R.say("La significativité de chaque variable reste inchangée quelle que soit la spécification testée.")
    return R.finish()


# ---------------------------------------------------------------------------------------------
# Modèles de comptage
# ---------------------------------------------------------------------------------------------
def _rob_count(mid, name, df, target, features):
    import statsmodels.api as sm
    R = Rob(mid, name)
    X, y, notes, _ = prepare_xy(df, target, features)
    Xc = sm.add_constant(X, has_constant='add')
    pois = sm.GLM(y, Xc, family=sm.families.Poisson()).fit()
    pois_r = sm.GLM(y, Xc, family=sm.families.Poisson()).fit(cov_type='HC1')
    disp = float(pois.pearson_chi2 / pois.df_resid)
    rows = [[v, fmt(pois.params[v], 3), fmt_p(pois.pvalues[v]), fmt_p(pois_r.pvalues[v]),
             'stable' if (pois.pvalues[v] < .05) == (pois_r.pvalues[v] < .05) else 'diffère'] for v in X.columns]
    R.table('Poisson : erreurs classiques et robustes', ['Variable', 'Coefficient', 'p classique', 'p robuste (HC1)', 'Conclusion'], rows)
    R.table('Surdispersion', ['Indicateur', 'Valeur', 'Lecture'], [['Statistique de Pearson / ddl', fmt(disp, 2),
                                                                    'Surdispersion : préférer binomiale négative ou erreurs robustes' if disp > 1.5 else 'Dispersion compatible avec Poisson']])
    R.check('Absence de surdispersion forte', disp <= 1.5, f'ratio = {fmt(disp, 2)}')
    stable = np.mean([(pois.pvalues[v] < .05) == (pois_r.pvalues[v] < .05) for v in X.columns])
    R.check('Conclusions identiques avec erreurs robustes', stable >= .8, f'{fmt(100 * stable, 0)} % des variables')
    try:
        nb = sm.NegativeBinomial(y, Xc).fit(disp=0)
        R.table('Comparaison Poisson / binomiale négative', ['Modèle', 'AIC', 'BIC'], [['Poisson', fmt(pois.aic, 1), fmt(pois.bic, 1)], ['Binomiale négative', fmt(nb.aic, 1), fmt(nb.bic, 1)]])
        same = np.mean([np.sign(nb.params[v]) == np.sign(pois.params[v]) for v in X.columns])
        R.check('Signes identiques entre Poisson et binomiale négative', same >= .9, f'{fmt(100 * same, 0)} %')
    except Exception:
        pass
    rng = np.random.RandomState(SEED)
    perm = rng.permutation(len(X))
    signs = []
    for part in (perm[: len(X) // 2], perm[len(X) // 2:]):
        m = sm.GLM(y.iloc[part], sm.add_constant(X.iloc[part], has_constant='add'), family=sm.families.Poisson()).fit()
        signs.append([np.sign(m.params[v]) == np.sign(pois.params[v]) for v in X.columns])
    sub = np.mean(signs)
    R.check('Stabilité des signes sur demi-échantillons', sub >= .9, f'{fmt(100 * sub, 0)} %')
    R.say("Les modèles de comptage sont éprouvés face à la surdispersion, aux erreurs standard robustes et à un changement de loi (Poisson, binomiale négative).")
    return R.finish()


# ---------------------------------------------------------------------------------------------
# Machine learning / deep learning : régression
# ---------------------------------------------------------------------------------------------
def _light(est):
    """Réduit le coût des ensembles d'arbres pour les tests répétés."""
    try:
        params = est.get_params()
        for key in list(params):
            if key.endswith('n_estimators') and params[key] > 60:
                est.set_params(**{key: 60})
    except Exception:
        pass
    return est


def _rob_ml_reg(mid, name, df, target, features):
    from sklearn.dummy import DummyRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import RepeatedKFold, cross_val_score, permutation_test_score, KFold
    R = Rob(mid, name)
    _, _, factory = _reg_estimator(mid)
    X, y, notes, _ = prepare_xy(df, target, features, max_rows=2500)
    if len(X) < 40:
        raise ValueError("Pas assez d'observations.")
    rkf = RepeatedKFold(n_splits=5, n_repeats=2, random_state=SEED)
    sc = cross_val_score(_light(factory()), X, y, cv=rkf, scoring='r2')
    sc_lin = cross_val_score(LinearRegression(), X, y, cv=rkf, scoring='r2')
    sc_dum = cross_val_score(DummyRegressor(), X, y, cv=rkf, scoring='r2')
    rm = -cross_val_score(_light(factory()), X, y, cv=KFold(5, shuffle=True, random_state=SEED), scoring='neg_root_mean_squared_error')
    R.table('Validation croisée répétée (5 blocs × 2)', ['Modèle', 'R² moyen', 'Écart-type', 'Min', 'Max'], [
        [name, fmt(sc.mean(), 3), fmt(sc.std(), 3), fmt(sc.min(), 3), fmt(sc.max(), 3)],
        ['Régression linéaire (référence)', fmt(sc_lin.mean(), 3), fmt(sc_lin.std(), 3), fmt(sc_lin.min(), 3), fmt(sc_lin.max(), 3)],
        ['Prédiction par la moyenne (naïf)', fmt(sc_dum.mean(), 3), fmt(sc_dum.std(), 3), fmt(sc_dum.min(), 3), fmt(sc_dum.max(), 3)]])
    R.table('Erreur de prédiction (RMSE par bloc)', ['Moyenne', 'Écart-type', 'Min', 'Max'], [[fmt(rm.mean(), 3), fmt(rm.std(), 3), fmt(rm.min(), 3), fmt(rm.max(), 3)]])
    R.check('Meilleur que le modèle naïf', sc.mean() > sc_dum.mean() + .05, f'{fmt(sc.mean(), 3)} contre {fmt(sc_dum.mean(), 3)}')
    R.check('Stabilité entre blocs (écart-type du R² < 0,10)', sc.std() < .10, f'écart-type {fmt(sc.std(), 3)}')
    R.check('Au moins aussi bon qu\'une régression linéaire', sc.mean() >= sc_lin.mean() - .02, f'{fmt(sc.mean(), 3)} contre {fmt(sc_lin.mean(), 3)}')
    try:
        s, perms, p = permutation_test_score(_light(factory()), X, y, cv=KFold(3, shuffle=True, random_state=SEED), n_permutations=15, scoring='r2', random_state=SEED, n_jobs=1)
        R.table('Test de permutation (liaison réelle entre X et y)', ['R² observé', 'R² moyen sous permutation', 'p-value'], [[fmt(s, 3), fmt(perms.mean(), 3), fmt_p(p)]])
        R.check('Test de permutation significatif', p < .1, f'p = {fmt_p(p)}')
    except Exception:
        pass
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    bp = ax.boxplot([sc, sc_lin, sc_dum], labels=['Modèle', 'Linéaire', 'Naïf'], patch_artist=True)
    for p_, c in zip(bp['boxes'], [NAVY, STEEL, GOLD]):
        p_.set_facecolor(c); p_.set_alpha(.8)
    ax.set_title('R² en validation croisée'); ax.set_ylabel('R²')
    fig.tight_layout()
    R.chart('Distribution du R² en validation croisée', fig)
    R.say("La robustesse d'un modèle d'apprentissage se juge hors échantillon : le R² est recalculé sur 10 découpages différents puis comparé à une référence linéaire et à un modèle naïf.")
    return R.finish()


# ---------------------------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------------------------
def _clf_factory(mid, imb):
    if mid == 'logit':
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        return lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    return _clf_estimator(mid, imb)[2]


def _rob_clf(mid, name, df, target, features):
    from sklearn.dummy import DummyClassifier
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
    from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score, cross_val_predict, StratifiedKFold, permutation_test_score
    R = Rob(mid, name)
    X, y, classes, notes = _clf_data(df, target, features)
    if len(X) > 2500:
        idx = np.random.RandomState(SEED).choice(len(X), 2500, replace=False)
        X, y = X.iloc[idx], y.iloc[idx]
    imb = float(y.value_counts().max() / max(y.value_counts().min(), 1))
    factory = _clf_factory(mid, imb)
    binary = len(classes) == 2
    if y.value_counts().min() < 6:
        raise ValueError("Une classe compte moins de 6 observations.")
    rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=2, random_state=SEED)
    acc = cross_val_score(_light(factory()), X, y, cv=rskf, scoring='accuracy')
    dum = cross_val_score(DummyClassifier(strategy='most_frequent'), X, y, cv=rskf, scoring='accuracy')
    rows = [[name, 'Exactitude', fmt(acc.mean(), 3), fmt(acc.std(), 3), fmt(acc.min(), 3), fmt(acc.max(), 3)],
            ['Classe majoritaire (naïf)', 'Exactitude', fmt(dum.mean(), 3), fmt(dum.std(), 3), fmt(dum.min(), 3), fmt(dum.max(), 3)]]
    auc = None
    if binary:
        auc = cross_val_score(_light(factory()), X, y, cv=rskf, scoring='roc_auc')
        rows.insert(1, [name, 'AUC', fmt(auc.mean(), 3), fmt(auc.std(), 3), fmt(auc.min(), 3), fmt(auc.max(), 3)])
    else:
        f1m = cross_val_score(_light(factory()), X, y, cv=rskf, scoring='f1_macro')
        rows.insert(1, [name, 'F1 macro', fmt(f1m.mean(), 3), fmt(f1m.std(), 3), fmt(f1m.min(), 3), fmt(f1m.max(), 3)])
    R.table('Validation croisée stratifiée répétée (5 blocs × 2)', ['Modèle', 'Mesure', 'Moyenne', 'Écart-type', 'Min', 'Max'], rows)
    R.check('Meilleur que la classe majoritaire', acc.mean() > dum.mean() + .02, f'{fmt(acc.mean(), 3)} contre {fmt(dum.mean(), 3)}')
    R.check('Stabilité entre blocs (écart-type < 0,05)', acc.std() < .05, f'écart-type {fmt(acc.std(), 3)}')
    if auc is not None:
        R.check('Pouvoir discriminant (AUC moyen ≥ 0,65)', auc.mean() >= .65, f'AUC = {fmt(auc.mean(), 3)}')
    # sensibilité au seuil
    if binary:
        try:
            proba = cross_val_predict(_light(factory()), X, y, cv=StratifiedKFold(5, shuffle=True, random_state=SEED), method='predict_proba')[:, 1]
            rows, f1s = [], []
            for th in (.3, .4, .5, .6, .7):
                pr = (proba >= th).astype(int)
                f1 = f1_score(y, pr, zero_division=0)
                f1s.append(f1)
                rows.append([fmt(th, 1), fmt(accuracy_score(y, pr), 3), fmt(precision_score(y, pr, zero_division=0), 3),
                             fmt(recall_score(y, pr, zero_division=0), 3), fmt(f1, 3)])
            R.table('Sensibilité au seuil de décision (prédictions hors échantillon)', ['Seuil', 'Exactitude', 'Précision', 'Rappel', 'F1'], rows)
            R.check('Qualité peu sensible au seuil (écart de F1 entre 0,4 et 0,6 < 0,15)', abs(f1s[1] - f1s[3]) < .15, f'écart = {fmt(abs(f1s[1] - f1s[3]), 3)}')
            # bootstrap de l'AUC
            rng = np.random.RandomState(SEED)
            yy = y.values
            bs = []
            for _ in range(300):
                i = rng.randint(0, len(yy), len(yy))
                if len(set(yy[i])) == 2:
                    bs.append(roc_auc_score(yy[i], proba[i]))
            lo, hi = np.percentile(bs, [2.5, 97.5])
            R.table('Bootstrap de l\'AUC (300 tirages)', ['AUC', 'IC 95 % bas', 'IC 95 % haut'], [[fmt(roc_auc_score(yy, proba), 3), fmt(lo, 3), fmt(hi, 3)]])
            R.check('Borne basse de l\'AUC supérieure à 0,5', lo > .5, f'IC [{fmt(lo, 3)} ; {fmt(hi, 3)}]')
            fig, ax = plt.subplots(figsize=(6, 3.3))
            ths = np.linspace(.1, .9, 17)
            ax.plot(ths, [f1_score(y, (proba >= t).astype(int), zero_division=0) for t in ths], color=NAVY, lw=2, label='F1')
            ax.plot(ths, [accuracy_score(y, (proba >= t).astype(int)) for t in ths], color=GOLD, lw=2, label='Exactitude')
            ax.set_xlabel('Seuil de décision'); ax.set_title('Sensibilité au seuil'); ax.legend(frameon=False)
            fig.tight_layout()
            R.chart('Sensibilité au seuil de décision', fig)
        except Exception:
            traceback.print_exc()
    try:
        s, perms, p = permutation_test_score(_light(factory()), X, y, cv=StratifiedKFold(3, shuffle=True, random_state=SEED), n_permutations=15, scoring='accuracy', random_state=SEED, n_jobs=1)
        R.table('Test de permutation', ['Exactitude observée', 'Exactitude moyenne sous permutation', 'p-value'], [[fmt(s, 3), fmt(perms.mean(), 3), fmt_p(p)]])
        R.check('Test de permutation significatif', p < .1, f'p = {fmt_p(p)}')
    except Exception:
        pass
    # logit : erreurs robustes
    if mid == 'logit' and binary:
        try:
            import statsmodels.api as sm
            Xc = sm.add_constant(X, has_constant='add')
            m1 = sm.Logit(y, Xc).fit(disp=0)
            m2 = sm.Logit(y, Xc).fit(disp=0, cov_type='HC1')
            rows = [[v, fmt(m1.params[v], 3), fmt_p(m1.pvalues[v]), fmt_p(m2.pvalues[v]), 'stable' if (m1.pvalues[v] < .05) == (m2.pvalues[v] < .05) else 'diffère'] for v in X.columns]
            R.table('Logit : erreurs classiques et robustes', ['Variable', 'Coefficient', 'p classique', 'p robuste (HC1)', 'Conclusion'], rows)
            st = np.mean([(m1.pvalues[v] < .05) == (m2.pvalues[v] < .05) for v in X.columns])
            R.check('Conclusions identiques avec erreurs robustes', st >= .8, f'{fmt(100 * st, 0)} %')
        except Exception:
            pass
    R.say("Le modèle de classification est évalué par validation croisée répétée, comparé à une règle triviale, puis éprouvé par permutation, bootstrap et variation du seuil.")
    return R.finish()


# ---------------------------------------------------------------------------------------------
# Séries temporelles
# ---------------------------------------------------------------------------------------------
def _rob_ts(mid, name, df, target, features, time_col):
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.stats.diagnostic import acorr_ljungbox
    R = Rob(mid, name)
    series, meta = prepare_series(df, target, time_col)
    if len(series) < 30:
        raise ValueError("Série trop courte (moins de 30 observations).")
    y = series.iloc[-400:].reset_index(drop=True)
    st = stationarity(y)
    d = st['d']
    per = meta.get('period')
    if per and (len(y) < 3 * per or not detect_seasonality(y.diff(d).dropna().values if d else y.values, [per])[0]):
        per = None
    grid = [(p, d, q, None) for p, q in itertools.product(range(3), range(3)) if not (p == 0 and q == 0 and d == 0)]
    if per:
        grid += [((1, 0, 0), d, (0, 1, 1), per), ((0, 0, 1), d, (0, 1, 1), per)]
    fits = []
    for g in grid:
        try:
            if g[3] is None:
                order, seas = (g[0], g[1], g[2]), (0, 0, 0, 0)
                lbl = f'ARIMA({g[0]},{g[1]},{g[2]})'
            else:
                order, seas = (g[0][0], g[1], g[0][2]), (g[2][0], g[2][1], g[2][2], g[3])
                lbl = f'SARIMA{order}x{seas}'
            m = SARIMAX(y, order=order, seasonal_order=seas, trend='c' if d == 0 else 'n').fit(disp=False, maxiter=100)
            fits.append((lbl, order, seas, m))
        except Exception:
            continue
    if not fits:
        raise ValueError("Aucune spécification alternative n'a pu être estimée.")
    fits.sort(key=lambda t: t[3].aic)
    rows = [[l, fmt(m.aic, 1), fmt(m.bic, 1), fmt(m.llf, 1)] for l, _, _, m in fits[:8]]
    R.table('Spécifications alternatives (classées par AIC)', ['Modèle', 'AIC', 'BIC', 'Log-vraisemblance'], rows)
    gap = fits[1][3].aic - fits[0][3].aic if len(fits) > 1 else 10
    R.say(f"Le meilleur modèle selon l'AIC est {fits[0][0]} ; l'écart d'AIC avec la spécification suivante est de {fmt(gap, 2)}"
          + (" : les deux spécifications sont quasi équivalentes." if gap < 2 else "."))
    best = fits[0]
    resid = best[3].resid.iloc[max(d, 1):]
    lb = acorr_ljungbox(resid, lags=[10], return_df=True)
    R.table('Diagnostic du meilleur modèle', ['Test', 'p-value', 'Lecture'], [['Ljung-Box des résidus (10 retards)', fmt_p(lb['lb_pvalue'].iloc[0]),
                                                                          'Résidus sans autocorrélation' if lb['lb_pvalue'].iloc[0] >= .05 else 'Autocorrélation résiduelle']])
    R.check('Résidus sans autocorrélation', lb['lb_pvalue'].iloc[0] >= .05, f'p = {fmt_p(lb["lb_pvalue"].iloc[0])}')
    # évaluation hors échantillon à origine mobile
    k = int(min(24, max(8, len(y) // 5)))
    train_end = len(y) - k
    errs_m, errs_n, errs_s, preds = [], [], [], []
    try:
        m0 = SARIMAX(y.iloc[:train_end], order=best[1], seasonal_order=best[2], trend='c' if d == 0 else 'n').fit(disp=False, maxiter=100)
        res_roll = m0
        for t in range(train_end, len(y)):
            f = float(res_roll.forecast(1).iloc[0])
            preds.append(f)
            errs_m.append(y.iloc[t] - f)
            errs_n.append(y.iloc[t] - y.iloc[t - 1])
            if per and t - per >= 0:
                errs_s.append(y.iloc[t] - y.iloc[t - per])
            res_roll = res_roll.append(y.iloc[t:t + 1], refit=False)
        rm = lambda e: float(np.sqrt(np.mean(np.square(e))))
        ma = lambda e: float(np.mean(np.abs(e)))
        rows = [[best[0], fmt(rm(errs_m), 3), fmt(ma(errs_m), 3)], ['Naïf (dernière valeur)', fmt(rm(errs_n), 3), fmt(ma(errs_n), 3)]]
        if len(errs_s) == k:
            rows.append([f'Naïf saisonnier (retard {per})', fmt(rm(errs_s), 3), fmt(ma(errs_s), 3)])
        R.table(f'Prévision à un pas sur les {k} dernières observations', ['Méthode', 'RMSE', 'MAE'], rows)
        R.check('Prévision hors échantillon meilleure que le modèle naïf', rm(errs_m) < rm(errs_n), f'RMSE {fmt(rm(errs_m), 3)} contre {fmt(rm(errs_n), 3)}')
        fig, ax = plt.subplots(figsize=(8.5, 3.4))
        ax.plot(range(len(y)), y.values, color=NAVY, lw=1.4, label='Observé')
        ax.plot(range(train_end, len(y)), preds, color=GOLD, lw=2, label='Prévision à un pas')
        ax.axvline(train_end, color=GREY, ls='--'); ax.legend(frameon=False)
        ax.set_title(f'Évaluation hors échantillon ({best[0]})')
        fig.tight_layout()
        R.chart('Prévision hors échantillon', fig)
    except Exception:
        traceback.print_exc()
    # stabilité sur deux sous-périodes
    half = len(y) // 2
    try:
        a = SARIMAX(y.iloc[:half], order=best[1], seasonal_order=best[2], trend='c' if d == 0 else 'n').fit(disp=False, maxiter=100)
        b = SARIMAX(y.iloc[half:].reset_index(drop=True), order=best[1], seasonal_order=best[2], trend='c' if d == 0 else 'n').fit(disp=False, maxiter=100)
        names = [n for n in a.params.index if n in b.params.index and n.startswith(('ar', 'ma'))]
        if names:
            R.table('Stabilité des paramètres entre deux sous-périodes', ['Paramètre', 'Première moitié', 'Seconde moitié'], [[n, fmt(a.params[n], 3), fmt(b.params[n], 3)] for n in names])
            diff = max(abs(a.params[n] - b.params[n]) for n in names)
            R.check('Paramètres stables entre sous-périodes (écart maximal < 0,3)', diff < .3, f'écart maximal = {fmt(diff, 2)}')
    except Exception:
        pass
    R.say("La robustesse d'un modèle de série temporelle est évaluée par comparaison de spécifications voisines, test d'autocorrélation des résidus, "
          "prévision hors échantillon contre des méthodes naïves et stabilité des paramètres dans le temps.")
    return R.finish()


# ---------------------------------------------------------------------------------------------
# Volatilité
# ---------------------------------------------------------------------------------------------
def _rob_vol(mid, name, df, target, features, time_col):
    from arch import arch_model
    from statsmodels.stats.diagnostic import acorr_ljungbox
    R = Rob(mid, name)
    series, meta = prepare_series(df, target, time_col)
    if len(series) < 100:
        raise ValueError("Au moins 100 observations sont nécessaires.")
    ret, _ = volatility_input(series, target)
    ret = ret.iloc[-2500:]
    specs = []
    for lbl, kw in [('GARCH(1,1)', dict(vol='GARCH', p=1, q=1)), ('GJR-GARCH(1,1,1)', dict(vol='GARCH', p=1, o=1, q=1)), ('EGARCH(1,1)', dict(vol='EGARCH', p=1, o=1, q=1))]:
        for dist in ('normal', 't', 'skewt'):
            try:
                res = arch_model(ret, mean='Constant', dist=dist, **kw).fit(disp='off', show_warning=False)
                pers = None
                pr = res.params
                if 'alpha[1]' in pr and 'beta[1]' in pr:
                    pers = float(pr['alpha[1]'] + pr['beta[1]'] + (0.5 * pr['gamma[1]'] if 'gamma[1]' in pr and kw.get('vol') == 'GARCH' else 0))
                z = res.std_resid.dropna()
                lb = acorr_ljungbox(z ** 2, lags=[10], return_df=True)['lb_pvalue'].iloc[0]
                specs.append((lbl, dist, res, pers, float(lb)))
            except Exception:
                continue
    if not specs:
        raise ValueError("Aucune spécification n'a pu être estimée.")
    specs.sort(key=lambda t: t[2].bic)
    R.table('Spécifications alternatives (classées par BIC)', ['Modèle', 'Loi des innovations', 'AIC', 'BIC', 'Persistance', 'Ljung-Box des carrés standardisés (p)'],
            [[l, d_, fmt(r.aic, 1), fmt(r.bic, 1), fmt(p, 3) if p is not None else '—', fmt_p(lb)] for l, d_, r, p, lb in specs])
    dist_best = {d_: min([s for s in specs if s[1] == d_], key=lambda t: t[2].bic) for d_ in {s[1] for s in specs}}
    R.check('La loi non gaussienne améliore le BIC (queues épaisses)', specs[0][1] != 'normal', f'meilleure loi : {specs[0][1]}')
    pers = [s[3] for s in specs if s[3] is not None]
    if pers:
        R.check('Persistance stable entre spécifications (étendue < 0,10)', (max(pers) - min(pers)) < .10, f'de {fmt(min(pers), 3)} à {fmt(max(pers), 3)}')
        R.check('Processus stationnaire (persistance < 1)', max(pers) < 1, f'maximum = {fmt(max(pers), 3)}')
    R.check('Carrés des résidus standardisés sans autocorrélation', specs[0][4] >= .05, f'p = {fmt_p(specs[0][4])}')
    half = len(ret) // 2
    hp = []
    for part in (ret.iloc[:half], ret.iloc[half:]):
        try:
            r = arch_model(part, mean='Constant', vol='GARCH', p=1, q=1, dist='t').fit(disp='off', show_warning=False)
            hp.append(float(r.params['alpha[1]'] + r.params['beta[1]']))
        except Exception:
            hp.append(None)
    if all(v is not None for v in hp):
        R.table('Stabilité de la persistance (GARCH(1,1), loi de Student)', ['Première moitié', 'Seconde moitié'], [[fmt(hp[0], 3), fmt(hp[1], 3)]])
        R.check('Persistance stable entre sous-périodes (écart < 0,15)', abs(hp[0] - hp[1]) < .15, f'écart = {fmt(abs(hp[0] - hp[1]), 3)}')
    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    for (lbl, dist, res, _, _), c in zip(specs[:3], [NAVY, GOLD, STEEL]):
        ax.plot(res.conditional_volatility.values, lw=1.1, color=c, label=f'{lbl} ({dist})')
    ax.set_title('Volatilité conditionnelle selon la spécification'); ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    R.chart('Volatilité conditionnelle', fig)
    R.say("Les modèles de volatilité sont confrontés à des variantes de spécification (symétrique, asymétrique) et de loi des innovations, puis à un découpage temporel.")
    return R.finish()


# ---------------------------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------------------------
def _rob_panel(mid, name, df, target, features, time_col, entity_col):
    R = Rob(mid, name)
    if not entity_col or not time_col:
        raise ValueError("Colonnes d'entité et de temps nécessaires.")
    fits = {}
    for which, lbl in (('pooled', 'MCO empilés'), ('re', 'Effets aléatoires'), ('fe', 'Effets fixes')):
        try:
            fits[lbl] = _fit_panel(df, target, features, entity_col, time_col, which, cov='clustered')[0]
        except Exception:
            continue
    if 'Effets fixes' not in fits:
        raise ValueError("Les effets fixes n'ont pas pu être estimés.")
    fe_un = _fit_panel(df, target, features, entity_col, time_col, 'fe', cov='unadjusted')[0]
    vars_ = [v for v in fits['Effets fixes'].params.index if v != 'const']
    cols = ['Variable'] + list(fits.keys())
    rows = [[v] + [f"{fmt(m.params[v], 3)}{stars(m.pvalues[v])}" if v in m.params.index else '—' for m in fits.values()] for v in vars_]
    R.table('Coefficients selon l\'estimateur (erreurs groupées par unité)', cols, rows)
    base = fits['Effets fixes']
    rows = [[v, fmt(base.std_errors[v], 4), fmt(fe_un.std_errors[v], 4), fmt_p(base.pvalues[v]), fmt_p(fe_un.pvalues[v]),
             'stable' if (base.pvalues[v] < .05) == (fe_un.pvalues[v] < .05) else 'diffère'] for v in vars_]
    R.table('Effets fixes : erreurs groupées et classiques', ['Variable', 'ES groupée', 'ES classique', 'p groupée', 'p classique', 'Conclusion'], rows)
    st = np.mean([(base.pvalues[v] < .05) == (fe_un.pvalues[v] < .05) for v in vars_])
    R.check('Conclusions identiques avec erreurs groupées et classiques', st >= .8, f'{fmt(100 * st, 0)} %')
    sg = np.mean([all(np.sign(m.params[v]) == np.sign(base.params[v]) for m in fits.values() if v in m.params.index) for v in vars_])
    R.check('Signe des coefficients identique entre estimateurs', sg >= .9, f'{fmt(100 * sg, 0)} % des variables')
    try:
        h = hausman_test(df, target, features, entity_col, time_col)
        if h:
            R.table('Choix de l\'estimateur', ['Test', 'Statistique', 'p-value', 'Conclusion'], [[h['method'], fmt(h['stat'], 3), fmt_p(h['p']), 'Effets fixes préférables' if h['p'] < .05 else 'Effets aléatoires acceptables']])
    except Exception:
        pass
    # jackknife par unité
    X, y, _ = _panel_frame(df, target, features, entity_col, time_col)
    ents = list(X.index.get_level_values(0).unique())
    if 2 < len(ents) <= 60:
        v0 = vars_[0]
        vals = []
        for e in ents:
            sub = df[df[entity_col].astype(str) != str(e)]
            try:
                m = _fit_panel(sub, target, features, entity_col, time_col, 'fe', cov='unadjusted')[0]
                vals.append((e, float(m.params[v0]), float(m.pvalues[v0])))
            except Exception:
                continue
        if vals:
            b0 = float(base.params[v0])
            R.table(f'Validation en omettant chaque unité (coefficient de {v0})', ['Unité omise', 'Coefficient', 'p-value'], [[str(e), fmt(b, 3), fmt_p(p)] for e, b, p in vals[:20]])
            same = np.mean([np.sign(b) == np.sign(b0) for _, b, _ in vals])
            sig = np.mean([p < .05 for _, _, p in vals]) if base.pvalues[v0] < .05 else np.mean([p >= .05 for _, _, p in vals])
            R.check('Signe inchangé quand on retire une unité', same >= .95, f'{fmt(100 * same, 0)} % des cas')
            R.check('Significativité inchangée quand on retire une unité', sig >= .8, f'{fmt(100 * sig, 0)} % des cas')
            fig, ax = plt.subplots(figsize=(7.5, 3.3))
            ax.bar([str(e) for e, _, _ in vals], [b for _, b, _ in vals], color=STEEL)
            ax.axhline(b0, color=GOLD, lw=2, label='Estimation complète'); ax.legend(frameon=False)
            ax.set_title(f'Coefficient de {v0} en omettant chaque unité'); plt.setp(ax.get_xticklabels(), rotation=25)
            fig.tight_layout()
            R.chart('Jackknife par unité', fig)
    R.say("La robustesse du panel est examinée en changeant d'estimateur (empilé, aléatoire, fixe), de matrice de variance (groupée ou classique) et en retirant tour à tour chaque unité.")
    return R.finish()


# ---------------------------------------------------------------------------------------------
def run_robustness(mid, df, target, features, time_col=None, entity_col=None, name=None):
    fam = FAMILY_OF.get(mid, 'regression')
    name = name or mid
    try:
        if mid in ('ols', 'ridge', 'lasso', 'elasticnet'):
            return _rob_linear(mid, name, df, target, features)
        if mid in ('poisson', 'negbin'):
            return _rob_count(mid, name, df, target, features)
        if fam == 'panel':
            return _rob_panel(mid, name, df, target, features, time_col, entity_col)
        if fam == 'volatility':
            return _rob_vol(mid, name, df, target, features, time_col)
        if fam == 'timeseries':
            return _rob_ts(mid, name, df, target, features, time_col)
        if mid in ('logit', 'mlogit') or mid.endswith('_clf'):
            return _rob_clf(mid, name, df, target, features)
        if mid.endswith('_reg') or mid in ('svr', 'mlp_reg'):
            return _rob_ml_reg(mid, name, df, target, features)
        raise ValueError('Pas de test de robustesse défini pour ce modèle.')
    except Exception as e:
        traceback.print_exc()
        return {'id': mid, 'name': name, 'status': 'error', 'verdict': '', 'checks': [], 'tables': [], 'charts': [], 'text': [],
                'error': f"Les tests de robustesse n'ont pas pu être calculés : {e}"}
