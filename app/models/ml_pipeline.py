# -*- coding: utf-8 -*-
"""
Partition train / validation / test, optimisation des hyperparamètres et évaluation finale.

- Régression et classification (ML, deep learning) : 60 % apprentissage, 20 % validation, 20 % test.
  Les hyperparamètres sont choisis sur la validation ; le modèle retenu est ré-estimé sur apprentissage + validation
  puis évalué une seule fois sur le test.
- Séries temporelles et volatilité : partition chronologique 70 / 15 / 15.
"""
import time
import warnings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from models.runners import fmt, fmt_p, NAVY, STEEL, GOLD, GREY, RED, GREEN

warnings.filterwarnings('ignore')
SEED = 42
MAX_TUNE_SECONDS = 45
N_CANDIDATES = 10

GRIDS = {
    'rf_reg': {'n_estimators': [100, 200, 300], 'max_depth': [4, 8, 12, None], 'min_samples_leaf': [1, 3, 5]},
    'rf_clf': {'n_estimators': [100, 200, 300], 'max_depth': [4, 8, 12, None], 'min_samples_leaf': [1, 3, 5]},
    'gb_reg': {'n_estimators': [100, 200], 'learning_rate': [.03, .05, .1], 'max_depth': [2, 3, 4], 'subsample': [.8, 1.0]},
    'gb_clf': {'n_estimators': [100, 200], 'learning_rate': [.03, .05, .1], 'max_depth': [2, 3, 4], 'subsample': [.8, 1.0]},
    'svr': {'C': [1, 10, 100], 'epsilon': [.01, .1, .5], 'gamma': ['scale', 'auto']},
    'svm_clf': {'C': [.5, 1, 3, 10, 30], 'gamma': ['scale', 'auto']},
    'knn_reg': {'n_neighbors': [3, 5, 7, 11, 15, 25], 'weights': ['uniform', 'distance']},
    'knn_clf': {'n_neighbors': [3, 5, 7, 11, 15, 25], 'weights': ['uniform', 'distance']},
    'tree_reg': {'max_depth': [3, 4, 5, 6, 8, None], 'min_samples_leaf': [1, 5, 10, 20]},
    'tree_clf': {'max_depth': [3, 4, 5, 6, 8, None], 'min_samples_leaf': [1, 5, 10, 20]},
    'mlp_reg': {'hidden_layer_sizes': [(32,), (64, 32), (128, 64), (64, 64, 32)], 'alpha': [1e-4, 1e-3, 1e-2], 'learning_rate_init': [1e-3, 1e-2]},
    'mlp_clf': {'hidden_layer_sizes': [(32,), (64, 32), (128, 64), (64, 64, 32)], 'alpha': [1e-4, 1e-3, 1e-2], 'learning_rate_init': [1e-3, 1e-2]},
    'nb_clf': {'var_smoothing': [1e-9, 1e-8, 1e-7, 1e-6]},
    'mlogit': {'C': [.1, 1, 10]},
}


def _set(est, params):
    """Applique des hyperparamètres sur l'estimateur final (pipeline ou non)."""
    if hasattr(est, 'steps'):
        name = est.steps[-1][0]
        est.set_params(**{f'{name}__{k}': v for k, v in params.items()})
    else:
        est.set_params(**params)
    return est


def _candidates(mid, rng):
    grid = GRIDS.get(mid, {})
    keys = list(grid)
    total = int(np.prod([len(grid[k]) for k in keys])) if keys else 0
    cands = [{}]  # configuration par défaut
    seen = {()}
    tries = 0
    while len(cands) < min(N_CANDIDATES, total + 1) and tries < 200:
        tries += 1
        p = {k: grid[k][rng.randint(len(grid[k]))] for k in keys}
        sig = tuple(sorted((k, str(v)) for k, v in p.items()))
        if sig in seen:
            continue
        seen.add(sig)
        cands.append(p)
    return cands


def three_way_split(X, y, stratify=False, chrono=False, seed=SEED):
    """Retourne (Xtr, ytr, Xva, yva, Xte, yte)."""
    from sklearn.model_selection import train_test_split
    n = len(X)
    if chrono:
        a, b = int(n * .6), int(n * .8)
        return X.iloc[:a], y.iloc[:a], X.iloc[a:b], y.iloc[a:b], X.iloc[b:], y.iloc[b:]
    st = y if (stratify and y.value_counts().min() >= 3) else None
    Xtmp, Xte, ytmp, yte = train_test_split(X, y, test_size=.2, random_state=seed, stratify=st)
    st2 = ytmp if st is not None else None
    Xtr, Xva, ytr, yva = train_test_split(Xtmp, ytmp, test_size=.25, random_state=seed, stratify=st2)
    return Xtr, ytr, Xva, yva, Xte, yte


