# -*- coding: utf-8 -*-
"""
PLS-SEM (moindres carrés partiels pour équations structurelles), à la manière de SmartPLS.

- Algorithme PLS : schéma de pondération « path » (centroïde et factoriel disponibles), mode A (réflexif)
  ou mode B (formatif), 300 itérations maximum, critère d'arrêt 1e-7.
- Évaluation : loadings / poids, fiabilité (alpha, rho_a, rho_c), AVE, HTMT, Fornell-Larcker, VIF, R², f²,
  effets directs, indirects et totaux, bootstrapping (intervalles percentile, t de Student à n-1 ddl).
"""
import itertools

import numpy as np
import pandas as pd
from scipy import stats

from models.runners import Res, fmt, fmt_p, stars, to_b64, NAVY, STEEL, GOLD, GREY, RED, GREEN
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch


# ----------------------------------------------------------------------------
# Validation de la spécification
# ----------------------------------------------------------------------------
def validate_spec(df, spec):
    """spec = {'constructs': [{'name','indicators':[...],'mode':'A'|'B'}], 'paths': [[from,to],...]}"""
    cons = spec.get('constructs') or []
    if len(cons) < 2:
        raise ValueError("Définissez au moins deux construits.")
    names = [c['name'].strip() for c in cons]
    if len(set(names)) != len(names) or any(not n for n in names):
        raise ValueError("Les noms de construits doivent être uniques et non vides.")
    seen = {}
    for c in cons:
        if not c.get('indicators'):
            raise ValueError(f"Le construit « {c['name']} » n'a aucun indicateur.")
        for ind in c['indicators']:
            if ind not in df.columns:
                raise ValueError(f"L'indicateur « {ind} » n'existe pas dans le jeu de données.")
            if ind in seen:
                raise ValueError(f"L'indicateur « {ind} » est utilisé dans deux construits ({seen[ind]} et {c['name']}).")
            seen[ind] = c['name']
    paths = [tuple(p) for p in (spec.get('paths') or [])]
    if not paths:
        raise ValueError("Tracez au moins une relation entre deux construits.")
    for a, b in paths:
        if a not in names or b not in names or a == b:
            raise ValueError(f"Relation invalide : {a} -> {b}.")
    if len(set(paths)) != len(paths):
        raise ValueError("Une relation est définie plusieurs fois.")
    # acyclicité
    succ = {n: [b for a, b in paths if a == n] for n in names}
    state = {}

    def dfs(u):
        state[u] = 1
        for v in succ[u]:
            if state.get(v) == 1 or (state.get(v) is None and dfs(v)):
                return True
        state[u] = 2
        return False
    for n in names:
        if state.get(n) is None and dfs(n):
            raise ValueError("Le modèle contient une boucle (relation circulaire) : le PLS-SEM exige un modèle récursif.")
    return names, paths


def _all_paths(names, paths, src, dst, maxlen=6):
    succ = {n: [b for a, b in paths if a == n] for n in names}
    out = []

    def go(u, acc):
        if len(acc) > maxlen:
            return
        for v in succ[u]:
            if v == dst:
                out.append(acc + [v])
            else:
                go(v, acc + [v])
    go(src, [src])
    return out


# ----------------------------------------------------------------------------
# Algorithme PLS
# ----------------------------------------------------------------------------
def _std(a):
    s = a.std(axis=0, ddof=1)
    s = np.where(s < 1e-12, 1.0, s)
    return (a - a.mean(axis=0)) / s


