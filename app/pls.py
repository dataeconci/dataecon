# -*- coding: utf-8 -*-
"""Moteur PLS-SEM pédagogique (algorithme PLS de Wold / Lohmöller, schéma de pondération « path »).
Reproduit les sorties usuelles de SmartPLS : loadings, poids, fiabilité (alpha, rho_a, rho_c), AVE, HTMT,
Fornell-Larcker, chemins, R², f², VIF, effets indirects, bootstrapping."""
import math
import numpy as np

MAX_ITER, TOL = 300, 1e-7


class PLSError(ValueError):
    pass


# ------------------------------------------------------------------ structure
def _validate(constructs, paths, cols):
    names = [c['name'] for c in constructs]
    if len(constructs) < 2:
        raise PLSError("Définissez au moins deux construits.")
    if len(set(names)) != len(names):
        raise PLSError("Chaque construit doit avoir un nom unique.")
    for c in constructs:
        if not c['indicators']:
            raise PLSError(f"Le construit « {c['name']} » n'a aucun indicateur.")
        for i in c['indicators']:
            if i not in cols:
                raise PLSError(f"Indicateur inconnu : {i}.")
        if c.get('mode') not in ('A', 'B'):
            c['mode'] = 'A'
    seen = {}
    for c in constructs:
        for i in c['indicators']:
            if i in seen:
                raise PLSError(f"L'indicateur « {i} » est utilisé dans deux construits ({seen[i]} et {c['name']}).")
            seen[i] = c['name']
    P = []
    for a, b in paths:
        if a not in names or b not in names:
            raise PLSError("Une relation fait référence à un construit inexistant.")
        if a == b:
            raise PLSError("Un construit ne peut pas être relié à lui-même.")
        if (a, b) in P:
            continue
        if (b, a) in P:
            raise PLSError(f"Relations inverses entre « {a} » et « {b} » : le modèle doit être récursif (sans boucle).")
        P.append((a, b))
    if not P:
        raise PLSError("Ajoutez au moins une relation entre deux construits.")
    # acyclicité
    adj = {n: [b for a, b in P if a == n] for n in names}
    state = {}

    def dfs(n):
        state[n] = 1
        for m in adj[n]:
            if state.get(m) == 1:
                raise PLSError("Le modèle contient une boucle (relations circulaires) : PLS-SEM exige un modèle récursif.")
            if state.get(m) is None:
                dfs(m)
        state[n] = 2
    for n in names:
        if state.get(n) is None:
            dfs(n)
    return names, P


def _topo_levels(names, P):
    lvl = {n: 0 for n in names}
    for _ in names:
        for a, b in P:
            lvl[b] = max(lvl[b], lvl[a] + 1)
    return lvl


# ------------------------------------------------------------------ algorithme
def _std(M):
    s = M.std(axis=0, ddof=1)
    s[s == 0] = 1.0
    return (M - M.mean(axis=0)) / s