def _score(task, est, X, y, classes=None):
    from sklearn.metrics import r2_score, roc_auc_score, f1_score
    if task == 'reg':
        return float(r2_score(y, est.predict(X)))
    if len(classes) == 2 and hasattr(est, 'predict_proba'):
        return float(roc_auc_score(y, est.predict_proba(X)[:, 1]))
    return float(f1_score(y, est.predict(X), average='weighted'))


def _fmt_params(p):
    if not p:
        return 'paramètres par défaut'
    return ', '.join(f'{k} = {v}' for k, v in p.items())


def partition_table(r, n_tr, n_va, n_te, chrono=False, extra=''):
    tot = n_tr + n_va + n_te
    r.table('Partition des données', ['Échantillon', 'Observations', 'Part', 'Rôle'], [
        ['Apprentissage (train)', n_tr, fmt(100 * n_tr / tot, 0) + ' %', 'Estimation des paramètres du modèle'],
        ['Validation', n_va, fmt(100 * n_va / tot, 0) + ' %', 'Choix des hyperparamètres et du seuil'],
        ['Test', n_te, fmt(100 * n_te / tot, 0) + ' %', 'Évaluation finale, utilisé une seule fois']])
    r.say("Les données sont découpées " + ("chronologiquement" if chrono else "aléatoirement" + (" avec stratification des classes" if 'strat' in extra else ""))
          + " en trois échantillons : apprentissage, validation et test. Le test n'intervient jamais dans le choix du modèle.")