def pls_algorithm(Z, blocks, modes, paths_idx, scheme='path', max_iter=300, tol=1e-7):
    """Z : matrice standardisée (n x p) ; blocks : liste d'index de colonnes par construit ;
    modes : 'A' ou 'B' ; paths_idx : liste (i, j) i -> j. Retourne poids, scores, itérations."""
    n = Z.shape[0]
    k = len(blocks)
    W = [np.ones(len(b)) for b in blocks]
    Y = np.zeros((n, k))

    def outer_scores():
        for j, b in enumerate(blocks):
            y = Z[:, b] @ W[j]
            Y[:, j] = (y - y.mean()) / (y.std(ddof=1) or 1.0)
    # normalisation initiale
    for j, b in enumerate(blocks):
        y = Z[:, b] @ W[j]
        W[j] = W[j] / (y.std(ddof=1) or 1.0)
    outer_scores()
    pred = {j: [a for a, bb in paths_idx if bb == j] for j in range(k)}
    succ = {j: [bb for a, bb in paths_idx if a == j] for j in range(k)}
    it = 0
    for it in range(1, max_iter + 1):
        # proxies internes
        E = np.zeros((k, k))
        for j in range(k):
            if pred[j]:
                P = Y[:, pred[j]]
                if scheme == 'path':
                    beta = np.linalg.lstsq(P, Y[:, j], rcond=None)[0]
                    for a, bv in zip(pred[j], beta):
                        E[j, a] = bv
                elif scheme == 'factorial':
                    for a in pred[j]:
                        E[j, a] = np.corrcoef(Y[:, j], Y[:, a])[0, 1]
                else:
                    for a in pred[j]:
                        E[j, a] = np.sign(np.corrcoef(Y[:, j], Y[:, a])[0, 1])
            for s in succ[j]:
                c = np.corrcoef(Y[:, j], Y[:, s])[0, 1]
                E[j, s] = c if scheme != 'centroid' else np.sign(c)
        inner = Y @ E.T
        Wn = []
        for j, b in enumerate(blocks):
            if not (pred[j] or succ[j]):
                Wn.append(W[j]); continue
            zi = inner[:, j]
            zi = (zi - zi.mean()) / (zi.std(ddof=1) or 1.0)
            X = Z[:, b]
            if modes[j] == 'A':
                w = X.T @ zi / (n - 1)
            else:
                w = np.linalg.lstsq(X, zi, rcond=None)[0]
            y = X @ w
            sd = y.std(ddof=1) or 1.0
            Wn.append(w / sd)
        diff = max(float(np.max(np.abs(a - b))) for a, b in zip(Wn, W))
        W = Wn
        outer_scores()
        if diff < tol:
            break
    return W, Y.copy(), it


def _fit(Z, blocks, modes, paths_idx, scheme, max_iter=300, tol=1e-7):
    W, Y, it = pls_algorithm(Z, blocks, modes, paths_idx, scheme, max_iter, tol)
    k = len(blocks)
    loadings = [np.array([np.corrcoef(Z[:, c], Y[:, j])[0, 1] for c in b]) for j, b in enumerate(blocks)]
    B = np.zeros((k, k))      # B[i, j] : effet de i sur j
    R2 = np.zeros(k)
    endo = sorted({j for _, j in paths_idx})
    for j in endo:
        pr = [a for a, bb in paths_idx if bb == j]
        beta = np.linalg.lstsq(Y[:, pr], Y[:, j], rcond=None)[0]
        for a, bv in zip(pr, beta):
            B[a, j] = bv
        res = Y[:, j] - Y[:, pr] @ beta
        R2[j] = 1 - float(res @ res) / float((Y[:, j] - Y[:, j].mean()) @ (Y[:, j] - Y[:, j].mean()))
    return {'W': W, 'Y': Y, 'L': loadings, 'B': B, 'R2': R2, 'iter': it}


def _htmt(Zc, blocks, modes):
    """HTMT entre construits (calculé sur les corrélations des indicateurs)."""
    C = np.abs(np.corrcoef(Zc, rowvar=False))
    k = len(blocks)
    H = np.full((k, k), np.nan)
    mono = []
    for b in blocks:
        if len(b) > 1:
            sub = C[np.ix_(b, b)]
            mono.append(float(sub[np.triu_indices(len(b), 1)].mean()))
        else:
            mono.append(np.nan)
    for i in range(k):
        for j in range(i + 1, k):
            het = float(C[np.ix_(blocks[i], blocks[j])].mean())
            den = np.sqrt(mono[i] * mono[j]) if not (np.isnan(mono[i]) or np.isnan(mono[j])) else np.nan
            H[i, j] = H[j, i] = het / den if den and not np.isnan(den) else np.nan
    return H


def _rho_a(Z, b, w):
    """Fiabilité rho_A de Dijkstra-Henseler (poids normalisés pour var(Y)=1)."""
    if len(b) < 2:
        return 1.0
    S = np.corrcoef(Z[:, b], rowvar=False)
    ww = np.outer(w, w)
    num = float(w @ w) ** 2 * float(w @ (S - np.diag(np.diag(S))) @ w)
    den = float(w @ (ww - np.diag(np.diag(ww))) @ w)
    return num / den if den else np.nan