def _estimate(X, blocks, modes, P_idx, names_n):
    """X : indicateurs standardisés (n, p). blocks : liste d'index de colonnes par construit.
    Retourne (scores, poids, nb_iter)."""
    n = X.shape[0]
    K = len(blocks)
    W = [np.ones(len(b)) for b in blocks]
    # initialisation : somme des indicateurs
    Y = np.column_stack([X[:, b] @ w for b, w in zip(blocks, W)])
    Y = _std(Y)
    pred = [[a for a, bb in P_idx if bb == k] for k in range(K)]
    succ = [[bb for a, bb in P_idx if a == k] for k in range(K)]
    it = 0
    for it in range(1, MAX_ITER + 1):
        # coefficients structurels courants (régressions des LV sur leurs prédécesseurs)
        beta = {}
        for k in range(K):
            if pred[k]:
                A = Y[:, pred[k]]
                coef, *_ = np.linalg.lstsq(A, Y[:, k], rcond=None)
                for j, a in enumerate(pred[k]):
                    beta[(a, k)] = coef[j]
        Z = np.zeros_like(Y)
        for k in range(K):
            z = np.zeros(n)
            for a in pred[k]:            # prédécesseurs : coefficients de chemin
                z += beta[(a, k)] * Y[:, a]
            for s in succ[k]:            # successeurs : corrélations
                z += float(np.corrcoef(Y[:, k], Y[:, s])[0, 1]) * Y[:, s]
            Z[:, k] = z if np.any(z) else Y[:, k]
        Z = _std(Z)
        Wn = []
        for k, b in enumerate(blocks):
            Xk = X[:, b]
            if modes[k] == 'A':
                w = Xk.T @ Z[:, k] / (n - 1)
            else:
                w, *_ = np.linalg.lstsq(Xk, Z[:, k], rcond=None)
            Wn.append(w)
        Yn = np.column_stack([X[:, b] @ w for b, w in zip(blocks, Wn)])
        sd = Yn.std(axis=0, ddof=1)
        sd[sd == 0] = 1.0
        Wn = [w / sd[k] for k, w in enumerate(Wn)]
        Yn = Yn / sd
        delta = max(float(np.max(np.abs(wn - wo))) for wn, wo in zip(Wn, W))
        W, Y = Wn, Yn - Yn.mean(axis=0)
        if delta < TOL:
            break
    return Y, W, it


def _path_model(Y, P_idx, K):
    coefs, r2 = {}, np.zeros(K)
    endo = sorted(set(b for _, b in P_idx))
    for k in endo:
        pr = [a for a, b in P_idx if b == k]
        A = Y[:, pr]
        c, *_ = np.linalg.lstsq(A, Y[:, k], rcond=None)
        for j, a in enumerate(pr):
            coefs[(a, k)] = float(c[j])
        res = Y[:, k] - A @ c
        r2[k] = 1 - float(res.var(ddof=1) / Y[:, k].var(ddof=1))
    return coefs, r2


def _indirect(names, P):
    """Effets indirects spécifiques (chemins de longueur >= 2) : liste de tuples (suite de construits)."""
    adj = {n: [b for a, b in P if a == n] for n in names}
    out = []

    def walk(path):
        for m in adj[path[-1]]:
            p2 = path + [m]
            if len(p2) >= 3:
                out.append(tuple(p2))
            walk(p2)
    for n in names:
        walk([n])
    return out


def _htmt(R, blocks):
    K = len(blocks)
    H = np.full((K, K), np.nan)
    for i in range(K):
        for j in range(i):
            het = np.abs(R[np.ix_(blocks[i], blocks[j])]).mean()

            def mono(b):
                if len(b) < 2:
                    return np.nan
                sub = np.abs(R[np.ix_(b, b)])
                return (sub.sum() - len(b)) / (len(b) * (len(b) - 1))
            mi, mj = mono(blocks[i]), mono(blocks[j])
            if np.isnan(mi) or np.isnan(mj) or mi <= 0 or mj <= 0:
                H[i, j] = np.nan
            else:
                H[i, j] = het / math.sqrt(mi * mj)
    return H


def _rho_a(w, S):
    """Dijkstra-Henseler rho_A à partir des poids (échelle : composite de variance 1)."""
    if len(w) < 2:
        return 1.0
    ww = np.outer(w, w)
    num = (w @ w) ** 2 * (w @ (S - np.diag(np.diag(S))) @ w)
    den = w @ (ww - np.diag(np.diag(ww))) @ w
    return float(num / den) if den != 0 else float('nan')


def _alpha(Rb):
    k = Rb.shape[0]
    if k < 2:
        return 1.0
    rbar = (Rb.sum() - k) / (k * (k - 1))
    return float(k * rbar / (1 + (k - 1) * rbar))


def _vif_matrix(Rm):
    """VIF pour chaque prédicteur à partir de la matrice de corrélation (inverse)."""
    try:
        inv = np.linalg.inv(Rm)
        return np.diag(inv)
    except np.linalg.LinAlgError:
        return np.full(Rm.shape[0], np.nan)