def tune_and_evaluate(r, mid, factory, X, y, task, classes=None, target=''):
    """
    Optimise les hyperparamètres sur la validation, ré-estime sur train+validation et évalue sur le test.
    Ajoute métriques, tables et graphiques à r. Retourne (estimateur final, X_test, y_test, prédictions test, probabilités test).
    """
    from sklearn.base import clone
    from sklearn.metrics import (mean_absolute_error, mean_squared_error, r2_score, accuracy_score, f1_score, precision_score,
                                 recall_score, roc_auc_score, roc_curve, precision_recall_curve, average_precision_score, confusion_matrix)
    rng = np.random.RandomState(SEED)
    Xtr, ytr, Xva, yva, Xte, yte = three_way_split(X, y, stratify=(task == 'clf'))
    partition_table(r, len(Xtr), len(Xva), len(Xte), extra='strat' if task == 'clf' else '')
    binary = task == 'clf' and len(classes) == 2

    # ---- optimisation sur la validation
    rows, best = [], None
    t0 = time.time()
    # sous-échantillon d'apprentissage pour la recherche si la base est grande
    if len(Xtr) > 4000:
        sub = np.random.RandomState(SEED).choice(len(Xtr), 4000, replace=False)
        Xs, ys = Xtr.iloc[sub], ytr.iloc[sub]
    else:
        Xs, ys = Xtr, ytr
    for p in _candidates(mid, rng):
        if time.time() - t0 > MAX_TUNE_SECONDS and best is not None:
            break
        try:
            est = _set(factory(), p).fit(Xs, ys)
            s_tr, s_va = _score(task, est, Xs, ys, classes), _score(task, est, Xva, yva, classes)
        except Exception:
            continue
        rows.append((p, s_tr, s_va))
        if best is None or s_va > best[2]:
            best = (p, s_tr, s_va)
    if best is None:
        raise ValueError("Aucune configuration n'a pu être estimée.")
    metric_name = 'R²' if task == 'reg' else ('AUC' if binary else 'F1 pondéré')
    rows_sorted = sorted(rows, key=lambda t: -t[2])
    r.table(f'Optimisation des hyperparamètres (mesure : {metric_name} sur la validation)',
            ['Rang', 'Paramètres', f'{metric_name} apprentissage', f'{metric_name} validation', 'Écart'],
            [[i + 1, _fmt_params(p), fmt(a, 3), fmt(b, 3), fmt(a - b, 3)] for i, (p, a, b) in enumerate(rows_sorted)])
    default_val = next((b for p, a, b in rows if not p), None)
    r.metric('BestVal', f'{metric_name} validation (meilleur)', best[2])
    if default_val is not None and best[2] > default_val + .005:
        r.say(f"L'optimisation améliore la validation de {fmt(default_val, 3)} (paramètres par défaut) à {fmt(best[2], 3)} : {_fmt_params(best[0])}.")
    else:
        r.say(f"Les paramètres par défaut sont proches de l'optimum testé ; configuration retenue : {_fmt_params(best[0])}.")
    fig, ax = plt.subplots(figsize=(7, 3.3))
    xs = np.arange(len(rows_sorted))
    ax.plot(xs, [b for _, _, b in rows_sorted], 'o-', color=NAVY, label='Validation')
    ax.plot(xs, [a for _, a, _ in rows_sorted], 's--', color=GOLD, label='Apprentissage')
    ax.set_xlabel('Configurations classées'); ax.set_ylabel(metric_name); ax.set_title('Optimisation des hyperparamètres'); ax.legend(frameon=False)
    ax.set_xticks(xs); ax.set_xticklabels([str(i + 1) for i in xs])
    fig.tight_layout()
    r.chart('Optimisation des hyperparamètres', fig)
    gap = best[1] - best[2]
    if gap > .15:
        r.warn(f"Écart apprentissage/validation important ({fmt(gap, 2)}) : risque de surapprentissage.")

    # ---- modèle final : train + validation, évalué sur le test
    Xfit, yfit = pd.concat([Xtr, Xva]), pd.concat([ytr, yva])
    final = _set(factory(), best[0]).fit(Xfit, yfit)
    pred = final.predict(Xte)
    proba = final.predict_proba(Xte) if (task == 'clf' and hasattr(final, 'predict_proba')) else None
    r.d['best_params'] = {k: str(v) for k, v in best[0].items()}

    if task == 'reg':
        r2 = r2_score(yte, pred); rmse = float(np.sqrt(mean_squared_error(yte, pred)))
        mae = mean_absolute_error(yte, pred)
        mask = yte != 0
        mape = float(np.mean(np.abs((yte[mask] - pred[mask]) / yte[mask])) * 100) if mask.sum() else None
        r2_tr = r2_score(ytr, final.predict(Xtr))
        r2_va = r2_score(yva, final.predict(Xva))
        r.metric('R2', 'R² (test)', r2)
        r.metric('RMSE', 'RMSE (test)', rmse)
        r.metric('MAE', 'MAE (test)', mae)
        r.table('Performance par échantillon', ['Échantillon', 'R²', 'RMSE', 'MAE'], [
            ['Apprentissage', fmt(r2_tr, 3), fmt(np.sqrt(mean_squared_error(ytr, final.predict(Xtr))), 3), fmt(mean_absolute_error(ytr, final.predict(Xtr)), 3)],
            ['Validation', fmt(r2_va, 3), fmt(np.sqrt(mean_squared_error(yva, final.predict(Xva))), 3), fmt(mean_absolute_error(yva, final.predict(Xva)), 3)],
            ['Test (final)', fmt(r2, 3), fmt(rmse, 3), fmt(mae, 3)]])
        if mape is not None:
            r.metric('MAPE', 'MAPE (test, %)', mape, 2)
        r.say(f"Sur l'échantillon test, jamais utilisé pour choisir le modèle, le R² est de {fmt(r2, 3)} (RMSE = {fmt(rmse, 3)}).")
        fig, ax = plt.subplots(1, 3, figsize=(12, 3.5))
        ax[0].scatter(yte, pred, s=14, color=STEEL, alpha=.6)
        lo, hi = float(min(yte.min(), pred.min())), float(max(yte.max(), pred.max()))
        ax[0].plot([lo, hi], [lo, hi], color=GOLD, lw=1.6)
        ax[0].set_xlabel('Observé'); ax[0].set_ylabel('Prédit'); ax[0].set_title('Prédit contre observé (test)')
        res_ = yte.values - pred
        ax[1].scatter(pred, res_, s=14, color=STEEL, alpha=.6)
        ax[1].axhline(0, color=GOLD, lw=1.6); ax[1].set_xlabel('Prédit'); ax[1].set_ylabel('Résidu'); ax[1].set_title('Résidus (test)')
        stats.probplot(res_, dist='norm', plot=ax[2])
        ax[2].get_lines()[0].set_markerfacecolor(STEEL); ax[2].get_lines()[0].set_markeredgecolor(STEEL); ax[2].get_lines()[0].set_markersize(4)
        ax[2].get_lines()[1].set_color(GOLD); ax[2].set_title('QQ-plot des résidus')
        fig.tight_layout()
        r.chart('Qualité de la prédiction sur le test', fig)
    else:
        avg = 'binary' if binary else 'weighted'
        kw = {'average': avg, 'zero_division': 0}
        if binary:
            kw['pos_label'] = 1
        acc = accuracy_score(yte, pred)
        r.metric('Accuracy', 'Exactitude (test)', acc)
        r.metric('Precision', 'Précision (test)', precision_score(yte, pred, **kw))
        r.metric('Recall', 'Rappel (test)', recall_score(yte, pred, **kw))
        r.metric('F1', 'F1-score (test)', f1_score(yte, pred, **kw))
        auc = None
        if proba is not None:
            try:
                auc = roc_auc_score(yte, proba[:, 1]) if binary else roc_auc_score(yte, proba, multi_class='ovr', average='weighted', labels=list(range(len(classes))))
                r.metric('AUC', 'AUC (test)', auc)
            except Exception:
                auc = None
        perf = []
        for nm, XX, yy in (('Apprentissage', Xtr, ytr), ('Validation', Xva, yva), ('Test (final)', Xte, yte)):
            pp = final.predict(XX)
            row = [nm, fmt(accuracy_score(yy, pp), 3), fmt(f1_score(yy, pp, **kw), 3)]
            if proba is not None and auc is not None:
                try:
                    pr_ = final.predict_proba(XX)
                    row.append(fmt(roc_auc_score(yy, pr_[:, 1]) if binary else roc_auc_score(yy, pr_, multi_class='ovr', average='weighted', labels=list(range(len(classes)))), 3))
                except Exception:
                    row.append('—')
            perf.append(row)
        r.table('Performance par échantillon', ['Échantillon', 'Exactitude', 'F1'] + (['AUC'] if proba is not None and auc is not None else []), perf)
        base = max(np.bincount(np.asarray(yte, dtype=int))) / len(yte)
        r.say(f"Sur le test, le modèle classe correctement {fmt(acc * 100, 1)} % des observations (référence « classe majoritaire » : {fmt(base * 100, 1)} %).")
        if acc <= base + .02:
            r.warn("L'exactitude ne dépasse pas la classe majoritaire : le modèle apporte peu d'information.")
        if auc is not None:
            qual = 'excellent' if auc >= .9 else ('bon' if auc >= .8 else ('moyen' if auc >= .7 else 'faible'))
            r.say(f"L'AUC de {fmt(auc, 3)} indique un pouvoir discriminant {qual}.")
        cm = confusion_matrix(yte, pred, labels=list(range(len(classes))))
        r.table('Matrice de confusion du test (lignes : réel, colonnes : prédit)', ['Réel \\ Prédit'] + [str(c) for c in classes],
                [[str(classes[i])] + [int(v) for v in cm[i]] for i in range(len(classes))])
        n_fig = 3 if (proba is not None) else 1
        fig, ax = plt.subplots(1, n_fig, figsize=(4.4 * n_fig, 3.7))
        ax = np.atleast_1d(ax)
        ax[0].imshow(cm, cmap='Blues'); ax[0].grid(False)
        ax[0].set_xticks(range(len(classes))); ax[0].set_yticks(range(len(classes)))
        ax[0].set_xticklabels([str(c) for c in classes], rotation=30); ax[0].set_yticklabels([str(c) for c in classes])
        for i in range(len(classes)):
            for j in range(len(classes)):
                ax[0].text(j, i, int(cm[i, j]), ha='center', va='center', color='white' if cm[i, j] > cm.max() / 2 else NAVY)
        ax[0].set_ylim(len(classes) - 0.5, -0.5); ax[0].set_xlim(-0.5, len(classes) - 0.5)
        ax[0].set_title('Matrice de confusion (test)')
        if proba is not None:
            if binary:
                for nm, XX, yy, col in (('Apprentissage', Xtr, ytr, GREY), ('Validation', Xva, yva, GOLD), ('Test', Xte, yte, NAVY)):
                    pr_ = final.predict_proba(XX)[:, 1]
                    f, t, _ = roc_curve(yy, pr_)
                    ax[1].plot(f, t, color=col, lw=2 if nm == 'Test' else 1.2, label=f'{nm} (AUC = {roc_auc_score(yy, pr_):.3f})')
                ax[1].plot([0, 1], [0, 1], color='#cbd5e1', ls='--')
                ax[1].set_xlabel('Taux de faux positifs'); ax[1].set_ylabel('Taux de vrais positifs'); ax[1].set_title('Courbes ROC'); ax[1].legend(loc='lower right', fontsize=7, frameon=False)
                pr_, rc_, _ = precision_recall_curve(yte, proba[:, 1])
                ax[2].plot(rc_, pr_, color=NAVY, lw=2, label=f'AP = {average_precision_score(yte, proba[:, 1]):.3f}')
                ax[2].axhline(float(np.mean(yte)), color=GREY, ls='--', label='Hasard')
                ax[2].set_xlabel('Rappel'); ax[2].set_ylabel('Précision'); ax[2].set_title('Courbe précision-rappel'); ax[2].legend(frameon=False, fontsize=8)
            else:
                cols = [NAVY, STEEL, GOLD, '#5b8c85', GREY, RED, '#6a5d9a', '#b87a3d']
                for k, c in enumerate(classes[:8]):
                    yb = (np.asarray(yte) == k).astype(int)
                    if 0 < yb.sum() < len(yb):
                        f, t, _ = roc_curve(yb, proba[:, k])
                        ax[1].plot(f, t, color=cols[k % 8], lw=1.6, label=f'{c} (AUC = {roc_auc_score(yb, proba[:, k]):.2f})')
                        p_, r_, _ = precision_recall_curve(yb, proba[:, k])
                        ax[2].plot(r_, p_, color=cols[k % 8], lw=1.6, label=str(c))
                ax[1].plot([0, 1], [0, 1], color='#cbd5e1', ls='--')
                ax[1].set_title('Courbes ROC (une classe contre les autres)'); ax[1].legend(fontsize=7, frameon=False, loc='lower right')
                ax[1].set_xlabel('Faux positifs'); ax[1].set_ylabel('Vrais positifs')
                ax[2].set_title('Précision-rappel par classe'); ax[2].set_xlabel('Rappel'); ax[2].set_ylabel('Précision'); ax[2].legend(fontsize=7, frameon=False)
        fig.tight_layout()
        r.chart('Matrice de confusion, courbes ROC et précision-rappel (test)', fig)
        # seuil optimal sur la validation (binaire)
        if binary and proba is not None:
            try:
                pv = final.predict_proba(Xva)[:, 1]
                ths = np.linspace(.05, .95, 19)
                f1s = [f1_score(yva, (pv >= t).astype(int), zero_division=0) for t in ths]
                th = float(ths[int(np.argmax(f1s))])
                pt = (proba[:, 1] >= th).astype(int)
                r.table('Seuil de décision optimisé sur la validation (maximisation du F1)', ['Seuil', 'Exactitude (test)', 'Précision (test)', 'Rappel (test)', 'F1 (test)'],
                        [['0,50', fmt(accuracy_score(yte, pred), 3), fmt(precision_score(yte, pred, zero_division=0), 3), fmt(recall_score(yte, pred, zero_division=0), 3), fmt(f1_score(yte, pred, zero_division=0), 3)],
                         [fmt(th, 2), fmt(accuracy_score(yte, pt), 3), fmt(precision_score(yte, pt, zero_division=0), 3), fmt(recall_score(yte, pt, zero_division=0), 3), fmt(f1_score(yte, pt, zero_division=0), 3)]])
            except Exception:
                pass

    # ---- courbe d'apprentissage
    try:
        from sklearn.model_selection import learning_curve
        Xl, yl = Xfit, yfit
        if len(Xl) > 2500:
            sub = np.random.RandomState(SEED).choice(len(Xl), 2500, replace=False)
            Xl, yl = Xl.iloc[sub], yl.iloc[sub]
        sizes, trs, vas = learning_curve(_set(factory(), best[0]), Xl, yl, cv=3, train_sizes=np.linspace(.2, 1, 5),
                                         scoring='r2' if task == 'reg' else ('roc_auc' if binary else 'f1_weighted'), n_jobs=1, random_state=SEED, shuffle=True)
        fig, ax = plt.subplots(figsize=(6.4, 3.4))
        ax.plot(sizes, trs.mean(1), 'o-', color=GOLD, label='Apprentissage')
        ax.fill_between(sizes, trs.mean(1) - trs.std(1), trs.mean(1) + trs.std(1), color=GOLD, alpha=.15)
        ax.plot(sizes, vas.mean(1), 'o-', color=NAVY, label='Validation croisée')
        ax.fill_between(sizes, vas.mean(1) - vas.std(1), vas.mean(1) + vas.std(1), color=NAVY, alpha=.15)
        ax.set_xlabel('Taille de l\'échantillon d\'apprentissage'); ax.set_ylabel(metric_name); ax.set_title('Courbe d\'apprentissage'); ax.legend(frameon=False)
        fig.tight_layout()
        r.chart('Courbe d\'apprentissage', fig)
        if vas.mean(1)[-1] - vas.mean(1)[-2] > .02:
            r.say("La courbe d'apprentissage progresse encore avec la taille de l'échantillon : davantage de données amélioreraient probablement le modèle.")
    except Exception:
        pass
    return final, Xte, yte, pred, proba


