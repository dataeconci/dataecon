# -*- coding: utf-8 -*-
"""
Préparation automatique des données avant toute analyse :
- conversion des nombres écrits en texte (virgule décimale)
- traitement des valeurs manquantes par la méthode adaptée à la structure des données
- encodage des variables qualitatives
- décision de standardisation / normalisation

preprocess_dataframe(...) -> (df_propre, rapport)
rapport = {'steps': [{'variable','probleme','traitement','detail'}], 'n_before', 'n_after', 'summary': [str]}
"""
import numpy as np
import pandas as pd

MAX_MISSING_FEATURE = 0.60     # au-delà, la variable explicative est retirée
MAX_GAP_SHARE_TARGET = 0.25    # série : au-delà, on ne comble pas la cible, on retire les lignes


def _numeric_like(s):
    return parse_number_series(s)


_SUFFIX = {'K': 1e3, 'M': 1e6, 'B': 1e9, 'G': 1e9, 'T': 1e12}


def parse_number_series(s):
    """Convertit une colonne texte en nombres (format français ou anglais).
    Gère : virgule décimale, espaces/espaces insécables, %, devise, suffixes K/M/B, parenthèses négatives.
    Retourne une Series numérique ou None si moins de 90 % des valeurs s'y prêtent."""
    if pd.api.types.is_numeric_dtype(s) or s.dtype == bool:
        return None
    t = s.astype(str).str.strip()
    t = t.where(s.notna(), None)
    c = (t.str.replace('\u00a0', '', regex=False).str.replace('\u202f', '', regex=False)
          .str.replace(' ', '', regex=False).str.replace('%', '', regex=False)
          .str.replace('$', '', regex=False).str.replace('€', '', regex=False)
          .str.replace('\u2212', '-', regex=False))
    mult = c.str.extract(r'([KkMmBbGgTt])$', expand=False).str.upper().map(_SUFFIX)
    c = c.str.replace(r'[KkMmBbGgTt]$', '', regex=True)
    neg = c.str.match(r'^\(.*\)$', na=False)
    c = c.str.strip('()')

    def fix(v):
        if v is None or v != v:
            return v
        if ',' in v and '.' in v:
            return v.replace('.', '').replace(',', '.') if v.rfind(',') > v.rfind('.') else v.replace(',', '')
        if ',' in v:
            return v.replace(',', '.')
        return v
    c = c.map(fix)
    num = pd.to_numeric(c, errors='coerce')
    num = num * mult.fillna(1)
    num = num.where(~neg, -num)
    valid = s.notna() & (t != '') & (t.str.lower() != 'nan')
    if valid.sum() == 0 or num[valid].notna().mean() < 0.9:
        return None
    num[~valid] = np.nan
    return num


def parse_date_series(s):
    """Détecte les dates (jj/mm/aaaa, aaaa-mm-jj...) ; retourne une Series datetime ou None."""
    if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s):
        return None
    t = s.dropna().astype(str).str.strip()
    t = t[t != '']
    if len(t) == 0:
        return None
    smp = t.head(300)
    if not smp.str.contains(r'[/\-\.]|\d{4}', regex=True).mean() > 0.9:
        return None
    if smp.str.fullmatch(r'-?[\d.,\s]+').mean() > 0.5:
        return None
    iso = smp.str.match(r'^\d{4}-\d{1,2}-\d{1,2}').mean() > 0.9
    parsed = pd.to_datetime(smp, errors='coerce', dayfirst=not iso)
    if parsed.notna().mean() < 0.9:
        return None
    out = pd.to_datetime(s.astype(str).str.strip(), errors='coerce', dayfirst=not iso)
    return out


def clean_imported_dataframe(df):
    """Normalise un jeu importé : colonnes de nombres en texte -> numériques, dates -> datetime."""
    d = df.copy()
    for c in d.columns:
        col = d[c]
        if pd.api.types.is_numeric_dtype(col) or pd.api.types.is_datetime64_any_dtype(col):
            continue
        dt = parse_date_series(col)
        if dt is not None:
            d[c] = dt
            continue
        num = parse_number_series(col)
        if num is not None:
            d[c] = num
    return d