# ------------------------------------------------------------------ calcul principal
def run_pls(df, constructs, paths):
    cols = list(df.columns)
    names, P = _validate(constructs, paths, cols)
    inds = [i for c in constructs for i in c['indicators']]
    data = df[inds].apply(lambda s: s.astype(float)).dropna()
    n = len(data)
    if n < 30:
        raise PLSError(f"Seulement {n} lignes complètes : au moins 30 observations sont nécessaires.")
    if (data.std(axis=0, ddof=1) == 0).any():
        bad = [c for c in inds if data[c].std(ddof=1) == 0]
        raise PLSError("Indicateur(s) sans variation (constant) : " + ", ".join(bad))
    Xraw = data.values
    X = _std(Xraw)
    pos, blocks = 0, []
    for c in constructs:
        blocks.append(list(range(pos, pos + len(c['indicators']))))
        pos += len(c['indicators'])
    modes = [c['mode'] for c in constructs]
    idx = {nme: k for k, nme in enumerate(names)}
    P_idx = [(idx[a], idx[b]) for a, b in P]
    K = len(names)
    Y, W, it = _estimate(X, blocks, modes, P_idx, names)
    coefs, r2 = _path_model(Y, P_idx, K)
    R = np.corrcoef(X, rowvar=False)
    if R.ndim == 0:
        R = np.array([[1.0]])
    LAM = {}
    out = {'n': int(n), 'iterations': int(it), 'converged': it < MAX_ITER}
    # modèle de mesure
    loadings, weights, cross, rel = [], [], [], []
    for k, c in enumerate(constructs):
        b = blocks[k]
        lam = np.array([float(np.corrcoef(X[:, j], Y[:, k])[0, 1]) for j in b])
        w = W[k]
        for j, nm in enumerate(c['indicators']):
            loadings.append({'construct': c['name'], 'indicator': nm, 'loading': float(lam[j]), 'weight': float(w[j])})
        cl = {}
        for kk in range(K):
            cl[names[kk]] = [float(np.corrcoef(X[:, j], Y[:, kk])[0, 1]) for j in b]
        cross.append({'construct': c['name'], 'indicators': c['indicators'], 'values': cl})
        Rb = R[np.ix_(b, b)]
        S_w = Rb
        sl = lam.sum()
        rho_c = float(sl ** 2 / (sl ** 2 + (1 - lam ** 2).sum())) if len(b) > 0 else float('nan')
        rel.append({'construct': c['name'], 'mode': c['mode'], 'n_ind': len(b),
                    'alpha': _alpha(Rb), 'rho_a': _rho_a(w, S_w) if c['mode'] == 'A' else None,
                    'rho_c': rho_c, 'ave': float((lam ** 2).mean())})
    out['loadings'] = loadings
    out['cross_loadings'] = cross
    out['reliability'] = rel
    # VIF externe (construits formatifs)
    outer_vif = []
    for k, c in enumerate(constructs):
        if c['mode'] == 'B' and len(blocks[k]) > 1:
            v = _vif_matrix(R[np.ix_(blocks[k], blocks[k])])
            for j, nm in enumerate(c['indicators']):
                outer_vif.append({'construct': c['name'], 'indicator': nm, 'vif': float(v[j])})
    out['outer_vif'] = outer_vif
    # HTMT et Fornell-Larcker
    H = _htmt(R, blocks)
    out['htmt'] = {'names': names, 'matrix': [[None if np.isnan(H[i, j]) or j >= i else float(H[i, j]) for j in range(K)] for i in range(K)]}
    CY = np.corrcoef(Y, rowvar=False)
    CY = np.array([[1.0]]) if CY.ndim == 0 else CY
    sqave = [math.sqrt(max(r['ave'], 0)) for r in rel]
    out['fornell'] = {'names': names, 'matrix': [[(sqave[i] if i == j else (float(CY[i, j]) if j < i else None)) for j in range(K)] for i in range(K)]}
    # modèle structurel
    paths_out = [{'from': names[a], 'to': names[b], 'beta': coefs[(a, b)]} for a, b in P_idx]
    # f² et VIF interne
    for p in paths_out:
        a, b = idx[p['from']], idx[p['to']]
        pr = [x for x, y in P_idx if y == b]
        if len(pr) >= 1:
            rest = [x for x in pr if x != a]
            if rest:
                A = Y[:, rest]
                c2, *_ = np.linalg.lstsq(A, Y[:, b], rcond=None)
                r_ex = 1 - float((Y[:, b] - A @ c2).var(ddof=1) / Y[:, b].var(ddof=1))
            else:
                r_ex = 0.0
            r_in = r2[b]
            p['f2'] = float((r_in - r_ex) / (1 - r_in)) if r_in < 1 else float('nan')
            if len(pr) > 1:
                v = _vif_matrix(np.corrcoef(Y[:, pr], rowvar=False))
                p['vif'] = float(v[pr.index(a)])
            else:
                p['vif'] = 1.0
    out['paths'] = paths_out
    endo = sorted(set(b for _, b in P_idx))
    out['r2'] = [{'construct': names[k], 'r2': float(r2[k]), 'r2_adj': float(1 - (1 - r2[k]) * (n - 1) / (n - len([1 for a, b in P_idx if b == k]) - 1))} for k in endo]
    # effets indirects / totaux
    ind = _indirect(names, P)
    beta_by = {(names[a], names[b]): v for (a, b), v in coefs.items()}
    spec = []
    for chain in ind:
        val = 1.0
        for u, v in zip(chain[:-1], chain[1:]):
            val *= beta_by[(u, v)]
        spec.append({'chain': list(chain), 'effect': float(val)})
    out['indirect'] = spec
    tot = []
    for a in names:
        for b in names:
            if a == b:
                continue
            d = beta_by.get((a, b), 0.0)
            i_ = sum(s['effect'] for s in spec if s['chain'][0] == a and s['chain'][-1] == b)
            if (a, b) in beta_by or i_ != 0:
                tot.append({'from': a, 'to': b, 'direct': float(d), 'indirect': float(i_), 'total': float(d + i_)})
    out['total_effects'] = tot
    out['scores_head'] = [[float(v) for v in row] for row in Y[:5]]
    out['_ctx'] = dict(X=X, blocks=blocks, modes=modes, P_idx=P_idx, names=names, Yorig=Y, Worig=W, coefs=coefs,
                       ind=ind, spec=spec, constructs=constructs, loadings_vec=[l['loading'] for l in loadings])
    return out