# ---------------------------------------------------------------------------------------------
# Séries temporelles : partition chronologique 70 / 15 / 15
# ---------------------------------------------------------------------------------------------
def evaluate_ts_split(r, series, meta, kind='arima', max_obs=400):
    """Sélection de l'ordre sur la validation, ré-estimation sur train+validation, évaluation sur le test."""
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from models.analysis import stationarity, detect_seasonality
    import itertools
    y = series.dropna().iloc[-max_obs:].reset_index(drop=True)
    n = len(y)
    if n < 40:
        r.warn("Série trop courte pour une partition train / validation / test (minimum 40 observations).")
        return
    a, b = int(n * .70), int(n * .85)
    ytr, yva, yte = y.iloc[:a], y.iloc[a:b], y.iloc[b:]
    partition_table(r, len(ytr), len(yva), len(yte), chrono=True)
    d = stationarity(ytr)['d']
    per = meta.get('period')
    if per and (len(ytr) < 3 * per or not detect_seasonality((ytr.diff(d).dropna().values if d else ytr.values), [per])[0]):
        per = None
    specs = [((p, d, q), (0, 0, 0, 0)) for p, q in itertools.product(range(3), range(3)) if not (p == 0 and q == 0 and d == 0)]
    if per:
        specs += [((1, d, 0), (0, 1, 1, per)), ((0, d, 1), (0, 1, 1, per)), ((1, d, 1), (0, 1, 1, per))]

    def rolling(res0, series_new):
        preds = []
        cur = res0
        for i in range(len(series_new)):
            preds.append(float(cur.forecast(1).iloc[0]))
            cur = cur.append(series_new.iloc[i:i + 1], refit=False)
        return np.array(preds)

    rows, best = [], None
    t0 = time.time()
    for order, seas in specs:
        if time.time() - t0 > 40 and best is not None:
            break
        try:
            m = SARIMAX(ytr, order=order, seasonal_order=seas, trend='c' if d == 0 else 'n').fit(disp=False, maxiter=100)
            pv = rolling(m, yva)
            rmse = float(np.sqrt(np.mean((yva.values - pv) ** 2)))
            lbl = f'ARIMA{order}' if seas[3] == 0 else f'SARIMA{order}x{seas}'
            rows.append((lbl, order, seas, rmse, float(np.mean(np.abs(yva.values - pv)))))
            if best is None or rmse < best[3]:
                best = rows[-1]
        except Exception:
            continue
    if best is None:
        r.warn("La sélection sur validation n'a pas pu être réalisée.")
        return
    rows.sort(key=lambda t: t[3])
    r.table('Sélection de l\'ordre sur l\'échantillon de validation (prévision à un pas)', ['Rang', 'Modèle', 'RMSE validation', 'MAE validation'],
            [[i + 1, t[0], fmt(t[3], 3), fmt(t[4], 3)] for i, t in enumerate(rows[:8])])
    # modèle final : train + validation, évalué sur le test
    ytv = pd.concat([ytr, yva]).reset_index(drop=True)
    m = SARIMAX(ytv, order=best[1], seasonal_order=best[2], trend='c' if d == 0 else 'n').fit(disp=False, maxiter=100)
    pt = rolling(m, yte)
    err = yte.values - pt
    naive = np.concatenate([[ytv.iloc[-1]], yte.values[:-1]])
    en = yte.values - naive
    rm = lambda e: float(np.sqrt(np.mean(np.square(e))))
    mape = float(np.mean(np.abs(err / np.where(yte.values == 0, np.nan, yte.values))) * 100) if (yte.values != 0).all() else None
    r.metric('RMSEtest', 'RMSE (test)', rm(err), 3)
    r.metric('MAEtest', 'MAE (test)', float(np.mean(np.abs(err))), 3)
    if mape is not None:
        r.metric('MAPEtest', 'MAPE (test, %)', mape, 2)
    r.metric('Theil', 'U de Theil (test)', rm(err) / rm(en) if rm(en) else float('nan'), 3, 'inférieur à 1 : meilleur que le modèle naïf')
    r.table('Évaluation finale sur le test', ['Méthode', 'RMSE', 'MAE'], [
        [best[0] + ' (retenu sur validation)', fmt(rm(err), 3), fmt(np.mean(np.abs(err)), 3)],
        ['Naïf (dernière valeur)', fmt(rm(en), 3), fmt(np.mean(np.abs(en)), 3)]])
    if rm(err) < rm(en):
        r.say(f"Sur le test, {best[0]} réduit l'erreur de {fmt(100 * (1 - rm(err) / rm(en)), 1)} % par rapport à la prévision naïve.")
    else:
        r.warn("Sur le test, le modèle ne fait pas mieux que la prévision naïve (dernière valeur).")
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(range(n), y.values, color=NAVY, lw=1.2, label='Observé')
    ax.plot(range(b, n), pt, color=GOLD, lw=2, label='Prévision test')
    ax.axvline(a, color=GREY, ls='--'); ax.axvline(b, color=GREY, ls='--')
    ymax = ax.get_ylim()[1]
    ax.text(a / 2, ymax, 'Apprentissage', ha='center', va='top', fontsize=8, color=GREY)
    ax.text((a + b) / 2, ymax, 'Validation', ha='center', va='top', fontsize=8, color=GREY)
    ax.text((b + n) / 2, ymax, 'Test', ha='center', va='top', fontsize=8, color=GREY)
    ax.set_title('Partition chronologique et prévision sur le test'); ax.legend(frameon=False, loc='lower left')
    fig.tight_layout()
    r.chart('Partition chronologique et prévision sur le test', fig)