def _is_cat(s):
    return (not pd.api.types.is_numeric_dtype(s)) or s.dtype == bool


def preprocess_dataframe(df, target, features, time_col=None, entity_col=None, structure='cross_section'):
    d = df.copy()
    steps = []
    n_before = len(d)

    def add(var, prob, trait, detail=''):
        steps.append({'variable': var, 'probleme': prob, 'traitement': trait, 'detail': detail})

    used = [c for c in [target] + list(features) if c in d.columns]

    # 1. nombres écrits en texte
    for c in used:
        conv = _numeric_like(d[c])
        if conv is not None:
            d[c] = conv
            add(c, 'Nombres stockés comme du texte', 'Conversion en valeurs numériques', 'virgule décimale et espaces gérés')

    # 2. ordre chronologique
    sort_cols = []
    if entity_col and entity_col in d.columns:
        sort_cols.append(entity_col)
    if time_col and time_col in d.columns:
        sort_cols.append(time_col)
    if structure in ('time_series', 'panel') and sort_cols:
        try:
            tmp = d[time_col]
            if not pd.api.types.is_numeric_dtype(tmp):
                d['__t'] = pd.to_datetime(tmp, errors='coerce')
                sort_cols = [c if c != time_col else '__t' for c in sort_cols]
            d = d.sort_values(sort_cols).drop(columns=['__t'], errors='ignore').reset_index(drop=True)
        except Exception:
            pass

    # 3. cible
    if target in d.columns:
        miss = int(d[target].isna().sum())
        if miss:
            share = miss / max(len(d), 1)
            if structure == 'time_series' and pd.api.types.is_numeric_dtype(d[target]) and share <= MAX_GAP_SHARE_TARGET:
                d[target] = d[target].interpolate(method='linear', limit_direction='both')
                add(target, f'{miss} valeur(s) manquante(s) dans la série ({100 * share:.1f} %)',
                    'Interpolation linéaire entre les dates voisines', 'préserve la continuité de la série ; aucune ligne supprimée')
            elif structure == 'panel' and entity_col in d.columns and pd.api.types.is_numeric_dtype(d[target]) and share <= MAX_GAP_SHARE_TARGET:
                d[target] = d.groupby(entity_col)[target].transform(lambda x: x.interpolate(limit_direction='both'))
                left = int(d[target].isna().sum())
                if left:
                    d = d[d[target].notna()]
                add(target, f'{miss} valeur(s) manquante(s) ({100 * share:.1f} %)', 'Interpolation linéaire à l\'intérieur de chaque unité',
                    f'{left} ligne(s) restante(s) supprimée(s)' if left else '')
            else:
                d = d[d[target].notna()]
                add(target, f'{miss} valeur(s) manquante(s) ({100 * share:.1f} %)', 'Suppression des lignes concernées',
                    "la variable à expliquer n'est jamais imputée pour ne pas fabriquer d'information")

    # 4. variables explicatives
    keep_feats = []
    for c in features:
        if c not in d.columns:
            continue
        s = d[c]
        miss = int(s.isna().sum())
        if miss == 0:
            keep_feats.append(c)
            continue
        share = miss / max(len(d), 1)
        if share > MAX_MISSING_FEATURE:
            d = d.drop(columns=[c])
            add(c, f'{100 * share:.0f} % de valeurs manquantes', 'Variable retirée', f'au-delà de {int(100 * MAX_MISSING_FEATURE)} % l\'imputation serait trop spéculative')
            continue
        if _is_cat(s):
            if share > 0.15:
                d[c] = s.astype(object).where(s.notna(), 'Manquant')
                add(c, f'{miss} valeur(s) manquante(s) ({100 * share:.1f} %)', 'Création d\'une modalité « Manquant »', 'l\'absence d\'information peut être informative')
            else:
                mode = s.mode(dropna=True)
                d[c] = s.fillna(mode.iloc[0] if len(mode) else 'Manquant')
                add(c, f'{miss} valeur(s) manquante(s) ({100 * share:.1f} %)', 'Remplacement par la modalité la plus fréquente (mode)')
        else:
            if structure == 'time_series':
                d[c] = s.interpolate(method='linear', limit_direction='both')
                add(c, f'{miss} valeur(s) manquante(s) ({100 * share:.1f} %)', 'Interpolation linéaire dans le temps')
            elif structure == 'panel' and entity_col in d.columns:
                d[c] = d.groupby(entity_col)[c].transform(lambda x: x.interpolate(limit_direction='both'))
                d[c] = d[c].fillna(d[c].median())
                add(c, f'{miss} valeur(s) manquante(s) ({100 * share:.1f} %)', 'Interpolation dans chaque unité, puis médiane globale si l\'unité est vide')
            else:
                x = s.dropna()
                skew = float(x.skew()) if len(x) > 2 else 0.0
                if abs(skew) > 1:
                    d[c] = s.fillna(x.median())
                    add(c, f'{miss} valeur(s) manquante(s) ({100 * share:.1f} %)', 'Remplacement par la médiane',
                        f'distribution asymétrique (asymétrie = {skew:.2f}) : la médiane résiste aux valeurs extrêmes')
                else:
                    d[c] = s.fillna(x.mean())
                    add(c, f'{miss} valeur(s) manquante(s) ({100 * share:.1f} %)', 'Remplacement par la moyenne',
                        f'distribution à peu près symétrique (asymétrie = {skew:.2f})')
        keep_feats.append(c)

    # 5. encodage
    cats = [c for c in keep_feats if c in d.columns and _is_cat(d[c])]
    for c in cats:
        k = d[c].nunique()
        if k > 20:
            add(c, f'{k} modalités', 'Variable ignorée dans les modèles', 'trop de modalités pour un encodage fiable')
        else:
            add(c, f'Variable qualitative à {k} modalités', 'Encodage binaire (one-hot)', f'{k - 1} indicatrice(s) créée(s), la première modalité sert de référence')
    if target in d.columns and _is_cat(d[target]):
        k = d[target].nunique()
        add(target, f'Variable à expliquer qualitative ({k} classes)', 'Encodage des classes en entiers' + (' (0/1)' if k == 2 else ''))

    # 6. échelle
    nums = [c for c in keep_feats if c in d.columns and not _is_cat(d[c]) and d[c].nunique() > 2]
    if len(nums) >= 2:
        sds = {c: float(d[c].std()) for c in nums if float(d[c].std()) > 0}
        if sds:
            hi, lo = max(sds, key=sds.get), min(sds, key=sds.get)
            ratio = sds[hi] / sds[lo]
            if ratio > 10:
                add('Variables numériques', f'Échelles très différentes (écart-type de {hi} = {ratio:.0f} × celui de {lo})',
                    'Standardisation (moyenne 0, écart-type 1)',
                    'appliquée automatiquement pour les modèles sensibles à l\'échelle : Ridge, Lasso, Elastic Net, SVM/SVR, k plus proches voisins, '
                    'régression logistique, réseaux de neurones. Calculée sur l\'échantillon d\'apprentissage seulement pour éviter toute fuite d\'information.')
            else:
                add('Variables numériques', 'Échelles comparables', 'Standardisation conservée pour les modèles pénalisés et les réseaux de neurones',
                    'les modèles à base d\'arbres et la régression linéaire classique n\'en ont pas besoin')
    if structure == 'time_series':
        pass

    d = d.reset_index(drop=True)
    summary = []
    if n_before != len(d):
        summary.append(f"{n_before - len(d)} ligne(s) supprimée(s) (cible manquante) ; {len(d)} observations conservées sur {n_before}.")
    imputed = [s['variable'] for s in steps if 'manquante' in s['probleme'] and 'Suppression' not in s['traitement'] and 'retirée' not in s['traitement']]
    if imputed:
        summary.append("Valeurs manquantes traitées dans : " + ', '.join(imputed) + '.')
    if not steps:
        summary.append("Aucun traitement nécessaire : pas de valeur manquante, variables déjà exploitables.")
    return d, {'steps': steps, 'n_before': n_before, 'n_after': len(d), 'summary': summary}
