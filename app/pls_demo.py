# -*- coding: utf-8 -*-
"""Jeu de données d'exemple pour le laboratoire SmartPLS : enquête de satisfaction (simulée, 300 répondants)."""
import numpy as np
import pandas as pd

MODEL = {
    'constructs': [
        {'name': 'Qualité', 'mode': 'A', 'indicators': ['QP1', 'QP2', 'QP3', 'QP4']},
        {'name': 'Prix perçu', 'mode': 'A', 'indicators': ['PX1', 'PX2', 'PX3']},
        {'name': 'Satisfaction', 'mode': 'A', 'indicators': ['SA1', 'SA2', 'SA3', 'SA4']},
        {'name': 'Fidélité', 'mode': 'A', 'indicators': ['FI1', 'FI2', 'FI3']},
    ],
    'paths': [['Qualité', 'Satisfaction'], ['Prix perçu', 'Satisfaction'], ['Satisfaction', 'Fidélité'], ['Qualité', 'Fidélité']],
}


def demo_dataframe(n=300, seed=7):
    rng = np.random.default_rng(seed)
    qp = rng.normal(size=n)
    px = 0.3 * qp + rng.normal(size=n) * 0.95
    sa = 0.55 * qp + 0.22 * px + rng.normal(size=n) * 0.78
    fi = 0.58 * sa + 0.12 * qp + rng.normal(size=n) * 0.75

    def likert(lv, lam, k, prefix, shift=0.0):
        out = {}
        for i in range(k):
            l = lam[i % len(lam)]
            x = l * lv + np.sqrt(1 - l * l) * rng.normal(size=n) + shift
            out[f'{prefix}{i + 1}'] = np.clip(np.round(4 + 1.1 * x), 1, 7).astype(int)
        return out
    d = {}
    d.update(likert(qp, [0.86, 0.82, 0.78, 0.74], 4, 'QP'))
    d.update(likert(px, [0.80, 0.76, 0.68], 3, 'PX'))
    d.update(likert(sa, [0.88, 0.84, 0.80, 0.42], 4, 'SA'))   # SA4 volontairement faible (exercice sur les loadings)
    d.update(likert(fi, [0.90, 0.86, 0.82], 3, 'FI'))
    df = pd.DataFrame(d)
    df['AGE'] = np.clip(np.round(rng.normal(36, 10, n)), 18, 70).astype(int)
    df['SEXE'] = rng.integers(0, 2, n)
    return df