# ---------------------------------------------------------------------------------------------
# Volatilité : partition chronologique 70 / 15 / 15
# ---------------------------------------------------------------------------------------------
def evaluate_vol_split(r, ret):
    """Sélection du modèle (famille et loi) sur la validation ; évaluation de la variance prévue sur le test."""
    from arch import arch_model
    x = pd.Series(ret).dropna().reset_index(drop=True)
    n = len(x)
    if n < 150:
        r.warn("Série trop courte pour une partition train / validation / test (minimum 150 observations).")
        return
    a, b = int(n * .70), int(n * .85)
    partition_table(r, a, b - a, n - b, chrono=True)
    specs = [('GARCH(1,1)', dict(vol='GARCH', p=1, q=1)), ('GJR-GARCH(1,1,1)', dict(vol='GARCH', p=1, o=1, q=1)), ('EGARCH(1,1)', dict(vol='EGARCH', p=1, o=1, q=1))]

    def qlike(r2, s2):
        s2 = np.maximum(s2, 1e-10)
        return float(np.mean(np.log(s2) + r2 / s2))

    rows, best = [], None
    for lbl, kw in specs:
        for dist in ('normal', 't', 'skewt'):
            try:
                mod = arch_model(x, mean='Constant', dist=dist, **kw)
                res = mod.fit(last_obs=a, disp='off', show_warning=False)
                full = mod.fix(res.params)
                s2 = full.conditional_volatility.values ** 2
                mu = float(res.params['mu'])
                e2 = (x.values - mu) ** 2
                v = (qlike(e2[a:b], s2[a:b]), float(np.mean((e2[a:b] - s2[a:b]) ** 2)))
                rows.append((lbl, dist, v[0], v[1], kw, res.params, mu))
                if best is None or v[0] < best[2]:
                    best = rows[-1]
            except Exception:
                continue
    if best is None:
        r.warn("La sélection sur validation n'a pas pu être réalisée.")
        return
    rows.sort(key=lambda t: t[2])
    r.table('Sélection du modèle sur l\'échantillon de validation (perte QLIKE de la variance prévue)', ['Rang', 'Modèle', 'Loi', 'QLIKE validation', 'EQM validation'],
            [[i + 1, t[0], t[1], fmt(t[2], 4), fmt(t[3], 4)] for i, t in enumerate(rows[:8])])
    mod = arch_model(x, mean='Constant', dist=best[1], **best[4])
    res = mod.fit(last_obs=b, disp='off', show_warning=False)       # ré-estimé sur apprentissage + validation
    full = mod.fix(res.params)
    s2 = full.conditional_volatility.values ** 2
    mu = float(res.params['mu'])
    e2 = (x.values - mu) ** 2
    const = np.full(n - b, e2[:b].mean())
    q_m, q_c = qlike(e2[b:], s2[b:]), qlike(e2[b:], const)
    mse_m, mse_c = float(np.mean((e2[b:] - s2[b:]) ** 2)), float(np.mean((e2[b:] - const) ** 2))
    r.metric('QLIKEtest', 'QLIKE (test)', q_m, 4, 'plus faible = meilleur')
    r.metric('MSEvar', 'EQM de la variance (test)', mse_m, 4)
    r.table('Évaluation finale sur le test', ['Prévision de la variance', 'QLIKE', 'EQM'],
            [[f'{best[0]} ({best[1]}), retenu sur validation', fmt(q_m, 4), fmt(mse_m, 4)], ['Variance constante (référence)', fmt(q_c, 4), fmt(mse_c, 4)]])
    if q_m < q_c:
        r.say("Sur le test, la variance prévue par le modèle est plus proche de la variance réalisée que celle d'une variance constante.")
    else:
        r.warn("Sur le test, le modèle de volatilité ne fait pas mieux qu'une variance constante.")
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(range(n), np.abs(x.values - mu), color='#cbd5e1', lw=.7, label='|rendement − moyenne|')
    ax.plot(range(n), np.sqrt(s2), color=NAVY, lw=1.2, label='Volatilité prévue à un pas')
    ax.axvline(a, color=GREY, ls='--'); ax.axvline(b, color=GREY, ls='--')
    ax.set_title('Volatilité prévue : apprentissage, validation (à gauche du second trait) et test (à droite)'); ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    r.chart('Volatilité prévue hors échantillon', fig)


