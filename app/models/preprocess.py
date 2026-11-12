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
    """Convertit une colonne texte en numérique si au moins 90 % des valeurs s'y prêtent."""
    if pd.api.types.is_numeric_dtype(s) or s.dtype == bool:
        return None
    t = s.dropna().astype(str).str.strip()
    if len(t) == 0:
        return None
    cleaned = (t.str.replace(' ', '', regex=False).str.replace(' ', '', regex=False)
                 .str.replace('%', '', regex=False))
    # « 1.234,5 » ou « 1,5 » -> « 1234.5 » / « 1.5 »
    has_comma = cleaned.str.contains(',', regex=False)
    cleaned = cleaned.where(~has_comma, cleaned.str.replace('.', '', regex=False).str.replace(',', '.', regex=False))
    num = pd.to_numeric(cleaned, errors='coerce')
    if num.notna().mean() >= 0.9:
        full = pd.to_numeric(
            s.astype(str).str.strip().str.replace(' ', '', regex=False).str.replace(' ', '', regex=False)
             .str.replace('%', '', regex=False).map(lambda v: v.replace('.', '').replace(',', '.') if ',' in v else v),
            errors='coerce')
        full[s.isna()] = np.nan
        return full
    return None


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