# ------------------------------------------------------------------ bootstrap
def _p_two(t, df):
    try:
        from scipy import stats
        return float(2 * (1 - stats.t.cdf(abs(t), df)))
    except Exception:
        return float(math.erfc(abs(t) / math.sqrt(2)))


def bootstrap(res, B=500, seed=2024):
    ctx = res['_ctx']
    X, blocks, modes, P_idx, names = ctx['X'], ctx['blocks'], ctx['modes'], ctx['P_idx'], ctx['names']
    n, K = X.shape[0], len(names)
    rng = np.random.default_rng(seed)
    pidx = {names[k]: k for k in range(K)}
    pairs = [(a, b) for a, b in P_idx]
    paths_b = {p: [] for p in pairs}
    load_b = [[] for _ in ctx['loadings_vec']]
    ind_b = [[] for _ in ctx['spec']]
    tot_b = {}
    htmt_b = {}
    r2_b = {k: [] for k in sorted(set(b for _, b in P_idx))}
    Yo = ctx['Yorig']
    ok = 0
    for _ in range(B):
        rows = rng.integers(0, n, n)
        Xb = X[rows]
        sd = Xb.std(axis=0, ddof=1)
        if (sd == 0).any():
            continue
        Xb = _std(Xb)
        try:
            Yb, Wb, _ = _estimate(Xb, blocks, modes, P_idx, names)
        except Exception:
            continue
        # alignement des signes sur le résultat d'origine
        for k in range(K):
            if float(np.corrcoef(Yb[:, k], Yo[rows, k])[0, 1]) < 0:
                Yb[:, k] *= -1
        cb, rb = _path_model(Yb, P_idx, K)
        ok += 1
        for p in pairs:
            paths_b[p].append(cb[p])
        j = 0
        for k, b in enumerate(blocks):
            for col in b:
                load_b[j].append(float(np.corrcoef(Xb[:, col], Yb[:, k])[0, 1]))
                j += 1
        bb = {(names[a], names[b]): v for (a, b), v in cb.items()}
        for s_i, s in enumerate(ctx['spec']):
            v = 1.0
            for u, w_ in zip(s['chain'][:-1], s['chain'][1:]):
                v *= bb[(u, w_)]
            ind_b[s_i].append(v)
        for k in r2_b:
            r2_b[k].append(float(rb[k]))
        Rb = np.corrcoef(Xb, rowvar=False)
        Hb = _htmt(Rb, blocks)
        for i in range(K):
            for jx in range(i):
                htmt_b.setdefault((i, jx), []).append(Hb[i, jx])
        for a in names:
            for b_ in names:
                if a == b_:
                    continue
                d = bb.get((a, b_), 0.0)
                i_ = 0.0
                for s_i, s in enumerate(ctx['spec']):
                    if s['chain'][0] == a and s['chain'][-1] == b_:
                        i_ += ind_b[s_i][-1]
                tot_b.setdefault((a, b_), []).append(d + i_)
    if ok < max(20, B // 2):
        raise PLSError("Le bootstrapping a échoué sur trop d'échantillons (données insuffisantes ou trop colinéaires).")

    def summ(orig, arr):
        a = np.array(arr, dtype=float)
        a = a[~np.isnan(a)]
        se = float(a.std(ddof=1)) if len(a) > 1 else float('nan')
        t = float(orig / se) if se and se > 0 else float('nan')
        lo, hi = (float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))) if len(a) else (float('nan'),) * 2
        return {'orig': float(orig), 'mean': float(a.mean()) if len(a) else float('nan'), 'se': se, 't': t,
                'p': _p_two(t, n - 1) if not math.isnan(t) else float('nan'), 'lo': lo, 'hi': hi}
    res['bootstrap'] = {'B': int(ok), 'ci': 'percentile 95 %', 'seed': seed}
    res['paths_boot'] = [dict(from_=names[a], to=names[b], **summ(ctx['coefs'][(a, b)], paths_b[(a, b)])) for a, b in pairs]
    for d in res['paths_boot']:
        d['from'] = d.pop('from_')
    res['loadings_boot'] = [dict(construct=l['construct'], indicator=l['indicator'], **summ(l['loading'], load_b[i])) for i, l in enumerate(res['loadings'])]
    res['indirect_boot'] = [dict(chain=s['chain'], **summ(s['effect'], ind_b[i])) for i, s in enumerate(ctx['spec'])]
    res['total_boot'] = [dict(**{'from': a, 'to': b}, **summ(next(t['total'] for t in res['total_effects'] if t['from'] == a and t['to'] == b), v))
                         for (a, b), v in tot_b.items() if any(t['from'] == a and t['to'] == b for t in res['total_effects'])]
    res['r2_boot'] = [dict(construct=names[k], **summ(next(r['r2'] for r in res['r2'] if r['construct'] == names[k]), v)) for k, v in r2_b.items()]
    ht = []
    Hm = res['htmt']['matrix']
    for (i, jx), arr in htmt_b.items():
        a = np.array(arr, dtype=float)
        a = a[~np.isnan(a)]
        if len(a) and Hm[i][jx] is not None:
            ht.append({'a': names[i], 'b': names[jx], 'htmt': Hm[i][jx], 'hi': float(np.percentile(a, 97.5)), 'lo': float(np.percentile(a, 2.5))})
    res['htmt_boot'] = ht
    return res


def public(res):
    return {k: v for k, v in res.items() if not k.startswith('_')}
