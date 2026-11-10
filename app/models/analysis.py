#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analyse automatique d'un jeu de données et recommandation de modèles.

A partir d'un dataframe, d'une variable cible et de variables explicatives, ce module :
  1. profile les colonnes (numérique, binaire, catégorielle, date...),
  2. détecte la structure (coupe transversale, série temporelle, panel),
  3. calcule des diagnostics (stationnarité, effet ARCH, multicolinéarité, non-linéarité...),
  4. classe les modèles adaptés avec un score et les raisons du choix.
"""

import re
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

TIME_NAMES = re.compile(
    r'(^|[_\s])(date|time|temps|annee|année|year|an|mois|month|trimestre|quarter|periode|période|jour|day|semaine|week)($|[_\s])',
    re.I)
ENTITY_NAMES = re.compile(
    r'(^|[_\s])(id|code|pays|country|firme|firm|entreprise|company|region|région|ville|city|individu|menage|ménage|'
    r'banque|bank|district|departement|département|zone|entity|unite|unité|nom|name|iso|sujet|subject)($|[_\s])',
    re.I)

FAMILY_LABELS = {
    'regression': 'Modèles de régression',
    'panel': 'Modèles de panel',
    'timeseries': 'Séries temporelles (stationnarité)',
    'volatility': 'Modèles de volatilité',
    'classification': 'Modèles de classification',
    'ml': 'Machine learning',
    'deep': 'Deep learning',
}
FAMILY_ORDER = ['timeseries', 'volatility', 'panel', 'regression', 'classification', 'ml', 'deep']


# ----------------------------------------------------------------------------
# Profil des colonnes
# ----------------------------------------------------------------------------
def _is_datetime_like(s):
    if pd.api.types.is_datetime64_any_dtype(s):
        return True
    if s.dtype == object:
        sample = s.dropna().astype(str).head(200)
        if len(sample) == 0:
            return False
        if sample.str.fullmatch(r'-?\d+(\.\d+)?').mean() > 0.5:
            return False
        parsed = pd.to_datetime(sample, errors='coerce')
        return parsed.notna().mean() > 0.9
    return False


def _is_integer_valued(s):
    s = pd.to_numeric(s, errors='coerce').dropna()
    return len(s) > 0 and bool(np.all(np.isclose(s, np.round(s))))


def column_kind(s):
    nun = s.nunique(dropna=True)
    if _is_datetime_like(s):
        return 'datetime'
    if pd.api.types.is_bool_dtype(s):
        return 'binary'
    if pd.api.types.is_numeric_dtype(s):
        return 'binary' if nun == 2 else 'numeric'
    if nun == 2:
        return 'binary'
    if nun <= 50:
        return 'categorical'
    return 'text'


def profile_columns(df):
    out = []
    for c in df.columns:
        s = df[c]
        nun = int(s.nunique(dropna=True))
        kind = column_kind(s)
        ex = s.dropna()
        out.append({
            'name': str(c),
            'dtype': str(s.dtype),
            'kind': kind,
            'n_unique': nun,
            'missing_pct': round(float(s.isna().mean() * 100), 1),
            'discrete': bool(kind == 'numeric' and nun <= 10 and _is_integer_valued(s)),
            'example': (str(ex.iloc[0])[:30] if len(ex) else ''),
        })
    return out


def detect_structure_columns(df, prof=None):
    """Détecte les colonnes temps et entité (panel) les plus probables."""
    prof = prof or profile_columns(df)
    kinds = {p['name']: p for p in prof}
    n = len(df)

    time_cands = []
    for p in prof:
        c = p['name']
        if p['kind'] == 'datetime':
            time_cands.append((0, c))
        elif p['kind'] == 'numeric' and TIME_NAMES.search(c) and _is_integer_valued(df[c]) and p['n_unique'] >= 3:
            time_cands.append((1, c))
    time_cands.sort()

    ent_cands = []
    for p in prof:
        c = p['name']
        if p['kind'] in ('categorical', 'text', 'binary') or (p['kind'] == 'numeric' and ENTITY_NAMES.search(c)):
            if 2 <= p['n_unique'] < n / 2:
                ent_cands.append((0 if ENTITY_NAMES.search(c) else 1, c))
    ent_cands.sort()

    best = None
    for _, t in time_cands:
        for _, e in ent_cands:
            if e == t:
                continue
            sub = df[[e, t]].dropna()
            if len(sub) == 0 or sub.duplicated().any():
                continue
            if sub[e].nunique() >= 2 and len(sub) / sub[e].nunique() >= 2:
                best = (e, t)
                break
        if best:
            break

    time_col = best[1] if best else (time_cands[0][1] if time_cands else None)
    entity_col = best[0] if best else None
    return {'time_col': time_col, 'entity_col': entity_col, 'panel': bool(best)}


# ----------------------------------------------------------------------------
# Préparation des données
# ----------------------------------------------------------------------------
def prepare_xy(df, target, features, max_rows=20000, keep_index=False, extra_cols=None):
    """Retourne X (numérique, variables catégorielles encodées), y, notes."""
    notes = []
    cols = [target] + list(features) + list(extra_cols or [])
    d = df[cols].copy()
    d = d.dropna()
    if len(d) > max_rows:
        d = d.sample(max_rows, random_state=42)
        notes.append(f"Échantillon aléatoire de {max_rows} observations utilisé pour limiter le temps de calcul.")
    y = d[target]
    X = d[list(features)].copy()
    keep_cat = []
    for c in X.columns:
        if not pd.api.types.is_numeric_dtype(X[c]) or X[c].dtype == bool:
            if X[c].nunique() > 20:
                notes.append(f"La variable « {c} » a trop de modalités ({X[c].nunique()}) et a été ignorée.")
                X = X.drop(columns=[c])
            else:
                keep_cat.append(c)
    if keep_cat:
        X = pd.get_dummies(X, columns=keep_cat, drop_first=True, dtype=float)
    X = X.apply(pd.to_numeric, errors='coerce').astype(float)
    const = [c for c in X.columns if X[c].nunique() <= 1]
    if const:
        X = X.drop(columns=const)
        notes.append("Variables constantes retirées : " + ", ".join(const))
    ok = X.notna().all(axis=1)
    X, y = X[ok], y[ok]
    if not keep_index:
        X = X.reset_index(drop=True)
        y = y.reset_index(drop=True)
    return X, y, notes, d


def prepare_series(df, target, time_col=None):
    """Construit une série temporelle ordonnée et ses métadonnées."""
    meta = {'freq': None, 'period': None, 'dates': None, 'step': None, 'notes': []}
    s = pd.to_numeric(df[target], errors='coerce')
    if time_col and time_col in df.columns:
        t = df[time_col]
        if _is_datetime_like(t):
            t = pd.to_datetime(t, errors='coerce')
        else:
            tn = pd.to_numeric(t, errors='coerce')
            if tn.notna().all() and tn.between(1800, 2200).all() and _is_integer_valued(tn):
                t = pd.to_datetime(tn.astype(int).astype(str), format='%Y', errors='coerce')
            else:
                t = tn
        d = pd.DataFrame({'t': t, 'y': s}).dropna()
        if d['t'].duplicated().any():
            meta['notes'].append("Plusieurs observations par date : moyenne calculée pour chaque date.")
            d = d.groupby('t', as_index=True)['y'].mean().reset_index()
        d = d.sort_values('t')
        series = pd.Series(d['y'].values, index=pd.Index(d['t'].values))
        if pd.api.types.is_datetime64_any_dtype(series.index) and len(series) >= 4:
            idx = pd.DatetimeIndex(series.index)
            freq = None
            try:
                freq = pd.infer_freq(idx)
            except Exception:
                freq = None
            if freq:
                series.index = pd.DatetimeIndex(idx, freq=freq)
                meta['freq'] = freq
                f = freq.upper()
                if f.startswith('M') or f.startswith('MS') or f == 'ME':
                    meta['period'] = 12
                elif f.startswith('Q'):
                    meta['period'] = 4
                elif f.startswith('W'):
                    meta['period'] = 52
                elif f.startswith('D') or f == 'B':
                    meta['period'] = 7 if not f.startswith('B') else 5
                elif f.startswith('H'):
                    meta['period'] = 24
            else:
                meta['notes'].append("Fréquence temporelle irrégulière : les dates sont utilisées seulement pour l'affichage.")
            meta['dates'] = idx
            diffs = np.diff(idx.values).astype('timedelta64[s]').astype(float)
            meta['step'] = pd.Timedelta(seconds=float(np.median(diffs))) if len(diffs) else None
            if not freq:
                series = pd.Series(series.values, index=pd.RangeIndex(len(series)))
        else:
            series = pd.Series(series.values.astype(float), index=pd.RangeIndex(len(series)))
    else:
        series = s.dropna().reset_index(drop=True)
        meta['notes'].append("Aucune colonne de temps : l'ordre des lignes est utilisé comme ordre chronologique.")
    series = series.astype(float)
    return series, meta


def detect_seasonality(x, candidates):
    """Retourne (période, force) ou (None, 0) à partir de l'autocorrélation."""
    from statsmodels.tsa.stattools import acf
    x = np.asarray(x, dtype=float)
    n = len(x)
    best, best_val = None, 0.0
    cands = sorted({int(m) for m in candidates if m and 2 <= m <= n // 3})
    if not cands:
        return None, 0.0
    try:
        a = acf(x, nlags=max(cands) + 1, fft=True)
    except Exception:
        return None, 0.0
    thr = 1.96 / np.sqrt(n)
    for m in cands:
        if m >= len(a):
            continue
        v = a[m]
        left = a[m - 1] if m - 1 < len(a) else 0
        right = a[m + 1] if m + 1 < len(a) else 0
        if v > max(thr, 0.15) and v >= left and v >= right and v > best_val:
            best, best_val = m, float(v)
    return best, best_val


def stationarity(series):
    """Tests ADF et KPSS, et ordre d'intégration d conseillé (0, 1 ou 2)."""
    from statsmodels.tsa.stattools import adfuller, kpss
    x = pd.Series(series).dropna().astype(float)
    out = {'adf_p': None, 'kpss_p': None, 'd': 0, 'stationary': True}

    def tests(v):
        try:
            a = adfuller(v, autolag='AIC')[1]
        except Exception:
            a = None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                k = kpss(v, regression='c', nlags='auto')[1]
        except Exception:
            k = None
        return a, k

    a, k = tests(x)
    out['adf_p'], out['kpss_p'] = a, k

    def is_stat(a_, k_):
        if a_ is None:
            return True
        if k_ is None:
            return a_ < 0.05
        return a_ < 0.05 and k_ > 0.05

    d = 0
    cur = x
    a_, k_ = a, k
    while not is_stat(a_, k_) and d < 2 and len(cur) > 12:
        cur = cur.diff().dropna()
        d += 1
        a_, k_ = tests(cur)
    out['d'] = d
    out['stationary'] = (d == 0)
    return out


def arch_effect(x, nlags=None):
    from statsmodels.stats.diagnostic import het_arch
    x = np.asarray(pd.Series(x).dropna(), dtype=float)
    if len(x) < 40:
        return None
    nlags = nlags or int(min(10, max(2, len(x) // 10)))
    try:
        return float(het_arch(x - x.mean(), nlags=nlags)[1])
    except Exception:
        return None


def volatility_input(series):
    """Retourne (rendements en %, description) utilisables pour un modèle GARCH."""
    s = pd.Series(series).dropna().astype(float)
    positive = bool((s > 0).all())
    st = stationarity(s)
    if positive and not st['stationary']:
        r = 100 * np.log(s).diff().dropna()
        return r.reset_index(drop=True), "Rendements logarithmiques en % calculés à partir des niveaux (série de type prix)."
    r = s - 0.0
    if r.std() < 0.1:
        return (r * 100).reset_index(drop=True), "Série supposée déjà en rendements ; mise à l'échelle ×100."
    return r.reset_index(drop=True), "Série utilisée telle quelle comme rendements."


def _vif_max(X):
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    Xn = X.copy()
    if Xn.shape[1] < 2:
        return None
    Xn = Xn.iloc[:, :30]
    Xn = (Xn - Xn.mean()) / Xn.std().replace(0, 1)
    Xn = Xn.assign(const=1.0)
    best = 0.0
    try:
        for i in range(Xn.shape[1] - 1):
            v = variance_inflation_factor(Xn.values, i)
            if np.isfinite(v):
                best = max(best, float(v))
            else:
                best = max(best, 1e6)
    except Exception:
        return None
    return best


def _benchmark(X, y, kind):
    """Compare un modèle linéaire et une forêt aléatoire en validation croisée."""
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.linear_model import LinearRegression, LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    if len(X) > 3000:
        idx = np.random.RandomState(42).choice(len(X), 3000, replace=False)
        X, y = X.iloc[idx], y.iloc[idx]
    try:
        if kind == 'continuous':
            lin = cross_val_score(make_pipeline(StandardScaler(), LinearRegression()), X, y, cv=3, scoring='r2').mean()
            rf = cross_val_score(RandomForestRegressor(n_estimators=60, max_depth=8, random_state=42, n_jobs=1), X, y, cv=3, scoring='r2').mean()
        else:
            lin = cross_val_score(make_pipeline(StandardScaler(), LogisticRegression(max_iter=500)), X, y, cv=3, scoring='accuracy').mean()
            rf = cross_val_score(RandomForestClassifier(n_estimators=60, max_depth=8, random_state=42, n_jobs=1), X, y, cv=3, scoring='accuracy').mean()
        return float(lin), float(rf)
    except Exception:
        return None, None


# ----------------------------------------------------------------------------
# Contexte du problème
# ----------------------------------------------------------------------------
def _fmt_p(p):
    if p is None:
        return 'n.d.'
    return '< 0,001' if p < 0.001 else f'{p:.3f}'.replace('.', ',')


def analyze_problem(df, target, features, time_col=None, entity_col=None):
    prof = profile_columns(df)
    pk = {p['name']: p for p in prof}
    if target not in pk:
        raise ValueError(f"Variable cible introuvable : {target}")
    features = [f for f in features if f in pk and f != target and f not in (time_col, entity_col)]

    ctx = {
        'n': int(len(df)), 'target': target, 'features': features,
        'time_col': time_col or None, 'entity_col': entity_col or None,
        'diagnostics': [], 'notes': [],
    }

    def diag(label, value, status='info'):
        ctx['diagnostics'].append({'label': label, 'value': value, 'status': status})

    # --- type de la cible
    tp = pk[target]
    y = df[target].dropna()
    ctx['n_used'] = int(len(y))
    kind = None
    ambiguous = False
    is_count = False
    if tp['kind'] == 'binary':
        kind = 'binary'
    elif tp['kind'] == 'numeric':
        yn = pd.to_numeric(y, errors='coerce').dropna()
        if tp['discrete'] and tp['n_unique'] >= 3 and float(yn.min()) >= 0:
            kind = 'multiclass'
            ambiguous = True
            is_count = float(yn.min()) == 0
        else:
            kind = 'continuous'
            if _is_integer_valued(yn) and float(yn.min()) >= 0 and tp['n_unique'] > 10:
                is_count = True
    elif tp['kind'] == 'categorical':
        kind = 'multiclass'
    else:
        raise ValueError("La variable cible doit être numérique ou catégorielle (peu de modalités).")
    ctx['target_kind'] = kind
    ctx['ambiguous'] = ambiguous
    ctx['is_count'] = is_count
    labels = {'continuous': 'Quantitative continue', 'binary': 'Binaire (deux modalités)',
              'multiclass': 'Catégorielle à plusieurs classes'}
    diag('Nature de la variable cible', labels[kind] + (' (entiers positifs : comptage possible)' if is_count else ''))
    if ambiguous:
        diag('Cible discrète', f"{tp['n_unique']} valeurs entières : traitée comme des classes ; la régression reste possible si c'est une quantité.", 'warn')

    # --- structure
    pk_time = pk.get(time_col) if time_col else None
    structure = 'cross_section'
    if entity_col and time_col and entity_col in pk and time_col in pk:
        sub = df[[entity_col, time_col]].dropna()
        if not sub.duplicated().any() and sub[entity_col].nunique() >= 2:
            structure = 'panel'
        else:
            ctx['notes'].append("Les couples (entité, temps) ne sont pas uniques : la structure panel n'a pas été retenue.")
    if structure != 'panel':
        if time_col and time_col in pk:
            structure = 'time_series'
        elif not features and kind == 'continuous':
            structure = 'time_series'
            ctx['time_assumed'] = True
    ctx['structure'] = structure
    names = {'cross_section': 'Coupe transversale', 'time_series': 'Série temporelle', 'panel': 'Données de panel'}
    if structure == 'panel':
        n_ent = int(df[entity_col].nunique())
        diag('Structure des données', f"{names[structure]} : {n_ent} entités (« {entity_col} ») observées dans le temps (« {time_col} »)", 'ok')
    elif structure == 'time_series':
        extra = f" (colonne « {time_col} »)" if time_col else ' (ordre des lignes)'
        diag('Structure des données', names[structure] + extra, 'ok')
    else:
        diag('Structure des données', names[structure], 'ok')
    diag('Taille de l\'échantillon', f"{ctx['n_used']} observations, {len(features)} variable(s) explicative(s)")

    # --- diagnostics selon le cas
    ctx['series_tests'] = None

    if structure == 'time_series' and kind == 'continuous':
        series, meta = prepare_series(df, target, time_col)
        ctx['series_len'] = int(len(series))
        st = stationarity(series) if len(series) >= 12 else {'adf_p': None, 'kpss_p': None, 'd': 0, 'stationary': True}
        ctx['series_tests'] = st
        ctx['d'] = st['d']
        a, k = st['adf_p'], st['kpss_p']
        if st['stationary']:
            diag('Stationnarité (ADF / KPSS)', f"Série stationnaire (ADF p = {_fmt_p(a)} ; KPSS p = {_fmt_p(k)})", 'ok')
        else:
            diag('Stationnarité (ADF / KPSS)', f"Série non stationnaire (ADF p = {_fmt_p(a)} ; KPSS p = {_fmt_p(k)}) : {st['d']} différenciation(s) conseillée(s)", 'warn')
        base = series.diff(st['d']).dropna() if st['d'] else series
        cands = [meta['period']] if meta['period'] else [4, 7, 12, 24, 52]
        per, force = detect_seasonality(base.values, cands)
        ctx['period'] = per or meta['period']
        ctx['seasonal'] = bool(per)
        if per:
            diag('Saisonnalité', f"Cycle détecté de période {per} (autocorrélation = {force:.2f})", 'ok')
        else:
            diag('Saisonnalité', "Aucune saisonnalité marquée détectée")
        # volatilité
        r, desc = volatility_input(series) if len(series) >= 60 else (None, '')
        ctx['arch_p'] = arch_effect(r) if r is not None else None
        if ctx['arch_p'] is not None:
            if ctx['arch_p'] < 0.05:
                diag('Effets ARCH (volatilité)', f"Hétéroscédasticité conditionnelle détectée (test ARCH-LM p = {_fmt_p(ctx['arch_p'])})", 'ok')
            else:
                diag('Effets ARCH (volatilité)', f"Pas d'effet ARCH net (p = {_fmt_p(ctx['arch_p'])})")
        if r is not None and len(r) > 30:
            ctx['skew'] = float(pd.Series(r).skew())
            ctx['kurt'] = float(pd.Series(r).kurt())
            # asymétrie : corrélation rendement(t) et r(t+1)^2
            rr = np.asarray(r, dtype=float)
            if len(rr) > 10:
                ctx['leverage'] = float(np.corrcoef(rr[:-1], rr[1:] ** 2)[0, 1])
        ctx['exog'] = bool(features)

    if structure == 'panel' and kind == 'continuous':
        ctx['n_entities'] = int(df[entity_col].nunique())
        ctx['hausman'] = None
        try:
            from models.runners import hausman_test
            h = hausman_test(df, target, features, entity_col, time_col)
            ctx['hausman'] = h
            if h and h.get('p') is not None:
                v = "effets fixes préférables" if h['p'] < 0.05 else "effets aléatoires acceptables"
                diag('Test de Hausman', f"p = {_fmt_p(h['p'])} : {v}", 'ok')
        except Exception:
            ctx['hausman'] = None

    if features and kind in ('continuous', 'binary', 'multiclass') and structure in ('cross_section', 'panel', 'time_series'):
        try:
            X, yy, notes, _ = prepare_xy(df, target, features, max_rows=5000)
            ctx['n_features_enc'] = int(X.shape[1])
            vif = _vif_max(X)
            ctx['vif'] = vif
            if vif is not None:
                if vif > 10:
                    diag('Multicolinéarité', f"VIF maximal = {vif:.1f} (> 10) : variables fortement corrélées", 'warn')
                else:
                    diag('Multicolinéarité', f"VIF maximal = {vif:.1f} : acceptable", 'ok')
            if True:
                lin, rf = _benchmark(X, yy if kind == 'continuous' else yy.astype('category').cat.codes, kind)
                ctx['bench'] = (lin, rf)
                if lin is not None:
                    metric = 'R²' if kind == 'continuous' else 'exactitude'
                    if rf > lin + 0.05:
                        diag('Linéarité de la relation', f"Un modèle non linéaire fait mieux ({metric} validé : forêt {rf:.2f} contre linéaire {lin:.2f}) : relation probablement non linéaire", 'warn')
                    else:
                        diag('Linéarité de la relation', f"Le modèle linéaire est suffisant ({metric} validé : linéaire {lin:.2f} ; forêt {rf:.2f})", 'ok')
            if kind in ('binary', 'multiclass'):
                vc = yy.value_counts(normalize=True)
                ctx['imbalance'] = float(vc.max() / max(vc.min(), 1e-9))
                if ctx['imbalance'] > 4:
                    diag('Équilibre des classes', f"Classes déséquilibrées (rapport {ctx['imbalance']:.1f} : 1) : privilégier AUC et F1", 'warn')
                else:
                    diag('Équilibre des classes', 'Classes raisonnablement équilibrées', 'ok')
            ctx['prep_notes'] = notes
        except Exception as e:
            ctx['notes'].append(f"Diagnostics sur les variables non calculés : {e}")
    return ctx


# ----------------------------------------------------------------------------
# Recommandation
# ----------------------------------------------------------------------------
def _level(score):
    if score >= 75:
        return 'Fortement recommandé'
    if score >= 55:
        return 'Recommandé'
    if score >= 35:
        return 'Possible'
    return 'Peu adapté'


def recommend(ctx):
    recs = []
    kind = ctx['target_kind']
    structure = ctx['structure']
    n = ctx.get('n_used', ctx['n'])
    p = ctx.get('n_features_enc', len(ctx['features']))
    has_x = len(ctx['features']) > 0
    vif = ctx.get('vif') or 0
    lin, rf = ctx.get('bench', (None, None)) or (None, None)
    nonlinear = bool(lin is not None and rf is not None and rf > lin + 0.05)

    def add(mid, family, name, score, reasons, available=True, why_not=None):
        score = int(max(0, min(100, round(score))))
        recs.append({
            'id': mid, 'family': family, 'family_label': FAMILY_LABELS[family], 'name': name,
            'score': score, 'level': _level(score), 'reasons': reasons,
            'available': available, 'why_not': why_not,
        })

    # --------------------- régression (cible continue)
    reg_allowed = kind == 'continuous' or ctx.get('ambiguous')
    pen = 0
    if ctx.get('ambiguous'):
        pen = 15
    if reg_allowed:
        pan_pen = 15 if structure == 'panel' else 0
        ts_pen = 15 if structure == 'time_series' else 0
        gp = pen + pan_pen + ts_pen
        cav = None
        if pan_pen:
            cav = "Ignore la structure de panel (effets individuels)."
        if ts_pen:
            cav = "Ignore la dépendance temporelle : à utiliser avec prudence."

        def reg(mid, fam, name, score, reasons, need_x=True, extra_ok=True, why=None):
            ok = (has_x or not need_x) and extra_ok
            add(mid, fam, name, score - gp, ([cav] if cav else []) + reasons if ok else reasons, ok,
                None if ok else (why or "Sélectionnez au moins une variable explicative."))

        r_ols = ["Modèle de référence, interprétable (coefficients, tests, intervalles de confiance)."]
        if nonlinear is False and lin is not None:
            r_ols.append(f"La relation semble linéaire (R² validé = {lin:.2f}).")
        if vif > 10:
            r_ols.append("Attention : multicolinéarité forte, préférez aussi Ridge ou Lasso.")
        reg('ols', 'regression', 'Régression linéaire (MCO)', 72 + (8 if (lin is not None and not nonlinear) else 0) - (10 if vif > 10 else 0), r_ols)
        reg('ridge', 'regression', 'Régression Ridge', 52 + (28 if vif > 10 else 0) + (8 if p > n / 10 else 0),
            ["Régularisation L2 : stabilise les coefficients."] + ([f"VIF maximal élevé ({vif:.0f}) : Ridge est adapté."] if vif > 10 else []))
        reg('lasso', 'regression', 'Régression Lasso', 48 + (25 if (p >= 10 or p > n / 10) else 0) + (10 if vif > 10 else 0),
            ["Sélection automatique des variables (coefficients annulés)."] + ([f"{p} variables : le Lasso aide à en sélectionner."] if p >= 10 else []))
        reg('elasticnet', 'regression', 'Elastic Net', 45 + (18 if (vif > 10 and p >= 8) else 0),
            ["Combine Ridge et Lasso : sélection de variables avec variables corrélées."])
        if ctx.get('is_count'):
            reg('poisson', 'regression', 'Régression de Poisson (comptage)', 78,
                ["La cible est un comptage (entiers positifs) : modèle de comptage adapté."])
            reg('negbin', 'regression', 'Binomiale négative (comptage)', 70,
                ["Alternative à Poisson en cas de surdispersion."])
        # machine learning
        boost = 28 if nonlinear else 0
        reg('rf_reg', 'ml', 'Forêt aléatoire (régression)', 52 + boost + (5 if n >= 200 else 0),
            ["Capte les non-linéarités et interactions sans hypothèse de forme."] + ([f"Meilleure que le linéaire en validation (R² {rf:.2f} contre {lin:.2f})."] if nonlinear else []))
        reg('gb_reg', 'ml', 'Gradient Boosting (régression)', 50 + boost + (5 if n >= 200 else 0),
            ["Souvent le plus précis sur données tabulaires."])
        reg('svr', 'ml', 'Machine à vecteurs de support (SVR)', 36 + (12 if nonlinear else 0) - (15 if n > 5000 else 0),
            ["Modèle à noyau pour relations non linéaires (efficace sur échantillons moyens)."])
        reg('knn_reg', 'ml', 'k plus proches voisins (régression)', 33 + (6 if nonlinear else 0), ["Méthode simple fondée sur la proximité entre observations."])
        reg('tree_reg', 'ml', 'Arbre de décision (régression)', 34 + (6 if nonlinear else 0), ["Règles de décision lisibles."])
        dl = 28 + (28 if (nonlinear and n >= 1000) else 0) + (8 if n >= 1000 else 0) - (18 if n < 300 else 0)
        rr = ["Réseau de neurones (perceptron multicouche) pour relations complexes."]
        if n < 300:
            rr.append(f"Seulement {n} observations : risque de surapprentissage.")
        reg('mlp_reg', 'deep', 'Réseau de neurones (perceptron multicouche)', dl, rr)

    # --------------------- classification
    if kind in ('binary', 'multiclass'):
        boost = 25 if nonlinear else 0
        imb = ctx.get('imbalance', 1)
        notes_imb = ["Classes déséquilibrées : pondération des classes appliquée."] if imb > 4 else []
        if kind == 'binary':
            add('logit', 'classification', 'Régression logistique (Logit)', 78 + (0 if nonlinear else 6),
                ["Modèle de référence pour une cible binaire : odds ratios interprétables."] + notes_imb, has_x,
                None if has_x else "Sélectionnez au moins une variable explicative.")
        else:
            add('mlogit', 'classification', 'Régression logistique multinomiale', 72,
                ["Extension du logit à plusieurs classes."] + notes_imb, has_x, None if has_x else "Sélectionnez au moins une variable explicative.")
        ok_msg = None if has_x else "Sélectionnez au moins une variable explicative."
        add('rf_clf', 'ml', 'Forêt aléatoire (classification)', 58 + boost + (5 if n >= 200 else 0),
            ["Robuste, capte les interactions et fournit l'importance des variables."] + notes_imb, has_x, ok_msg)
        add('gb_clf', 'ml', 'Gradient Boosting (classification)', 56 + boost + (5 if n >= 200 else 0),
            ["Très performant sur données tabulaires."], has_x, ok_msg)
        add('svm_clf', 'ml', 'Machine à vecteurs de support (SVM)', 38 + (12 if nonlinear else 0) - (15 if n > 5000 else 0),
            ["Séparation à noyau, adaptée aux échantillons moyens."], has_x, ok_msg)
        add('knn_clf', 'ml', 'k plus proches voisins', 34, ["Classification par similarité."], has_x, ok_msg)
        add('tree_clf', 'ml', 'Arbre de décision', 36 + (4 if nonlinear else 0), ["Règles de décision lisibles."], has_x, ok_msg)
        add('nb_clf', 'ml', 'Naive Bayes', 33, ["Modèle probabiliste très rapide (variables supposées indépendantes)."], has_x, ok_msg)
        dl = 28 + (28 if (nonlinear and n >= 1000) else 0) + (8 if n >= 1000 else 0) - (18 if n < 300 else 0)
        add('mlp_clf', 'deep', 'Réseau de neurones (perceptron multicouche)', dl,
            ["Réseau de neurones pour frontières de décision complexes."] + ([f"Seulement {n} observations : risque de surapprentissage."] if n < 300 else []),
            has_x, ok_msg)

    # --------------------- panel
    if kind == 'continuous':
        pan_ok = structure == 'panel' and has_x
        why = None
        if structure != 'panel':
            why = "Nécessite une colonne « entité » et une colonne « temps » avec des couples uniques."
        elif not has_x:
            why = "Sélectionnez au moins une variable explicative."
        h = ctx.get('hausman') or {}
        hp = h.get('p')
        fe_b = 72 + (15 if (hp is not None and hp < 0.05) else 0)
        re_b = 62 + (18 if (hp is not None and hp >= 0.05) else 0)
        r_fe = ["Contrôle l'hétérogénéité individuelle non observée (constante par entité)."]
        r_re = ["Efficace si les effets individuels ne sont pas corrélés aux variables explicatives."]
        if hp is not None:
            r_fe.append(f"Test de Hausman p = {_fmt_p(hp)} : " + ("effets fixes préférés." if hp < 0.05 else "pas de rejet de l'hypothèse d'effets aléatoires."))
            r_re.append(f"Test de Hausman p = {_fmt_p(hp)} : " + ("effets fixes préférés." if hp < 0.05 else "effets aléatoires acceptables."))
        add('panel_pooled', 'panel', 'Panel : MCO empilés (Pooled OLS)', 52, ["Ignore les effets individuels ; point de comparaison."], pan_ok, why)
        add('panel_fe', 'panel', 'Panel : effets fixes (Within)', fe_b, r_fe, pan_ok, why)
        add('panel_re', 'panel', 'Panel : effets aléatoires', re_b, r_re, pan_ok, why)

    # --------------------- séries temporelles et volatilité
    if kind == 'continuous':
        ts_ok = structure == 'time_series' and ctx.get('series_len', 0) >= 20
        why = None
        if structure != 'time_series':
            why = "Nécessite une série temporelle (une colonne de date ou une cible sans variables explicatives)."
        elif ctx.get('series_len', 0) < 20:
            why = "Moins de 20 observations : trop court pour un modèle de série temporelle."
        d = ctx.get('d', 0)
        stat = ctx.get('series_tests', {}) or {}
        is_stat = stat.get('stationary', True)
        seas = ctx.get('seasonal', False)
        per = ctx.get('period')
        st_txt = "La série est stationnaire." if is_stat else f"La série devient stationnaire après {d} différenciation(s)."
        base = 55 if structure == 'time_series' else 0
        ns = 0 if is_stat else -18
        add('ar', 'timeseries', 'AR (autorégressif)', base + (15 if is_stat else 0) + ns + (-5 if seas else 0),
            [st_txt, "Modélise la valeur actuelle par ses valeurs passées (ordre choisi par AIC)."], ts_ok, why)
        add('ma', 'timeseries', 'MA (moyenne mobile)', base - 5 + (8 if is_stat else 0) + ns + (-5 if seas else 0),
            [st_txt, "Modélise la série par les chocs passés (ordre choisi par AIC)."], ts_ok, why)
        add('arma', 'timeseries', 'ARMA', base + 5 + (12 if is_stat else 0) + ns + (-5 if seas else 0),
            [st_txt, "Combine composantes autorégressive et moyenne mobile."], ts_ok, why)
        add('arima', 'timeseries', 'ARIMA', base + 12 + (8 if not is_stat else 0) + (-6 if seas else 0),
            [st_txt, f"Intègre la différenciation (d = {d}) pour traiter la non-stationnarité."], ts_ok, why)
        add('sarima', 'timeseries', 'SARIMA (saisonnier)', (base - 15) + (40 if (seas and ctx.get('series_len', 0) >= 3 * (per or 12)) else 0),
            ([f"Saisonnalité détectée (période {per}) : SARIMA est adapté."] if seas else ["Pas de saisonnalité nette détectée."]), ts_ok, why)
        add('holtwinters', 'timeseries', 'Lissage exponentiel (Holt-Winters)', base - 12 + (22 if seas else 0),
            ["Méthode robuste de tendance et saisonnalité, utile pour des prévisions simples."], ts_ok, why)
        exog_ok = ts_ok and has_x
        add('arimax', 'timeseries', 'ARIMAX (avec variables explicatives)', (base + 8) if has_x else 20,
            ["Série temporelle expliquée par ses valeurs passées et des variables exogènes."], exog_ok,
            why or "Sélectionnez au moins une variable explicative.")
        var_ok = ts_ok and has_x
        add('var', 'timeseries', 'VAR (vecteur autorégressif) + causalité de Granger', (base + 3) if has_x else 15,
            ["Modélise plusieurs séries simultanément et teste la causalité de Granger."], var_ok,
            why or "Sélectionnez au moins une variable explicative.")
        # volatilité
        ap = ctx.get('arch_p')
        v_ok = structure == 'time_series' and ctx.get('series_len', 0) >= 100
        vwhy = None
        if structure != 'time_series':
            vwhy = "Nécessite une série temporelle."
        elif ctx.get('series_len', 0) < 100:
            vwhy = "Au moins 100 observations sont recommandées pour un modèle de volatilité."
        has_arch = ap is not None and ap < 0.05
        fin_like = (not seas) and (ctx.get('series_len', 0) >= 250 or (ctx.get('kurt') or 0) > 2)
        vb = 25 + (45 if has_arch else 0) + (8 if (ctx.get('kurt') or 0) > 1 else 0)
        rs = ([f"Effets ARCH détectés (p = {_fmt_p(ap)}) : volatilité qui varie dans le temps."] if has_arch
              else ["Pas d'effet ARCH détecté : un modèle de volatilité n'est pas indispensable."])
        if not fin_like:
            vb = min(vb, 40)
            rs.append("La série ressemble davantage à une série économique (ventes, production...) qu'à une série financière : usage à justifier.")
        add('garch', 'volatility', 'GARCH(1,1)', vb, rs + ["Modèle de référence de la volatilité conditionnelle."], v_ok, vwhy)
        add('arch', 'volatility', 'ARCH(q)', vb - 12, rs + ["Volatilité dépendant des chocs passés (ordre choisi par AIC)."], v_ok, vwhy)
        lev = ctx.get('leverage')
        asym = lev is not None and lev < -0.05
        add('egarch', 'volatility', 'EGARCH(1,1)', vb - 8 + (10 if asym else 0),
            rs + (["Effet de levier détecté (chocs négatifs plus volatils) : EGARCH est adapté."] if asym else ["Capte les effets asymétriques."]), v_ok, vwhy)
        add('gjr', 'volatility', 'GJR-GARCH(1,1,1)', vb - 8 + (10 if asym else 0),
            rs + ["Asymétrie : les mauvaises nouvelles augmentent plus la volatilité."], v_ok, vwhy)
        add('risk', 'volatility', 'Mesures de risque (VaR, ES, Sharpe)', ((45 if v_ok else 0) + (10 if has_arch else 0)) if fin_like else (30 if v_ok else 0),
            ["Value-at-Risk, Expected Shortfall et statistiques de rendements."], v_ok, vwhy)
        # deep learning séries
        dl_ts = 25 + (20 if ctx.get('series_len', 0) >= 500 else 0)
        add('mlp_ts', 'deep', 'Réseau de neurones autorégressif (retards)', dl_ts,
            ["Perceptron multicouche appliqué aux retards de la série ; comparé à une prévision naïve."], ts_ok, why)

    recs.sort(key=lambda r: (not r['available'], -r['score']))
    # présélection : meilleur modèle de chaque famille (score >= 55), max 5
    chosen = []
    seen_f = set()
    for r in recs:
        if not r['available'] or r['score'] < 60 or r['family'] in seen_f:
            continue
        chosen.append(r['id'])
        seen_f.add(r['family'])
        if len(chosen) >= 5:
            break
    if not chosen:
        for r in recs:
            if r['available']:
                chosen.append(r['id'])
                break
    for r in recs:
        r['selected'] = r['id'] in chosen
    return recs