def _vif(M):
    """VIF des colonnes de M (n x q)."""
    q = M.shape[1]
    if q < 2:
        return [1.0] * q
    out = []
    for i in range(q):
        y = M[:, i]
        X = np.delete(M, i, axis=1)
        X1 = np.column_stack([np.ones(len(y)), X])
        beta = np.linalg.lstsq(X1, y, rcond=None)[0]
        r = y - X1 @ beta
        r2 = 1 - float(r @ r) / float((y - y.mean()) @ (y - y.mean()))
        out.append(1 / (1 - r2) if r2 < 0.999999 else float('inf'))
    return out


def _sign_align(W_new, W_ref, Y_new, Y_ref_sign=None):
    out = []
    for wn, wr in zip(W_new, W_ref):
        out.append(-1.0 if float(wn @ wr) < 0 else 1.0)
    return out


# ----------------------------------------------------------------------------
# Exécution complète
# ----------------------------------------------------------------------------
def run_pls(df, spec, n_boot=1000, scheme='path', seed=42, progress=None):
    names, paths = validate_spec(df, spec)
    cons = spec['constructs']
    k = len(names)
    ind_all = [i for c in cons for i in c['indicators']]
    d = df[ind_all].apply(pd.to_numeric, errors='coerce')
    n0 = len(d)
    d = d.dropna()
    n = len(d)
    if n < max(30, len(ind_all) + 10):
        raise ValueError(f"Échantillon trop petit ({n} observations complètes) pour {len(ind_all)} indicateurs.")
    if (d.std() < 1e-12).any():
        raise ValueError("Un indicateur est constant (aucune variation) : retirez-le du modèle.")
    X = d.values.astype(float)
    Z = _std(X)
    blocks, pos = [], 0
    for c in cons:
        blocks.append(list(range(pos, pos + len(c['indicators']))))
        pos += len(c['indicators'])
    modes = ['B' if str(c.get('mode', 'A')).upper() in ('B', 'FORMATIF', 'FORMATIVE') and len(c['indicators']) > 1 else 'A' for c in cons]
    idx = {nm: i for i, nm in enumerate(names)}
    paths_idx = [(idx[a], idx[b]) for a, b in paths]
    endo = sorted({j for _, j in paths_idx})
    exo = [j for j in range(k) if j not in endo]

    fit = _fit(Z, blocks, modes, paths_idx, scheme)
    Y, B, R2, L, W = fit['Y'], fit['B'], fit['R2'], fit['L'], fit['W']
    T = np.linalg.inv(np.eye(k) - B) - np.eye(k)     # effets totaux
    spec_paths = []                                   # effets indirects spécifiques (longueur >= 2)
    for i, j in itertools.product(range(k), range(k)):
        if i != j:
            for p in _all_paths(names, paths, names[i], names[j]):
                if len(p) >= 3:
                    spec_paths.append([idx[x] for x in p])

    def spec_val(Bm, p):
        v = 1.0
        for a, b in zip(p[:-1], p[1:]):
            v *= Bm[a, b]
        return v
    ind_orig = np.array([spec_val(B, p) for p in spec_paths])

    # ----------------- bootstrapping
    nb = int(max(0, n_boot))
    rng = np.random.default_rng(seed)
    bw = {j: [] for j in range(k)}
    bl = {j: [] for j in range(k)}
    bB, bT, bI, bH, bR2 = [], [], [], [], []
    ok_b = 0
    if nb:
        for bi in range(nb):
            ix = rng.integers(0, n, n)
            Xb = X[ix]
            if (Xb.std(axis=0, ddof=1) < 1e-12).any():
                continue
            Zb = _std(Xb)
            try:
                fb = _fit(Zb, blocks, modes, paths_idx, scheme, max_iter=100, tol=1e-6)
            except Exception:
                continue
            sg = _sign_align(fb['W'], W, fb['Y'])
            Bb = fb['B'].copy()
            Lb = []
            for j in range(k):
                bw[j].append(fb['W'][j] * sg[j])
                Lb.append(fb['L'][j] * sg[j])
                bl[j].append(Lb[-1])
            s = np.array(sg)
            Bb = Bb * np.outer(s, s)
            bB.append(Bb)
            try:
                bT.append(np.linalg.inv(np.eye(k) - Bb) - np.eye(k))
            except Exception:
                bT.append(np.full((k, k), np.nan))
            bI.append([spec_val(Bb, p) for p in spec_paths])
            bH.append(_htmt(Zb, blocks, modes))
            bR2.append(fb['R2'])
            ok_b += 1
            if progress and bi % 100 == 0:
                progress(bi, nb)
        if ok_b < max(50, nb * 0.5):
            raise ValueError("Le bootstrapping a échoué sur trop d'échantillons : le modèle est instable avec ces données.")
    bB = np.array(bB) if bB else None
    bT = np.array(bT) if bT else None
    bI = np.array(bI) if bI else None

    def boot_stats(est, samples):
        """(se, t, p, lo, hi) à partir d'une série bootstrap."""
        if samples is None or len(samples) < 2:
            return None
        se = float(np.nanstd(samples, ddof=1))
        if se < 1e-12:
            return (se, np.nan, np.nan, float(np.nanpercentile(samples, 2.5)), float(np.nanpercentile(samples, 97.5)))
        t = est / se
        p = float(2 * (1 - stats.t.cdf(abs(t), df=n - 1)))
        return (se, t, p, float(np.nanpercentile(samples, 2.5)), float(np.nanpercentile(samples, 97.5)))

    # ----------------- mise en forme
    r = Res('plssem', 'sem', 'Équations structurelles (PLS-SEM)')
    r.d['family_label'] = 'Équations structurelles (PLS-SEM)'
    sig = lambda p: ('' if p is None or np.isnan(p) else stars(p))
    r.metric('n', 'Observations utilisées', n)
    r.metric('k', 'Construits', k)
    r.metric('p', 'Indicateurs', len(ind_all))
    r.metric('paths', 'Relations structurelles', len(paths))
    r.metric('R2', 'R² moyen (construits endogènes)', float(np.mean(R2[endo])), 3)
    r.metric('iter', 'Itérations de l\'algorithme', fit['iter'], 0)
    if nb:
        r.metric('boot', 'Échantillons bootstrap', ok_b, 0)
    if n0 > n:
        r.warn(f"{n0 - n} ligne(s) avec valeurs manquantes ont été exclues (suppression par liste) : {n} observations utilisées.")
    if nb and nb < 1000:
        r.warn("Le bootstrapping utilise moins de 1 000 échantillons : privilégiez 5 000 pour un rapport final.")
    maxarr = max(sum(1 for _, b in paths_idx if b == j) for j in endo)
    if n < 10 * maxarr:
        r.warn(f"Échantillon inférieur à la règle des 10 fois ({n} < {10 * maxarr}).")

    # 1. loadings / poids
    rows, lowload, formative_names = [], [], []
    for j, c in enumerate(cons):
        for q, ind in enumerate(c['indicators']):
            if modes[j] == 'A':
                est = float(L[j][q])
                bs = boot_stats(est, np.array([x[q] for x in bl[j]])) if nb else None
                verdict = 'Satisfaisant' if abs(est) >= 0.708 else ('À examiner' if abs(est) >= 0.40 else 'Faible : retrait conseillé')
                if abs(est) < 0.708:
                    lowload.append((ind, c['name'], est))
                rows.append([c['name'], ind, 'Réflexif', fmt(est, 3), fmt(bs[1], 2) if bs else '-', fmt_p(bs[2]) if bs else '-', verdict])
            else:
                est = float(W[j][q])
                bs = boot_stats(est, np.array([x[q] for x in bw[j]])) if nb else None
                verdict = ('Significatif' if (bs and bs[2] < 0.05) else 'Non significatif') if bs else '-'
                rows.append([c['name'], ind, 'Formatif', fmt(est, 3), fmt(bs[1], 2) if bs else '-', fmt_p(bs[2]) if bs else '-', verdict])
        if modes[j] == 'B':
            formative_names.append(c['name'])
    r.table('Loadings (construits réflexifs) et poids externes (construits formatifs)',
            ['Construit', 'Indicateur', 'Mesure', 'Loading / poids', 't', 'p-value', 'Lecture'], rows)

    # 2. fiabilité et AVE
    rel_rows, rel_issue, ave_issue, red_issue = [], [], [], []
    ave = {}
    for j, c in enumerate(cons):
        if modes[j] == 'B':
            rel_rows.append([c['name'], 'formatif', '-', '-', '-', '-', 'Voir poids et VIF'])
            continue
        lam = L[j]
        if len(lam) == 1:
            rel_rows.append([c['name'], '1 indicateur', '1,000', '1,000', '1,000', '1,000', 'Mesure à item unique'])
            ave[j] = 1.0
            continue
        S = np.corrcoef(Z[:, blocks[j]], rowvar=False)
        rbar = float(S[np.triu_indices(len(lam), 1)].mean())
        alpha = len(lam) * rbar / (1 + (len(lam) - 1) * rbar)
        rho_c = float(lam.sum() ** 2 / (lam.sum() ** 2 + np.sum(1 - lam ** 2)))
        rho_a = _rho_a(Z, blocks[j], W[j])
        av = float(np.mean(lam ** 2))
        ave[j] = av
        v = []
        if min(alpha, rho_c) < 0.70:
            v.append('Fiabilité insuffisante'); rel_issue.append(c['name'])
        if rho_c > 0.95:
            v.append('Redondance possible'); red_issue.append(c['name'])
        if av < 0.50:
            v.append('AVE < 0,50'); ave_issue.append(c['name'])
        rel_rows.append([c['name'], f'{len(lam)} indicateurs', fmt(alpha, 3), fmt(rho_a, 3), fmt(rho_c, 3), fmt(av, 3), ' ; '.join(v) or 'Satisfaisant'])
    r.table('Fiabilité et validité convergente', ['Construit', 'Mesure', 'Alpha de Cronbach', 'rho_a', 'rho_c', 'AVE', 'Lecture'], rel_rows)

    # 3. validité discriminante
    Hm = _htmt(Z, blocks, modes)
    htmt_issue = []
    lo_idx = [j for j in range(k) if modes[j] == 'A' and len(blocks[j]) > 1]
    if len(lo_idx) >= 2:
        hrows = []
        bHm = np.array(bH) if bH else None
        for ii, i in enumerate(lo_idx):
            row = [names[i]]
            for jj, j in enumerate(lo_idx):
                if jj >= ii:
                    row.append('-')
                else:
                    v = Hm[i, j]
                    row.append(fmt(v, 3) if not np.isnan(v) else '-')
                    if not np.isnan(v) and v >= 0.90:
                        htmt_issue.append((names[i], names[j], v))
                    elif not np.isnan(v) and v >= 0.85:
                        htmt_issue.append((names[i], names[j], v))
            hrows.append(row)
        r.table('Validité discriminante : HTMT (seuil 0,85 strict, 0,90 construits proches)', [''] + [names[j] for j in lo_idx], hrows)
        if bHm is not None:
            crow = []
            for ii, i in enumerate(lo_idx):
                for jj, j in enumerate(lo_idx):
                    if jj < ii:
                        up = float(np.nanpercentile(bHm[:, i, j], 97.5))
                        crow.append([f'{names[i]} - {names[j]}', fmt(Hm[i, j], 3), fmt(up, 3), 'IC contient 1 : problème' if up >= 1 else ('Limite haute > 0,90' if up > 0.90 else 'Satisfaisant')])
            r.table('HTMT : borne supérieure de l\'intervalle de confiance bootstrap à 95 %', ['Paire', 'HTMT', 'Borne haute (97,5 %)', 'Lecture'], crow)
        # Fornell-Larcker
        CY = np.corrcoef(Y, rowvar=False)
        frows = []
        for ii, i in enumerate(lo_idx):
            row = [names[i]]
            for jj, j in enumerate(lo_idx):
                row.append(fmt(np.sqrt(ave.get(i, np.nan)), 3) if i == j else (fmt(CY[i, j], 3) if jj < ii else '-'))
            frows.append(row)
        r.table('Critère de Fornell-Larcker (diagonale : racine carrée de l\'AVE)', [''] + [names[j] for j in lo_idx], frows)

    # 4. colinéarité
    vrows, vif_raw = [], []
    for j in endo:
        pr = [a for a, bb in paths_idx if bb == j]
        vv = _vif(Y[:, pr])
        for a, v in zip(pr, vv):
            vif_raw.append(v)
            vrows.append([f'{names[a]} -> {names[j]}', 'Structurelle', fmt(v, 2) if np.isfinite(v) else 'infini', 'Problème (> 5)' if v > 5 else ('Acceptable (3 à 5)' if v > 3 else 'Satisfaisant')])
    for j in range(k):
        if modes[j] == 'B':
            vv = _vif(Z[:, blocks[j]])
            for q, v in zip(cons[j]['indicators'], vv):
                vif_raw.append(v)
                vrows.append([f'{q} ({names[j]})', 'Indicateur formatif', fmt(v, 2) if np.isfinite(v) else 'infini', 'Problème (> 5)' if v > 5 else ('Acceptable (3 à 5)' if v > 3 else 'Satisfaisant')])
    max_vif = max([v for v in vif_raw if np.isfinite(v)] or [0])
    r.table('Colinéarité (VIF)', ['Relation / indicateur', 'Type', 'VIF', 'Lecture'], vrows)

    # 5. coefficients de chemin
    prow, sigpaths = [], {}
    for (a, bb) in paths_idx:
        est = float(B[a, bb])
        bs = boot_stats(est, bB[:, a, bb]) if bB is not None else None
        pr = [x for x, y in paths_idx if y == bb]
        Yx = Y[:, [x for x in pr if x != a]]
        if Yx.shape[1]:
            beta = np.linalg.lstsq(Yx, Y[:, bb], rcond=None)[0]
            rr = Y[:, bb] - Yx @ beta
            r2ex = 1 - float(rr @ rr) / float((Y[:, bb] - Y[:, bb].mean()) @ (Y[:, bb] - Y[:, bb].mean()))
        else:
            r2ex = 0.0
        f2 = (R2[bb] - r2ex) / (1 - R2[bb]) if R2[bb] < 0.999 else np.nan
        sigpaths[(a, bb)] = bs[2] if bs else None
        eff = ('grand' if f2 >= 0.35 else 'moyen' if f2 >= 0.15 else 'petit' if f2 >= 0.02 else 'négligeable') if not np.isnan(f2) else '-'
        prow.append([f'{names[a]} -> {names[bb]}', fmt(est, 3) + (sig(bs[2]) if bs else ''), fmt(bs[0], 3) if bs else '-', fmt(bs[1], 2) if bs else '-', fmt_p(bs[2]) if bs else '-',
                     f'[{fmt(bs[3], 3)} ; {fmt(bs[4], 3)}]' if bs else '-', fmt(f2, 3), eff])
    r.table('Coefficients de chemin (bootstrapping, IC percentile 95 %)', ['Relation', 'Coefficient β', 'Erreur std', 't', 'p-value', 'IC 95 %', 'f²', 'Taille d\'effet'], prow)

    # 6. R²
    r2rows = []
    for j in endo:
        npred = sum(1 for _, bb in paths_idx if bb == j)
        adj = 1 - (1 - R2[j]) * (n - 1) / (n - npred - 1)
        lvl = 'substantiel' if R2[j] >= 0.75 else 'modéré' if R2[j] >= 0.50 else 'faible' if R2[j] >= 0.25 else 'très faible'
        bs = boot_stats(float(R2[j]), np.array(bR2)[:, j]) if bR2 else None
        r2rows.append([names[j], fmt(R2[j], 3), fmt(adj, 3), fmt_p(bs[2]) if bs else '-', lvl.capitalize()])
    r.table('Pouvoir explicatif (R²)', ['Construit endogène', 'R²', 'R² ajusté', 'p-value', 'Lecture'], r2rows)

    # 7. effets indirects et totaux
    irows = []
    med_notes = []
    for si, p in enumerate(spec_paths):
        est = float(ind_orig[si])
        bs = boot_stats(est, bI[:, si]) if bI is not None else None
        irows.append([' -> '.join(names[x] for x in p), fmt(est, 3) + (sig(bs[2]) if bs else ''), fmt(bs[1], 2) if bs else '-', fmt_p(bs[2]) if bs else '-',
                      f'[{fmt(bs[3], 3)} ; {fmt(bs[4], 3)}]' if bs else '-'])
        if bs and bs[2] < 0.05 and len(p) == 3:
            a, m, c_ = p
            direct = (a, c_) in sigpaths
            if not direct:
                med_notes.append(f"{names[m]} médiatise entièrement l'effet de {names[a]} sur {names[c_]} (aucun effet direct modélisé).")
            else:
                dp = sigpaths[(a, c_)]
                dsign = B[a, c_] * est > 0
                if dp is not None and dp >= 0.05:
                    med_notes.append(f"{names[m]} médiatise totalement l'effet de {names[a]} sur {names[c_]} (effet indirect significatif, effet direct non significatif).")
                elif dsign:
                    med_notes.append(f"{names[m]} est un médiateur complémentaire de la relation {names[a]} -> {names[c_]} (effets direct et indirect significatifs de même signe).")
                else:
                    med_notes.append(f"{names[m]} est un médiateur compétitif de la relation {names[a]} -> {names[c_]} (effets direct et indirect de signes opposés).")
    if irows:
        r.table('Effets indirects spécifiques', ['Chemin', 'Effet', 't', 'p-value', 'IC 95 %'], irows)
    trows = []
    for i in range(k):
        for j in range(k):
            if i != j and abs(T[i, j]) > 1e-12:
                bs = boot_stats(float(T[i, j]), bT[:, i, j]) if bT is not None else None
                trows.append([f'{names[i]} -> {names[j]}', fmt(T[i, j], 3) + (sig(bs[2]) if bs else ''), fmt_p(bs[2]) if bs else '-', f'[{fmt(bs[3], 3)} ; {fmt(bs[4], 3)}]' if bs else '-'])
    r.table('Effets totaux (direct + indirects)', ['Relation', 'Effet total', 'p-value', 'IC 95 %'], trows)

    # ----------------- graphiques
    r.chart('Modèle structurel estimé', _diagram(names, paths_idx, B, R2, sigpaths, modes, endo))
    fig, ax = plt.subplots(figsize=(8, max(2.6, 0.32 * len(ind_all) + 1)))
    labs, vals, cols = [], [], []
    for j, c in enumerate(cons):
        for q, ind in enumerate(c['indicators']):
            labs.append(f'{ind}'); vals.append(L[j][q] if modes[j] == 'A' else W[j][q]); cols.append(STEEL if modes[j] == 'A' else GOLD)
    yy = np.arange(len(labs))[::-1]
    ax.barh(yy, vals, color=cols)
    ax.set_yticks(yy); ax.set_yticklabels(labs, fontsize=8)
    ax.axvline(0.708, color=NAVY, ls='--', lw=1); ax.text(0.71, yy.max() + 0.6, '0,708', fontsize=8, color=NAVY)
    ax.set_xlabel('Loading (bleu) / poids (or)'); ax.set_title('Loadings et poids des indicateurs')
    fig.tight_layout(); r.chart('Loadings et poids des indicateurs', fig)
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar([names[j] for j in endo], [R2[j] for j in endo], color=STEEL)
    for q, j in enumerate(endo):
        ax.text(q, R2[j] + 0.02, fmt(R2[j], 2), ha='center', fontsize=9, color=NAVY)
    ax.set_ylim(0, 1.05); ax.set_ylabel('R²'); ax.set_title('R² des construits endogènes')
    fig.tight_layout(); r.chart('R² des construits endogènes', fig)

    # ----------------- interprétation
    r.say(f"Le modèle comprend {k} construits, {len(ind_all)} indicateurs et {len(paths)} relations structurelles, estimés sur {n} observations (schéma de pondération {scheme}, convergence en {fit['iter']} itérations).")
    if lowload:
        r.say("Loadings inférieurs à 0,708 : " + ', '.join(f"{i} ({c}, {fmt(v, 2)})" for i, c, v in lowload[:6]) + ". Examinez leur retrait un à un.")
    else:
        r.say("Tous les loadings des construits réflexifs dépassent 0,708 : la fiabilité des indicateurs est satisfaisante.")
    if rel_issue:
        r.say("Fiabilité insuffisante (alpha ou rho_c < 0,70) : " + ', '.join(rel_issue) + ".")
    if ave_issue:
        r.say("Validité convergente insuffisante (AVE < 0,50) : " + ', '.join(ave_issue) + ".")
    if red_issue:
        r.say("rho_c supérieur à 0,95 (indicateurs possiblement redondants) : " + ', '.join(red_issue) + ".")
    if not (rel_issue or ave_issue):
        r.say("La fiabilité et la validité convergente des construits réflexifs sont satisfaisantes.")
    bad = [(a, b, v) for a, b, v in htmt_issue if v >= 0.85]
    if bad:
        r.say("Validité discriminante à surveiller (HTMT ≥ 0,85) : " + '; '.join(f"{a} / {b} ({fmt(v, 2)})" for a, b, v in bad) + ".")
    elif len(lo_idx) >= 2:
        r.say("La validité discriminante est établie : tous les HTMT sont inférieurs à 0,85.")
    if max_vif > 5:
        r.say(f"Colinéarité problématique (VIF maximal = {fmt(max_vif, 1)} > 5).")
    elif max_vif > 3:
        r.say(f"Colinéarité acceptable mais à surveiller (VIF maximal = {fmt(max_vif, 1)}).")
    else:
        r.say("Aucun problème de colinéarité (tous les VIF sont inférieurs à 3).")
    for (a, bb) in paths_idx:
        est = B[a, bb]; p_ = sigpaths.get((a, bb))
        if p_ is None:
            r.say(f"{names[a]} -> {names[bb]} : coefficient de {fmt(est, 3)} (bootstrapping non demandé).")
        elif p_ < 0.05:
            r.say(f"{names[a]} -> {names[bb]} : effet {'positif' if est > 0 else 'négatif'} et significatif (β = {fmt(est, 3)}, p {fmt_p(p_) if p_ >= 0.001 else '< 0,001'}).")
        else:
            r.say(f"{names[a]} -> {names[bb]} : effet non significatif (β = {fmt(est, 3)}, p = {fmt_p(p_)}).")
    for j in endo:
        r.say(f"{names[j]} : R² = {fmt(R2[j], 3)}, soit {fmt(R2[j] * 100, 1)} % de variance expliquée.")
    for t in med_notes:
        r.say(t)
    r.d['raw'].update({'max_vif': float(max_vif)})
    r.d['pls'] = {'names': names, 'paths': [list(p) for p in paths], 'modes': modes, 'n': n, 'boot': ok_b, 'scheme': scheme,
                  'R2': {names[j]: float(R2[j]) for j in endo}}
    r.d['score'] = 100
    r.d['level'] = 'Recommandé'
    r.d['reasons'] = ["Modèle d'équations structurelles défini par l'utilisateur (construits latents, mesure et relations structurelles)."]
    return r.d