def evaluate_hw_split(r, series, meta, max_obs=400):
    """Holt-Winters : configuration choisie sur la validation (prévision multi-pas), évaluée sur le test."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    y = series.dropna().iloc[-max_obs:].reset_index(drop=True)
    n = len(y)
    if n < 40:
        r.warn("Série trop courte pour une partition train / validation / test (minimum 40 observations).")
        return
    a, b = int(n * .70), int(n * .85)
    ytr, yva, yte = y.iloc[:a], y.iloc[a:b], y.iloc[b:]
    partition_table(r, len(ytr), len(yva), len(yte), chrono=True)
    per = meta.get('period')
    cfgs = []
    for trend in (None, 'add'):
        for damped in ((False,) if trend is None else (False, True)):
            for seas in ((None, 'add') if per and len(ytr) >= 2 * per else (None,)):
                cfgs.append((trend, damped, seas))
    rows, best = [], None
    for trend, damped, seas in cfgs:
        try:
            m = ExponentialSmoothing(ytr, trend=trend, damped_trend=damped, seasonal=seas, seasonal_periods=per if seas else None).fit()
            pv = np.asarray(m.forecast(len(yva)))
            rmse = float(np.sqrt(np.mean((yva.values - pv) ** 2)))
            lbl = f"tendance {('amortie' if damped else 'linéaire') if trend else 'aucune'}, saisonnalité {'additive' if seas else 'aucune'}"
            rows.append((lbl, trend, damped, seas, rmse, float(np.mean(np.abs(yva.values - pv)))))
            if best is None or rmse < best[4]:
                best = rows[-1]
        except Exception:
            continue
    if best is None:
        r.warn("La sélection sur validation n'a pas pu être réalisée.")
        return
    rows.sort(key=lambda t: t[4])
    r.table('Sélection de la configuration sur la validation (prévision sur tout l\'horizon de validation)', ['Rang', 'Configuration', 'RMSE validation', 'MAE validation'],
            [[i + 1, t[0], fmt(t[4], 3), fmt(t[5], 3)] for i, t in enumerate(rows)])
    ytv = pd.concat([ytr, yva]).reset_index(drop=True)
    m = ExponentialSmoothing(ytv, trend=best[1], damped_trend=best[2], seasonal=best[3], seasonal_periods=per if best[3] else None).fit()
    pt = np.asarray(m.forecast(len(yte)))
    err = yte.values - pt
    naive = np.full(len(yte), ytv.iloc[-1])
    rm = lambda e: float(np.sqrt(np.mean(np.square(e))))
    r.metric('RMSEtest', 'RMSE (test)', rm(err), 3)
    r.metric('MAEtest', 'MAE (test)', float(np.mean(np.abs(err))), 3)
    r.table('Évaluation finale sur le test', ['Méthode', 'RMSE', 'MAE'], [
        [f'Holt-Winters ({best[0]})', fmt(rm(err), 3), fmt(np.mean(np.abs(err)), 3)],
        ['Naïf (dernière valeur)', fmt(rm(yte.values - naive), 3), fmt(np.mean(np.abs(yte.values - naive)), 3)]])
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(range(n), y.values, color=NAVY, lw=1.2, label='Observé')
    ax.plot(range(b, n), pt, color=GOLD, lw=2, label='Prévision test')
    ax.axvline(a, color=GREY, ls='--'); ax.axvline(b, color=GREY, ls='--')
    ax.set_title('Partition chronologique et prévision sur le test'); ax.legend(frameon=False, loc='lower left')
    fig.tight_layout()
    r.chart('Partition chronologique et prévision sur le test', fig)