def _isnum(s):
    try:
        float(str(s).replace(',', '.'))
        return True
    except Exception:
        return False


def _diagram(names, paths_idx, B, R2, sigp, modes, endo):
    k = len(names)
    depth = [0] * k
    for _ in range(k):
        for a, b in paths_idx:
            depth[b] = max(depth[b], depth[a] + 1)
    layers = {}
    for j in range(k):
        layers.setdefault(depth[j], []).append(j)
    nl = max(layers) + 1
    maxrows = max(len(v) for v in layers.values())
    has_skip = any(depth[b] - depth[a] > 1 for a, b in paths_idx)
    rows_n = maxrows + (0.7 if has_skip else 0)
    fig, ax = plt.subplots(figsize=(max(6.5, 2.9 * nl), max(3.4, 1.7 * rows_n + 0.8)))
    ax.set_xlim(0, nl); ax.set_ylim(0, rows_n); ax.axis('off')
    pos = {}
    for l, js in layers.items():
        for q, j in enumerate(js):
            pos[j] = (l + 0.5, maxrows - (q + 0.5) * maxrows / len(js))
    for a, b in paths_idx:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        p = sigp.get((a, b))
        col = GREEN if (p is not None and p < 0.05) else (GREY if p is not None else NAVY)
        dx, dy = x2 - x1, y2 - y1
        L = np.hypot(dx, dy) or 1
        skip = (depth[b] - depth[a]) > 1 or (abs(dx) < 1e-9)
        rad = 0.0
        if skip:
            rad = 0.25 + 0.12 * max(1, depth[b] - depth[a])
            rad = -rad if dx > 0 else rad
        s_ = (x1 + dx / L * 0.34, y1 + dy / L * 0.25)
        e_ = (x2 - dx / L * 0.34, y2 - dy / L * 0.25)
        ax.add_patch(FancyArrowPatch(s_, e_, arrowstyle='-|>', mutation_scale=14, color=col, lw=1.8, connectionstyle=f'arc3,rad={rad}', zorder=1))
        mx, my = (s_[0] + e_[0]) / 2, (s_[1] + e_[1]) / 2
        ex, ey = e_[0] - s_[0], e_[1] - s_[1]
        lx, ly = mx + 0.5 * rad * ey, my - 0.5 * rad * ex
        ax.text(lx, ly + (0.0 if skip else 0.07), fmt(B[a, b], 3) + (stars(p) if p is not None else ''), ha='center', va='center', fontsize=9, color=col, fontweight='bold',
                bbox=dict(facecolor='white', edgecolor='none', pad=1.2), zorder=3)
    for j in range(k):
        x, y = pos[j]
        ax.add_patch(Ellipse((x, y), 0.68, 0.5, facecolor='#eaf1f8' if modes[j] == 'A' else '#f4e8c8', edgecolor=STEEL if modes[j] == 'A' else GOLD, lw=2))
        ax.text(x, y + (0.06 if j in endo else 0), names[j], ha='center', va='center', fontsize=9, fontweight='bold', color=NAVY)
        if j in endo:
            ax.text(x, y - 0.12, f'R² = {fmt(R2[j], 2)}', ha='center', va='center', fontsize=8, color=GOLD)
    ax.set_title('Modèle structurel estimé (vert : relation significative à 5 % ; or : construit formatif)', fontsize=9)
    fig.tight_layout()
    return fig
