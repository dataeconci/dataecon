# -*- coding: utf-8 -*-
"""
Génération de scripts reproductibles à partir d'une analyse :
Python (.py et notebook .ipynb), R (.R), Stata (.do), SQL (PostgreSQL).

cfg = {file, dataset_name, target, features, time_col, entity_col, structure, kind,
       models [ids], forecast_steps}
"""
import json
from datetime import datetime

TS_IDS = ('ar', 'ma', 'arma', 'arima', 'sarima', 'arimax')
ML_REG = ('rf_reg', 'gb_reg', 'svr', 'knn_reg', 'tree_reg', 'mlp_reg')
ML_CLF = ('rf_clf', 'gb_clf', 'svm_clf', 'knn_clf', 'tree_clf', 'nb_clf', 'mlp_clf', 'mlogit')

NAMES = {
    'ols': 'Moindres carrés ordinaires', 'ridge': 'Ridge', 'lasso': 'Lasso', 'elasticnet': 'Elastic Net', 'poisson': 'Poisson', 'negbin': 'Binomiale négative',
    'panel_pooled': 'Panel empilé', 'panel_fe': 'Panel à effets fixes', 'panel_re': 'Panel à effets aléatoires',
    'ar': 'AR', 'ma': 'MA', 'arma': 'ARMA', 'arima': 'ARIMA', 'sarima': 'SARIMA', 'arimax': 'ARIMAX', 'holtwinters': 'Holt-Winters', 'var': 'VAR',
    'garch': 'GARCH(1,1)', 'arch': 'ARCH(q)', 'egarch': 'EGARCH(1,1)', 'gjr': 'GJR-GARCH', 'risk': 'Mesures de risque (VaR, ES)',
    'logit': 'Logit', 'mlogit': 'Logit multinomial', 'rf_reg': 'Forêt aléatoire', 'gb_reg': 'Gradient Boosting', 'svr': 'SVR', 'knn_reg': 'k plus proches voisins',
    'tree_reg': 'Arbre de décision', 'rf_clf': 'Forêt aléatoire (classification)', 'gb_clf': 'Gradient Boosting (classification)', 'svm_clf': 'SVM',
    'knn_clf': 'k plus proches voisins (classification)', 'tree_clf': 'Arbre de décision (classification)', 'nb_clf': 'Naive Bayes',
    'mlp_reg': 'Réseau de neurones', 'mlp_clf': 'Réseau de neurones (classification)', 'mlp_ts': 'Réseau de neurones autorégressif',
}


def _name(m):
    return NAMES.get(m, m)


def _q(s):
    return json.dumps(s, ensure_ascii=False)


def _pq(v):
    return 'None' if v is None else json.dumps(v, ensure_ascii=False)


def _is_csv(cfg):
    return str(cfg.get('file', '')).lower().endswith(('.csv', '.txt', '.tsv'))


# =====================================================================================================
# PYTHON
# =====================================================================================================
def _py_header(cfg):
    return f'''# -*- coding: utf-8 -*-
"""
Analyse reproductible générée par DataEcon.Ci le {datetime.now().strftime('%d/%m/%Y')}
Jeu de données : {cfg.get('dataset_name', '')}
Variable cible : {cfg['target']}
Variables explicatives : {', '.join(cfg['features']) or '(aucune)'}
Structure : {cfg.get('structure', '')}
Modèles : {', '.join(_name(m) for m in cfg['models'])}

Prérequis : pip install pandas numpy scipy matplotlib statsmodels scikit-learn arch linearmodels openpyxl
Placez le fichier de données à côté de ce script et ajustez FICHIER si besoin.
"""'''


def _py_load(cfg):
    read = (f"pd.read_csv(FICHIER, sep=None, engine='python')" if _is_csv(cfg) else "pd.read_excel(FICHIER)")
    return f'''# %% [markdown]
# ## 1. Chargement des données

# %%
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

FICHIER = {_q(cfg.get('file', 'donnees.csv'))}
CIBLE = {_q(cfg['target'])}
EXPLICATIVES = {json.dumps(cfg['features'], ensure_ascii=False)}
COL_TEMPS = {_pq(cfg.get('time_col'))}
COL_UNITE = {_pq(cfg.get('entity_col'))}
STRUCTURE = {_q(cfg.get('structure', 'cross_section'))}   # cross_section | time_series | panel
SEED = 42

df = {read}
df.columns = [str(c).strip() for c in df.columns]
print(df.shape)
df.head()
'''


def _py_prep(cfg):
    return '''# %% [markdown]
# ## 2. Préparation des données
# Conversion des nombres écrits en texte, valeurs manquantes (méthode selon la structure), encodage.

# %%
d = df.copy()
cols = [CIBLE] + EXPLICATIVES

# 2.1 nombres stockés comme du texte (virgule décimale)
for c in cols:
    if not pd.api.types.is_numeric_dtype(d[c]):
        t = d[c].astype(str).str.strip().str.replace("\\u00a0", "", regex=False).str.replace(" ", "", regex=False)
        t = t.where(~t.str.contains(","), t.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
        num = pd.to_numeric(t.where(d[c].notna()), errors="coerce")
        if num.notna().sum() >= 0.9 * d[c].notna().sum():
            d[c] = num

# 2.2 ordre chronologique
if STRUCTURE in ("time_series", "panel") and COL_TEMPS:
    d["_t"] = pd.to_numeric(d[COL_TEMPS], errors="coerce") if pd.api.types.is_numeric_dtype(d[COL_TEMPS]) else pd.to_datetime(d[COL_TEMPS], errors="coerce")
    d = d.sort_values(([COL_UNITE] if COL_UNITE else []) + ["_t"]).drop(columns="_t").reset_index(drop=True)

# 2.3 valeurs manquantes
print("Valeurs manquantes avant traitement :\\n", d[cols].isna().sum())
if STRUCTURE == "time_series" and pd.api.types.is_numeric_dtype(d[CIBLE]):
    d[CIBLE] = d[CIBLE].interpolate(limit_direction="both")          # interpolation linéaire de la série
else:
    d = d[d[CIBLE].notna()]                                           # la cible n'est jamais imputée
for c in EXPLICATIVES:
    if d[c].isna().sum() == 0:
        continue
    if d[c].isna().mean() > 0.60:
        EXPLICATIVES.remove(c); continue                              # trop de valeurs manquantes
    if not pd.api.types.is_numeric_dtype(d[c]):
        if d[c].isna().mean() > 0.15:
            d[c] = d[c].fillna("Manquant")
        else:
            d[c] = d[c].fillna(d[c].mode().iloc[0])
    elif STRUCTURE == "time_series":
        d[c] = d[c].interpolate(limit_direction="both")
    elif STRUCTURE == "panel" and COL_UNITE:
        d[c] = d.groupby(COL_UNITE)[c].transform(lambda x: x.interpolate(limit_direction="both")).fillna(d[c].median())
    else:
        d[c] = d[c].fillna(d[c].median() if abs(d[c].skew()) > 1 else d[c].mean())
d = d.reset_index(drop=True)

# 2.4 encodage des variables qualitatives (indicatrices, première modalité en référence)
quali = [c for c in EXPLICATIVES if not pd.api.types.is_numeric_dtype(d[c]) or d[c].dtype == bool]
X = pd.get_dummies(d[EXPLICATIVES], columns=quali, drop_first=True, dtype=float).astype(float) if EXPLICATIVES else pd.DataFrame(index=d.index)
y = d[CIBLE]
print("Variables du modèle :", list(X.columns))
# La standardisation (StandardScaler) est appliquée dans les pipelines des modèles sensibles à l'échelle.
'''


def _py_desc(cfg):
    return '''# %% [markdown]
# ## 3. Statistiques descriptives et graphiques

# %%
num = [c for c in [CIBLE] + EXPLICATIVES if pd.api.types.is_numeric_dtype(d[c])]
display(d[num].describe().T.assign(asymetrie=d[num].skew(), aplatissement=d[num].kurt())) if "display" in dir() else print(d[num].describe().T)
print(d[num].corr().round(2))

fig, axes = plt.subplots(1, 3, figsize=(13, 3.5))
d[CIBLE].dropna().plot.hist(bins=25, ax=axes[0], color="#1f5f99"); axes[0].set_title("Histogramme de " + CIBLE)
d[num].boxplot(ax=axes[1]); axes[1].set_title("Boîtes à moustaches")
stats.probplot(pd.to_numeric(d[CIBLE], errors="coerce").dropna(), dist="norm", plot=axes[2]); axes[2].set_title("QQ-plot")
plt.tight_layout(); plt.show()

for c in [x for x in num if x != CIBLE][:4]:
    if pd.api.types.is_numeric_dtype(d[CIBLE]):
        z = d[[c, CIBLE]].dropna(); lr = stats.linregress(z[c], z[CIBLE])
        plt.scatter(z[c], z[CIBLE], s=10, alpha=.5); plt.plot(z[c], lr.intercept + lr.slope * z[c], color="#c2a15a")
        plt.xlabel(c); plt.ylabel(CIBLE); plt.title(f"{CIBLE} selon {c} (pente = {lr.slope:.3f})"); plt.show()
'''


def _py_split(cfg):
    chrono = cfg.get('structure') in ('time_series',)
    clf = cfg.get('kind') in ('binary', 'multiclass')
    if clf:
        enc = '''from sklearn.preprocessing import LabelEncoder
le = LabelEncoder(); y = pd.Series(le.fit_transform(y.astype(str)), index=y.index)
CLASSES = list(le.classes_); print("Classes :", CLASSES)
'''
    else:
        enc = ''
    if chrono:
        sp = '''# Partition chronologique 60 / 20 / 20
a, b = int(len(X) * .6), int(len(X) * .8)
Xtr, ytr, Xva, yva, Xte, yte = X.iloc[:a], y.iloc[:a], X.iloc[a:b], y.iloc[a:b], X.iloc[b:], y.iloc[b:]'''
    else:
        sp = f'''# Partition aléatoire 60 / 20 / 20{' stratifiée' if clf else ''}
Xtmp, Xte, ytmp, yte = train_test_split(X, y, test_size=.2, random_state=SEED{', stratify=y' if clf else ''})
Xtr, Xva, ytr, yva = train_test_split(Xtmp, ytmp, test_size=.25, random_state=SEED{', stratify=ytmp' if clf else ''})'''
    return f'''# %% [markdown]
# ## 4. Partition train / validation / test
# Apprentissage : estimation ; validation : choix des hyperparamètres ; test : évaluation finale unique.

# %%
from sklearn.model_selection import train_test_split
{enc}{sp}
print(len(Xtr), len(Xva), len(Xte))
'''


GRID_CODE = '''
GRILLES = {
    "rf": {"n_estimators": [100, 200, 300], "max_depth": [4, 8, 12, None], "min_samples_leaf": [1, 3, 5]},
    "gb": {"n_estimators": [100, 200], "learning_rate": [.03, .05, .1], "max_depth": [2, 3, 4], "subsample": [.8, 1.0]},
    "svm": {"C": [.5, 1, 3, 10, 30], "gamma": ["scale", "auto"]},
    "knn": {"n_neighbors": [3, 5, 7, 11, 15, 25], "weights": ["uniform", "distance"]},
    "tree": {"max_depth": [3, 4, 5, 6, 8, None], "min_samples_leaf": [1, 5, 10, 20]},
    "mlp": {"hidden_layer_sizes": [(32,), (64, 32), (128, 64)], "alpha": [1e-4, 1e-3, 1e-2], "learning_rate_init": [1e-3, 1e-2]},
}

def optimiser(fabrique, grille, score, n_essais=6):
    """Recherche aléatoire : on garde la configuration qui maximise le score sur la VALIDATION."""
    rng = np.random.RandomState(SEED); essais = [{}]
    while len(essais) < n_essais:
        p = {k: v[rng.randint(len(v))] for k, v in grille.items()}
        if p not in essais:
            essais.append(p)
    res = []
    for p in essais:
        m = fabrique(**p).fit(Xtr, ytr)
        res.append((score(m, Xva, yva), p))
    res.sort(key=lambda t: -t[0])
    print(pd.DataFrame([{"score_validation": s, **p} for s, p in res]).head(10))
    return res[0][1]
'''


def _py_models(cfg):
    out = ['''# %% [markdown]
# ## 5. Modèles
''']
    ids = cfg['models']
    kind = cfg.get('kind')
    needs_ml = any(m in ML_REG + ML_CLF for m in ids)
    if needs_ml:
        out.append('# %%\nfrom sklearn.pipeline import make_pipeline\nfrom sklearn.preprocessing import StandardScaler\nfrom sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error, accuracy_score, f1_score, roc_auc_score, roc_curve, confusion_matrix, precision_recall_curve\n' + GRID_CODE)
    for m in ids:
        out.append(f'# %% [markdown]\n# ### {_name(m)}\n')
        out.append('# %%\n' + _py_model(m, cfg))
    return '\n'.join(out)


def _py_model(m, cfg):
    reg = cfg.get('kind') == 'continuous'
    T = cfg.get('time_col')
    if m == 'ols':
        return '''import statsmodels.api as sm
Xc = sm.add_constant(X)
ols = sm.OLS(y, Xc).fit()
print(ols.summary())
ols_rob = sm.OLS(y, Xc).fit(cov_type="HC3")      # erreurs standard robustes (robustesse)
print(ols_rob.summary().tables[1])
from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset
print("Breusch-Pagan p =", het_breuschpagan(ols.resid, Xc)[1])
try:
    print("RESET p =", float(linear_reset(ols, power=2, use_f=True).pvalue))
except Exception as e:      # incompatibilité de versions pandas / statsmodels
    print("RESET non calculé :", e)'''
    if m in ('ridge', 'lasso', 'elasticnet'):
        cls = {'ridge': 'RidgeCV(alphas=np.logspace(-3, 3, 30))', 'lasso': 'LassoCV(cv=5, random_state=SEED)', 'elasticnet': 'ElasticNetCV(l1_ratio=[.2, .5, .8, 1], cv=5, random_state=SEED)'}[m]
        return f'''from sklearn.linear_model import RidgeCV, LassoCV, ElasticNetCV
pen = make_pipeline(StandardScaler(), {cls}).fit(pd.concat([Xtr, Xva]), pd.concat([ytr, yva]))
print("R² test :", r2_score(yte, pen.predict(Xte)))
print(dict(zip(X.columns, pen[-1].coef_.round(4))))''' if 'make_pipeline' in ''.join(['make_pipeline']) else ''
    if m in ('poisson', 'negbin'):
        fit = "sm.GLM(y, Xc, family=sm.families.Poisson()).fit()" if m == 'poisson' else "sm.NegativeBinomial(y, Xc).fit()"
        return f'''import statsmodels.api as sm
Xc = sm.add_constant(X)
mod = {fit}
print(mod.summary())
print("Rapport de dispersion (Pearson/ddl) :", float(sm.GLM(y, Xc, family=sm.families.Poisson()).fit().pearson_chi2 / (len(y) - Xc.shape[1])))'''
    if m.startswith('panel_'):
        which = {'panel_pooled': 'PooledOLS(y_p, sm.add_constant(X_p))', 'panel_fe': 'PanelOLS(y_p, X_p, entity_effects=True)', 'panel_re': 'RandomEffects(y_p, sm.add_constant(X_p))'}[m]
        return f'''import statsmodels.api as sm
from linearmodels.panel import PanelOLS, PooledOLS, RandomEffects
pan = d.set_index([COL_UNITE, COL_TEMPS])
X_p = pd.get_dummies(pan[EXPLICATIVES], columns=quali, drop_first=True, dtype=float).astype(float); y_p = pan[CIBLE]
res = {which}.fit(cov_type="clustered", cluster_entity=True)
print(res.summary)'''
    if m in TS_IDS:
        order_code = {
            'ar': 'grille = [((p, d_, 0), (0, 0, 0, 0)) for p in range(1, 4)]',
            'ma': 'grille = [((0, d_, q), (0, 0, 0, 0)) for q in range(1, 4)]',
            'arma': 'grille = [((p, 0, q), (0, 0, 0, 0)) for p in range(1, 3) for q in range(1, 3)]',
            'arima': 'grille = [((p, d_, q), (0, 0, 0, 0)) for p in range(3) for q in range(3)]',
            'sarima': 'grille = [((p, d_, q), (1, 1 if d_ == 0 else 0, 1, 12)) for p in range(2) for q in range(2)]   # période 12 : adaptez-la',
            'arimax': 'grille = [((p, d_, q), (0, 0, 0, 0)) for p in range(3) for q in range(3)]',
        }[m]
        exog = 'exog = X if EXPLICATIVES else None' if m == 'arimax' else 'exog = None'
        return f'''from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller
serie = y.reset_index(drop=True)
d_ = 0 if adfuller(serie.dropna())[1] < .05 else 1          # ordre d'intégration (test ADF)
{exog}
{order_code}
meilleur = None
for ordre, saison in grille:
    try:
        r_ = SARIMAX(serie, exog=exog, order=ordre, seasonal_order=saison, trend="c" if d_ == 0 else "n").fit(disp=False)
        if meilleur is None or r_.aic < meilleur[0].aic:
            meilleur = (r_, ordre, saison)
    except Exception:
        pass
res, ordre, saison = meilleur
print("Modèle retenu (AIC) :", ordre, saison); print(res.summary())
print(res.get_forecast({cfg.get('forecast_steps', 12)}{', exog=exog.iloc[-%d:]' % cfg.get('forecast_steps', 12) if m == 'arimax' else ''}).summary_frame())'''
    if m == 'holtwinters':
        return f'''from statsmodels.tsa.holtwinters import ExponentialSmoothing
serie = y.reset_index(drop=True)
hw = ExponentialSmoothing(serie, trend="add", damped_trend=True, seasonal=None).fit()
print(hw.summary()); print(hw.forecast({cfg.get('forecast_steps', 12)}))'''
    if m == 'var':
        return '''from statsmodels.tsa.api import VAR
data = pd.concat([y, X], axis=1).diff().dropna()
res = VAR(data).fit(maxlags=6, ic="aic"); print(res.summary())'''
    if m == 'mlp_ts':
        return '''from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
p = 6
M = np.column_stack([y.values[i:len(y) - p + i] for i in range(p)]); cible = y.values[p:]
k = int(.8 * len(M))
mlp = make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=800, random_state=SEED)).fit(M[:k], cible[:k])
print("RMSE test :", np.sqrt(np.mean((cible[k:] - mlp.predict(M[k:])) ** 2)))'''
    if m in ('garch', 'arch', 'egarch', 'gjr', 'risk'):
        kw = {'garch': 'vol="GARCH", p=1, q=1', 'arch': 'vol="ARCH", p=3', 'egarch': 'vol="EGARCH", p=1, o=1, q=1', 'gjr': 'vol="GARCH", p=1, o=1, q=1', 'risk': 'vol="GARCH", p=1, q=1'}[m]
        ret = '''# Rendements : logarithmiques en % si la série est un niveau (prix, indice), sinon utilisée telle quelle
s = pd.Series(d[CIBLE].values, dtype=float).dropna()
niveau = (s > 0).all() and s.autocorr(1) > 0.95
ret = (100 * np.log(s).diff().dropna()) if niveau else (s - s.mean() if s.std() >= .1 else s * 100)
ret = ret.reset_index(drop=True)
print("Rendements calculés :", "logarithmiques (%)" if niveau else "série utilisée telle quelle"); print(ret.describe())
from arch import arch_model
a_, b_ = int(len(ret) * .70), int(len(ret) * .85)          # partition chronologique 70 / 15 / 15'''
        base = f'''mod = arch_model(ret, mean="Constant", dist="t", {kw})
res = mod.fit(last_obs=b_, disp="off")                 # estimé sur apprentissage + validation
print(res.summary())
s2 = mod.fix(res.params).conditional_volatility.values ** 2   # variance prévue à un pas
e2 = (ret.values - res.params["mu"]) ** 2
qlike = lambda e, s: np.mean(np.log(s) + e / s)
print("QLIKE test :", qlike(e2[b_:], s2[b_:]), " | variance constante :", qlike(e2[b_:], np.full(len(e2) - b_, e2[:b_].mean())))
print(res.forecast(horizon={cfg.get('forecast_steps', 12)}{', method="simulation", reindex=False' if m == 'egarch' else ''}).variance.iloc[-1] ** .5)'''
        if m == 'risk':
            base += '''
x = ret.values / 100
for p_ in (0.95, 0.99):
    var = -np.quantile(x, 1 - p_); es = -x[x <= -var].mean()
    print(f"VaR {int(p_*100)} % historique = {var:.4f} ; ES = {es:.4f}")'''
        return ret + '\n' + base
    if m == 'logit':
        return '''import statsmodels.api as sm
logit = sm.Logit(ytr, sm.add_constant(Xtr)).fit(disp=0); print(logit.summary())
print("Odds ratios :\\n", np.exp(logit.params))
pv = logit.predict(sm.add_constant(Xva)); ths = np.linspace(.05, .95, 19)
seuil = ths[int(np.argmax([f1_score(yva, (pv >= t).astype(int)) for t in ths]))]      # seuil optimisé sur la validation
pt = logit.predict(sm.add_constant(Xte))
print("Seuil :", seuil, "| AUC test :", roc_auc_score(yte, pt), "| exactitude :", accuracy_score(yte, (pt >= seuil).astype(int)))
fpr, tpr, _ = roc_curve(yte, pt); plt.plot(fpr, tpr); plt.plot([0, 1], [0, 1], "--"); plt.title("Courbe ROC (test)"); plt.show()'''
    if m in ML_REG + ML_CLF:
        spec = {
            'rf_reg': ('RandomForestRegressor', 'from sklearn.ensemble import RandomForestRegressor', 'rf', False),
            'rf_clf': ('RandomForestClassifier', 'from sklearn.ensemble import RandomForestClassifier', 'rf', False),
            'gb_reg': ('GradientBoostingRegressor', 'from sklearn.ensemble import GradientBoostingRegressor', 'gb', False),
            'gb_clf': ('GradientBoostingClassifier', 'from sklearn.ensemble import GradientBoostingClassifier', 'gb', False),
            'svr': ('SVR', 'from sklearn.svm import SVR', 'svm', True),
            'svm_clf': ('SVC', 'from sklearn.svm import SVC', 'svm', True),
            'knn_reg': ('KNeighborsRegressor', 'from sklearn.neighbors import KNeighborsRegressor', 'knn', True),
            'knn_clf': ('KNeighborsClassifier', 'from sklearn.neighbors import KNeighborsClassifier', 'knn', True),
            'tree_reg': ('DecisionTreeRegressor', 'from sklearn.tree import DecisionTreeRegressor', 'tree', False),
            'tree_clf': ('DecisionTreeClassifier', 'from sklearn.tree import DecisionTreeClassifier', 'tree', False),
            'mlp_reg': ('MLPRegressor', 'from sklearn.neural_network import MLPRegressor', 'mlp', True),
            'mlp_clf': ('MLPClassifier', 'from sklearn.neural_network import MLPClassifier', 'mlp', True),
            'nb_clf': ('GaussianNB', 'from sklearn.naive_bayes import GaussianNB', None, False),
            'mlogit': ('LogisticRegression', 'from sklearn.linear_model import LogisticRegression', None, True),
        }[m]
        cls, imp, gk, scale = spec
        clf = m in ML_CLF
        extra = ', probability=True' if m == 'svm_clf' else (', max_iter=1000' if m == 'mlogit' else (', max_iter=600, early_stopping=True' if m.startswith('mlp') else ''))
        extra += ', random_state=SEED' if m in ('rf_reg', 'rf_clf', 'gb_reg', 'gb_clf', 'tree_reg', 'tree_clf', 'mlp_reg', 'mlp_clf') else ''
        if scale:
            fab = f'lambda **p: make_pipeline(StandardScaler(), {cls}({extra.lstrip(", ")}{", " if extra else ""}**p))'
        else:
            fab = f'lambda **p: {cls}({extra.lstrip(", ")}{", " if extra else ""}**p)'
        score = ('lambda m, X_, y_: roc_auc_score(y_, m.predict_proba(X_)[:, 1]) if len(CLASSES) == 2 else f1_score(y_, m.predict(X_), average="weighted")' if clf else 'lambda m, X_, y_: r2_score(y_, m.predict(X_))')
        grid = f'GRILLES["{gk}"]' if gk else '{}'
        if m in ('svm_clf', 'mlp_clf', 'mlp_reg', 'svr', 'knn_clf', 'knn_reg'):
            prefix = {'svm_clf': 'svc', 'svr': 'svr', 'knn_clf': 'kneighborsclassifier', 'knn_reg': 'kneighborsregressor', 'mlp_clf': 'mlpclassifier', 'mlp_reg': 'mlpregressor'}[m]
        if m == 'mlogit':
            grid = '{"C": [.1, 1, 10]}'
            fab = f'lambda **p: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, **p))'
        if m == 'nb_clf':
            grid = '{"var_smoothing": [1e-9, 1e-8, 1e-7, 1e-6]}'
            fab = 'lambda **p: GaussianNB(**p)'
        # pour les pipelines les paramètres doivent être préfixés par le nom de l'étape finale
        wrap = ''
        if scale and m != 'mlogit':
            pre = {'svm_clf': 'svc', 'svr': 'svr', 'knn_clf': 'kneighborsclassifier', 'knn_reg': 'kneighborsregressor', 'mlp_clf': 'mlpclassifier', 'mlp_reg': 'mlpregressor'}[m]
            fab = f'lambda **p: make_pipeline(StandardScaler(), {cls}({extra.lstrip(", ")}{", " if extra else ""}**p))'
        if clf:
            ev = '''pt = final.predict(Xte); print("Exactitude test :", accuracy_score(yte, pt), "| F1 :", f1_score(yte, pt, average="weighted"))
print(confusion_matrix(yte, pt))
if hasattr(final, "predict_proba"):
    pr = final.predict_proba(Xte)
    if len(CLASSES) == 2:
        print("AUC test :", roc_auc_score(yte, pr[:, 1]))
        fpr, tpr, _ = roc_curve(yte, pr[:, 1]); plt.plot(fpr, tpr, label="ROC test"); plt.plot([0, 1], [0, 1], "--"); plt.legend(); plt.show()
        p_, r_, _ = precision_recall_curve(yte, pr[:, 1]); plt.plot(r_, p_); plt.title("Précision-rappel (test)"); plt.show()'''
        else:
            ev = '''pt = final.predict(Xte)
print("R² test :", r2_score(yte, pt), "| RMSE :", np.sqrt(mean_squared_error(yte, pt)), "| MAE :", mean_absolute_error(yte, pt))
plt.scatter(yte, pt, s=10); plt.plot([yte.min(), yte.max()], [yte.min(), yte.max()], color="#c2a15a"); plt.xlabel("Observé"); plt.ylabel("Prédit"); plt.show()'''
        if scale and gk:
            # préfixe des paramètres pour pipeline
            pre = {'svm_clf': 'svc', 'svr': 'svr', 'knn_clf': 'kneighborsclassifier', 'knn_reg': 'kneighborsregressor', 'mlp_clf': 'mlpclassifier', 'mlp_reg': 'mlpregressor'}.get(m)
            if pre:
                fab = f'lambda **p: make_pipeline(StandardScaler(), {cls}({extra.lstrip(", ")}{", " if extra else ""}**p))'
        return f'''{imp}
fabrique = {fab}
meilleurs = optimiser(fabrique, {grid}, {score})
print("Hyperparamètres retenus :", meilleurs)
final = fabrique(**meilleurs).fit(pd.concat([Xtr, Xva]), pd.concat([ytr, yva]))      # ré-estimation train + validation
{ev}'''
    return '# Modèle non pris en charge dans ce script.'


def make_python(cfg):
    parts = [_py_header(cfg), _py_load(cfg), _py_prep(cfg), _py_desc(cfg)]
    if cfg.get('structure') != 'panel' or any(m in ML_REG + ML_CLF + ('logit',) for m in cfg['models']):
        parts.append(_py_split(cfg))
    parts.append(_py_models(cfg))
    return '\n'.join(parts) + '\n'


def make_notebook(cfg):
    code = make_python(cfg)
    header, *rest = code.split('# %% [markdown]\n', 1)[0], code
    cells = []
    # le docstring d'en-tête devient une cellule texte
    head, body = code.split('# %% [markdown]', 1)
    cells.append({'cell_type': 'markdown', 'metadata': {}, 'source': ['# Analyse DataEcon.Ci\n'] + [l + '\n' for l in head.replace('"""', '').replace('# -*- coding: utf-8 -*-', '').strip().splitlines()]})
    body = '# %% [markdown]' + body
    chunks = body.split('\n# %%')
    for ch in chunks:
        ch = ch.strip('\n')
        if not ch:
            continue
        if ch.startswith('# %% [markdown]') or ch.startswith(' [markdown]'):
            txt = ch.split('\n', 1)[1] if '\n' in ch else ''
            txt = '\n'.join(l[2:] if l.startswith('# ') else l.lstrip('#') for l in txt.splitlines())
            cells.append({'cell_type': 'markdown', 'metadata': {}, 'source': [l + '\n' for l in txt.splitlines()]})
        else:
            c = ch[1:] if ch.startswith('\n') else ch
            c = c.replace('# %%\n', '', 1) if c.startswith('# %%\n') else c
            cells.append({'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [], 'source': [l + '\n' for l in c.strip('\n').splitlines()]})
    nb = {'cells': cells, 'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}, 'language_info': {'name': 'python'}},
          'nbformat': 4, 'nbformat_minor': 4}
    return json.dumps(nb, ensure_ascii=False, indent=1)


# =====================================================================================================
# R
# =====================================================================================================
def make_r(cfg):
    T, E = cfg.get('time_col'), cfg.get('entity_col')
    feats = cfg['features']
    rhs = ' + '.join(f'`{f}`' for f in feats) if feats else '1'
    ids = cfg['models']
    kind = cfg.get('kind')
    clf = kind in ('binary', 'multiclass')
    out = [f'''# Analyse reproductible générée par DataEcon.Ci le {datetime.now().strftime('%d/%m/%Y')}
# Jeu de données : {cfg.get('dataset_name', '')}
# Variable cible : {cfg['target']} | Explicatives : {', '.join(feats) or '(aucune)'}
# Modèles : {', '.join(_name(m) for m in ids)}
#
# Packages : install.packages(c("tidyverse","lmtest","sandwich","glmnet","MASS","plm","forecast","tseries","vars",
#            "rugarch","pROC","randomForest","gbm","e1071","class","rpart","nnet","caret","readxl","zoo"))

suppressPackageStartupMessages({{library(tidyverse); library(lmtest); library(sandwich)}})
set.seed(42)

# ---- 1. Chargement
fichier <- {_q(cfg.get('file', 'donnees.csv'))}
df <- {'read.csv(fichier, sep = ",", dec = ".", stringsAsFactors = FALSE, check.names = FALSE)' if _is_csv(cfg) else 'readxl::read_excel(fichier)'}
names(df) <- trimws(names(df))
cible <- {_q(cfg['target'])}
explicatives <- c({', '.join(_q(f) for f in feats)})
col_temps <- {_q(T) if T else 'NULL'}
col_unite <- {_q(E) if E else 'NULL'}
structure <- {_q(cfg.get('structure', 'cross_section'))}

# ---- 2. Préparation : nombres en texte, valeurs manquantes, encodage
for (v in c(cible, explicatives)) if (!is.numeric(df[[v]])) {{
  t <- gsub(" ", "", as.character(df[[v]])); t <- ifelse(grepl(",", t), gsub(",", ".", gsub("\\\\.", "", t)), t)
  num <- suppressWarnings(as.numeric(t)); if (mean(!is.na(num[!is.na(df[[v]])])) >= 0.9) df[[v]] <- num
}}
if (structure %in% c("time_series", "panel") && !is.null(col_temps)) df <- df[order(if (!is.null(col_unite)) df[[col_unite]] else 1, df[[col_temps]]), ]
if (structure == "time_series" && is.numeric(df[[cible]])) df[[cible]] <- zoo::na.approx(df[[cible]], na.rm = FALSE, rule = 2) else df <- df[!is.na(df[[cible]]), ]
for (v in explicatives) {{
  if (!anyNA(df[[v]])) next
  if (mean(is.na(df[[v]])) > 0.60) {{ explicatives <- setdiff(explicatives, v); next }}
  if (!is.numeric(df[[v]])) {{
    df[[v]][is.na(df[[v]])] <- if (mean(is.na(df[[v]])) > 0.15) "Manquant" else names(which.max(table(df[[v]])))
  }} else if (structure == "time_series") df[[v]] <- zoo::na.approx(df[[v]], na.rm = FALSE, rule = 2)
  else {{ sk <- e1071::skewness(df[[v]], na.rm = TRUE); df[[v]][is.na(df[[v]])] <- if (abs(sk) > 1) median(df[[v]], na.rm = TRUE) else mean(df[[v]], na.rm = TRUE) }}
}}
for (v in explicatives) if (!is.numeric(df[[v]])) df[[v]] <- factor(df[[v]])     # encodage : facteurs (indicatrices automatiques dans les modèles)
{'df[[cible]] <- factor(df[[cible]])' if clf else ''}
cat("Observations :", nrow(df), "\\n")

# ---- 3. Statistiques descriptives et graphiques
num <- names(df)[sapply(df, is.numeric) & names(df) %in% c(cible, explicatives)]
print(summary(df[, c(cible, explicatives)]))
print(round(cor(df[, num], use = "pairwise.complete.obs"), 2))
par(mfrow = c(1, 3))
if (is.numeric(df[[cible]])) {{ hist(df[[cible]], main = paste("Histogramme de", cible), col = "#1f5f99"); boxplot(df[, num], las = 2, main = "Boîtes à moustaches"); qqnorm(df[[cible]]); qqline(df[[cible]]) }}
par(mfrow = c(1, 1))
''']
    if cfg.get('structure') != 'panel' or any(m in ML_REG + ML_CLF + ('logit',) for m in ids):
        out.append(f'''# ---- 4. Partition train / validation / test (60 / 20 / 20)
n <- nrow(df)
{'idx <- 1:n; i_tr <- idx[1:floor(.6*n)]; i_va <- idx[(floor(.6*n)+1):floor(.8*n)]; i_te <- idx[(floor(.8*n)+1):n]   # chronologique' if cfg.get('structure') == 'time_series' else 'idx <- sample(n); i_tr <- idx[1:floor(.6*n)]; i_va <- idx[(floor(.6*n)+1):floor(.8*n)]; i_te <- idx[(floor(.8*n)+1):n]'}
train <- df[i_tr, ]; valid <- df[i_va, ]; test <- df[i_te, ]
formule <- as.formula(paste0("`", cible, "` ~ ", {_q(rhs)}))
rmse <- function(a, b) sqrt(mean((a - b)^2))
''')
    for m in ids:
        out.append(f'# ---- Modèle : {_name(m)}\n' + _r_model(m, cfg, rhs))
    return '\n'.join(out) + '\n'


def _r_model(m, cfg, rhs):
    T, E = cfg.get('time_col'), cfg.get('entity_col')
    steps = cfg.get('forecast_steps', 12)
    if m == 'ols':
        return '''ols <- lm(formule, data = rbind(train, valid))
print(summary(ols))
print(coeftest(ols, vcov = vcovHC(ols, type = "HC3")))          # erreurs robustes
print(bptest(ols)); print(resettest(ols, power = 2))
cat("RMSE test :", rmse(test[[cible]], predict(ols, test)), "\\n")
'''
    if m in ('ridge', 'lasso', 'elasticnet'):
        a = {'ridge': 0, 'lasso': 1, 'elasticnet': 0.5}[m]
        return f'''library(glmnet)
Xm <- model.matrix(formule, rbind(train, valid))[, -1]; ym <- rbind(train, valid)[[cible]]
cv <- cv.glmnet(Xm, ym, alpha = {a}, standardize = TRUE)          # lambda optimisé par validation croisée
print(coef(cv, s = "lambda.min"))
pred <- predict(cv, model.matrix(formule, test)[, -1], s = "lambda.min")
cat("RMSE test :", rmse(test[[cible]], pred), "\\n")
'''
    if m == 'poisson':
        return '''mod <- glm(formule, family = poisson, data = rbind(train, valid)); print(summary(mod))
print(coeftest(mod, vcov = vcovHC(mod, type = "HC1")))
cat("Dispersion :", sum(residuals(mod, "pearson")^2) / mod$df.residual, "\\n")
'''
    if m == 'negbin':
        return '''library(MASS); mod <- glm.nb(formule, data = rbind(train, valid)); print(summary(mod))
'''
    if m.startswith('panel_'):
        mode = {'panel_pooled': 'pooling', 'panel_fe': 'within', 'panel_re': 'random'}[m]
        return f'''library(plm)
pdata <- pdata.frame(df, index = c(col_unite, col_temps))
mod <- plm(formule, data = pdata, model = "{mode}")
print(summary(mod, vcov = function(x) vcovHC(x, cluster = "group")))     # erreurs groupées par unité
{'fe <- plm(formule, data = pdata, model = "within"); re <- plm(formule, data = pdata, model = "random"); print(phtest(fe, re))   # Hausman' if m != 'panel_pooled' else ''}
'''
    if m in TS_IDS:
        arg = {'ar': 'max.q = 0, stationary = TRUE', 'ma': 'max.p = 0, stationary = TRUE', 'arma': 'd = 0', 'arima': 'seasonal = FALSE', 'sarima': 'seasonal = TRUE', 'arimax': 'seasonal = FALSE, xreg = as.matrix(model.matrix(formule, df)[, -1, drop = FALSE])'}[m]
        return f'''library(forecast); library(tseries)
serie <- ts(df[[cible]], frequency = 12)                              # adaptez la fréquence (12, 4, 1...)
print(adf.test(serie)); print(kpss.test(serie))
n_tr <- floor(length(serie) * .7); n_va <- floor(length(serie) * .15)
ajust <- auto.arima(window(serie, end = time(serie)[n_tr]), {arg})     # ordre choisi par AIC sur l'apprentissage
fc_va <- forecast(ajust, h = n_va); print(accuracy(fc_va, window(serie, start = time(serie)[n_tr + 1], end = time(serie)[n_tr + n_va])))
final <- Arima(window(serie, end = time(serie)[n_tr + n_va]), model = ajust)             # ré-estimé train + validation
print(accuracy(forecast(final, h = length(serie) - n_tr - n_va), window(serie, start = time(serie)[n_tr + n_va + 1])))
print(summary(final)); checkresiduals(final)
plot(forecast(Arima(serie, model = ajust), h = {steps}))
'''
    if m == 'holtwinters':
        return f'''serie <- ts(df[[cible]], frequency = 12)
hw <- HoltWinters(serie, gamma = frequency(serie) > 1 && length(serie) >= 2 * frequency(serie)); print(hw)
plot(forecast::forecast(hw, h = {steps}))
'''
    if m == 'var':
        return '''library(vars)
dat <- na.omit(diff(as.matrix(df[, c(cible, explicatives)])))
sel <- VARselect(dat, lag.max = 6, type = "const"); fit <- VAR(dat, p = sel$selection["AIC(n)"], type = "const"); print(summary(fit))
'''
    if m in ('garch', 'arch', 'egarch', 'gjr', 'risk'):
        model = {'garch': 'sGARCH', 'arch': 'sGARCH', 'egarch': 'eGARCH', 'gjr': 'gjrGARCH', 'risk': 'sGARCH'}[m]
        order = '3, 0' if m == 'arch' else '1, 1'
        risk_r = ('VaR95 <- -quantile(ret / 100, .05); ES95 <- -mean((ret / 100)[ret / 100 <= -VaR95]); cat("VaR 95 % :", VaR95, "ES :", ES95, "\\n")' if m == 'risk' else '')
        return f'''library(rugarch)
# Rendements : logarithmiques en % si la série est un niveau (prix, indice)
s <- na.omit(df[[cible]])
niveau <- all(s > 0) && acf(s, plot = FALSE)$acf[2] > 0.95
ret <- if (niveau) 100 * diff(log(s)) else (if (sd(s) < .1) s * 100 else s - mean(s))
cat("Rendements :", if (niveau) "logarithmiques (%)" else "série utilisée telle quelle", "\\n"); print(summary(ret))
spec <- ugarchspec(variance.model = list(model = "{model}", garchOrder = c({order})), mean.model = list(armaOrder = c(0, 0)), distribution.model = "std")
n <- length(ret); b <- floor(n * .85)
fit <- ugarchfit(spec, ret, out.sample = n - b)                         # estimé apprentissage + validation, test en dehors de l'échantillon
print(fit)
fc <- ugarchforecast(fit, n.ahead = {cfg.get('forecast_steps', 12)}); print(sigma(fc))
{risk_r}
'''
    if m == 'logit':
        return '''library(pROC)
fit <- glm(formule, family = binomial, data = train); print(summary(fit)); print(exp(coef(fit)))     # odds ratios
pv <- predict(fit, valid, type = "response")
ths <- seq(.05, .95, .05); f1 <- sapply(ths, function(t) { p <- pv >= t; tp <- sum(p & valid[[cible]] == levels(df[[cible]])[2]); 2*tp / (sum(p) + sum(valid[[cible]] == levels(df[[cible]])[2])) })
seuil <- ths[which.max(f1)]
pt <- predict(fit, test, type = "response"); r <- roc(test[[cible]], pt); print(auc(r)); plot(r, main = "Courbe ROC (test)")
print(table(Predit = pt >= seuil, Reel = test[[cible]]))
'''
    if m == 'mlogit':
        return '''library(nnet); fit <- multinom(formule, data = rbind(train, valid), trace = FALSE); print(summary(fit))
print(table(Predit = predict(fit, test), Reel = test[[cible]]))
'''
    if m in ML_REG + ML_CLF:
        meth = {'rf_reg': 'rf', 'rf_clf': 'rf', 'gb_reg': 'gbm', 'gb_clf': 'gbm', 'svr': 'svmRadial', 'svm_clf': 'svmRadial', 'knn_reg': 'knn', 'knn_clf': 'knn',
                'tree_reg': 'rpart', 'tree_clf': 'rpart', 'mlp_reg': 'nnet', 'mlp_clf': 'nnet', 'nb_clf': 'nb'}[m]
        clf = m in ML_CLF
        extra = ', trace = FALSE, linout = TRUE' if m == 'mlp_reg' else (', trace = FALSE' if m == 'mlp_clf' else (', verbose = FALSE' if meth == 'gbm' else ''))
        ctrl = f'trainControl(method = "cv", number = 5{", classProbs = TRUE, summaryFunction = twoClassSummary" if clf and cfg.get("kind") == "binary" else ""})'
        metric = ', metric = "ROC"' if clf and cfg.get('kind') == 'binary' else ''
        ev = ('''pt <- predict(mod, test); print(confusionMatrix(pt, test[[cible]]))
if (nlevels(df[[cible]]) == 2) { library(pROC); pr <- predict(mod, test, type = "prob")[, 2]; r <- roc(test[[cible]], pr); print(auc(r)); plot(r, main = "Courbe ROC (test)") }'''
              if clf else '''pt <- predict(mod, test); cat("R2 test :", cor(test[[cible]], pt)^2, "| RMSE :", rmse(test[[cible]], pt), "\\n"); plot(test[[cible]], pt, xlab = "Observé", ylab = "Prédit")''')
        val_r = 'print(mean(pv == valid[[cible]]))' if clf else 'cat("RMSE validation :", rmse(valid[[cible]], pv), "\\n")'
        levels_fix = 'levels(train[[cible]]) <- make.names(levels(train[[cible]])); levels(valid[[cible]]) <- levels(train[[cible]]); levels(test[[cible]]) <- levels(train[[cible]])\n' if clf and cfg.get('kind') == 'binary' else ''
        return f'''library(caret)
{levels_fix}ctrl <- {ctrl}
mod <- train(formule, data = train, method = "{meth}", trControl = ctrl, tuneLength = 5, preProcess = c("center", "scale"){metric}{extra})   # hyperparamètres optimisés par validation croisée sur l'apprentissage
print(mod); plot(mod)
cat("Validation :\\n"); pv <- predict(mod, valid); {val_r}
{ev}
'''
    return '# modèle non pris en charge\n'


# =====================================================================================================
# STATA
# =====================================================================================================
def make_stata(cfg):
    T, E = cfg.get('time_col'), cfg.get('entity_col')
    feats = cfg['features']
    tgt = cfg['target']
    fv = ' '.join(feats)
    ids = cfg['models']
    clf = cfg.get('kind') in ('binary', 'multiclass')
    out = [f'''* Analyse reproductible générée par DataEcon.Ci le {datetime.now().strftime('%d/%m/%Y')}
* Jeu de données : {cfg.get('dataset_name', '')}
* Variable cible : {tgt} | Explicatives : {fv or '(aucune)'}
* Modèles : {', '.join(_name(m) for m in ids)}
* NB : les variables qualitatives doivent être écrites i.nom_variable (indicatrices automatiques).

clear all
set more off
set seed 42

* ---- 1. Chargement
{'import delimited "%s", clear varnames(1) encoding(utf8)' % cfg.get('file', 'donnees.csv') if _is_csv(cfg) else 'import excel "%s", firstrow clear' % cfg.get('file', 'donnees.xlsx')}
describe

* ---- 2. Préparation : valeurs manquantes, encodage, standardisation
misstable summarize {tgt} {fv}
drop if missing({tgt})                              // la cible n'est jamais imputée''']
    for f in feats:
        out.append(f'''capture confirm numeric variable {f}
if _rc == 0 {{
    quietly summarize {f}, detail
    local sk = r(skewness)
    {'' if cfg.get('structure') != 'time_series' else 'ipolate ' + f + ' ' + (T or 'n') + ', gen(' + f + '_i)' + chr(10) + '    replace ' + f + ' = ' + f + '_i if missing(' + f + ')' + chr(10) + '    drop ' + f + '_i'}
    replace {f} = cond(abs(`sk') > 1, r(p50), r(mean)) if missing({f})   // médiane si asymétrique, sinon moyenne
}}
else {{
    quietly count if missing({f})
    replace {f} = "Manquant" if missing({f})
}}''')
    if T and cfg.get('structure') in ('time_series', 'panel'):
        out.append(f'\n* ordre chronologique\n{"sort " + E + " " + T if E else "sort " + T}')
    out.append(f'''
* Standardisation (utile pour les modèles pénalisés / distances) : variables z_*
foreach v of varlist {' '.join(f for f in feats)} {{
    capture confirm numeric variable `v'
    if _rc == 0 egen z_`v' = std(`v')
}}

* ---- 3. Statistiques descriptives et graphiques
summarize {tgt} {fv}, detail
correlate {tgt} {fv}
histogram {tgt}, normal
graph box {tgt}
{'qnorm ' + tgt if cfg.get('kind') == 'continuous' else ''}
{'twoway (scatter ' + tgt + ' ' + feats[0] + ') (lfit ' + tgt + ' ' + feats[0] + ')' if feats else ''}
''')
    split = cfg.get('structure') != 'panel' or any(m in ML_REG + ML_CLF + ('logit',) for m in ids)
    if split:
        out.append('''* ---- 4. Partition train / validation / test (60 / 20 / 20)
splitsample, generate(echantillon) split(.6 .2 .2) rseed(42)       // 1 = apprentissage, 2 = validation, 3 = test
''')
    for m in ids:
        out.append(f'* ---- Modèle : {_name(m)}\n' + _stata_model(m, cfg))
    return '\n'.join(out) + '\n'


def _stata_model(m, cfg):
    T, E = cfg.get('time_col'), cfg.get('entity_col')
    tgt = cfg['target']
    fv = ' '.join(cfg['features'])
    steps = cfg.get('forecast_steps', 12)
    if m == 'ols':
        return f'''regress {tgt} {fv} if echantillon != 3
regress {tgt} {fv} if echantillon != 3, vce(robust)         // erreurs robustes
estat hettest
estat ovtest
predict yhat if echantillon == 3
gen e2 = ({tgt} - yhat)^2 if echantillon == 3
quietly summarize e2
display "RMSE test = " sqrt(r(mean))
drop yhat e2
'''
    if m in ('ridge', 'lasso', 'elasticnet'):
        cmd = {'ridge': 'elasticnet linear', 'lasso': 'lasso linear', 'elasticnet': 'elasticnet linear'}[m]
        al = ', alpha(0) rseed(42)' if m == 'ridge' else (', rseed(42)' if m == 'lasso' else ', alpha(.2 .5 .8) rseed(42)')
        return f'''{cmd} {tgt} {fv} if echantillon != 3{al}
lassocoef
'''
    if m == 'poisson':
        return f'poisson {tgt} {fv}, vce(robust)\nestat gof\n'
    if m == 'negbin':
        return f'nbreg {tgt} {fv}\n'
    if m.startswith('panel_'):
        cmd = {'panel_pooled': 'regress ' + tgt + ' ' + fv + ', vce(cluster ' + (E or 'id') + ')', 'panel_fe': 'xtreg ' + tgt + ' ' + fv + ', fe vce(cluster ' + (E or 'id') + ')', 'panel_re': 'xtreg ' + tgt + ' ' + fv + ', re vce(cluster ' + (E or 'id') + ')'}[m]
        return f'''encode {E}, gen(unite_id)
xtset unite_id {T}
{cmd}
{'quietly xtreg ' + tgt + ' ' + fv + ', fe' + chr(10) + 'estimates store fe' + chr(10) + 'quietly xtreg ' + tgt + ' ' + fv + ', re' + chr(10) + 'estimates store re' + chr(10) + 'hausman fe re' if m != 'panel_pooled' else ''}
'''
    if m in TS_IDS:
        order = {'ar': '(2,0,0)', 'ma': '(0,0,2)', 'arma': '(1,0,1)', 'arima': '(1,1,1)', 'sarima': '(1,1,1)', 'arimax': '(1,1,1)'}[m]
        seas = ' sarima(0,1,1,12)' if m == 'sarima' else ''
        exo = f' {fv}' if m == 'arimax' else ''
        return f'''tsset {T or 'obs'}                                     // déclarez la dimension temporelle
dfuller {tgt}
arima {tgt}{exo} if echantillon != 3, arima{order}{seas}   // ordres à ajuster selon ACF/PACF et critères AIC (estat ic)
estat ic
predict yfc, dynamic(.)
tsappend, add({steps})
'''
    if m == 'holtwinters':
        return f'tssmooth shwinters hw = {tgt}, forecast({steps})\n'
    if m == 'var':
        return f'tsset {T or "obs"}\nvarsoc {tgt} {fv}\nvar {tgt} {fv}, lags(1/2)\nvarstable\nfcast compute f_, step({steps})\n'
    if m in ('garch', 'arch', 'egarch', 'gjr', 'risk'):
        cmd = {'garch': 'arch ret, arch(1) garch(1) distribution(t)', 'arch': 'arch ret, arch(1/3) distribution(t)', 'egarch': 'arch ret, earch(1) egarch(1) distribution(t)',
               'gjr': 'arch ret, arch(1) tarch(1) garch(1) distribution(t)', 'risk': 'arch ret, arch(1) garch(1) distribution(t)'}[m]
        extra = '''_pctile ret, p(5 1)
display "VaR 95 % = " -r(r1)/100 "   VaR 99 % = " -r(r2)/100
''' if m == 'risk' else ''
        return f'''tsset {T or "obs"}
* Rendements logarithmiques en % (série de niveaux : prix, indice) ; si la série est déjà un rendement : gen ret = {tgt}
gen ret = 100 * (ln({tgt}) - ln(L.{tgt}))
summarize ret, detail
{cmd}
predict sigma2, variance
{extra}'''
    if m == 'logit':
        return f'''logit {tgt} {fv} if echantillon == 1
estat classification
lroc if echantillon == 1                    // courbe ROC (apprentissage)
predict p_te if echantillon == 3
roctab {tgt} p_te if echantillon == 3       // AUC sur le test
'''
    if m == 'mlogit':
        return f'mlogit {tgt} {fv} if echantillon != 3, baseoutcome(1)\npredict p1 p2 p3 if echantillon == 3\n'
    if m in ML_REG + ML_CLF:
        if m in ('rf_reg', 'rf_clf'):
            typ = 'class' if m == 'rf_clf' else 'reg'
            return f'''* Forêt aléatoire (commande communautaire) : ssc install rforest
rforest {tgt} {fv} if echantillon == 1, type({ 'class' if typ == 'class' else 'reg'}) iterations(300) numvars(`=wordcount("{fv}")'/3)
predict yhat_rf if echantillon == 3
'''
        return f'''* {_name(m)} : pas de commande native dans Stata.
* Utilisez le script Python ou R de cette analyse (optimisation des hyperparamètres, courbes ROC, etc.).
'''
    if m == 'mlp_ts':
        return '* Réseau de neurones autorégressif : non disponible dans Stata, utilisez le script Python ou R.\n'
    return ''


# =====================================================================================================
# SQL (PostgreSQL)
# =====================================================================================================
def _ident(c):
    return '"' + str(c).replace('"', '""') + '"'


def make_sql(cfg):
    T, E = cfg.get('time_col'), cfg.get('entity_col')
    tgt = cfg['target']
    cats = set(cfg.get('cat_features') or [])
    cat_feats = [f for f in cfg['features'] if f in cats]
    feats = [f for f in cfg['features'] if f not in cats]       # le SQL traite les variables numériques ; les qualitatives ont des tableaux de fréquences
    t = _ident(tgt)
    ids = cfg['models']
    out = [f'''-- Analyse reproductible générée par DataEcon.Ci le {datetime.now().strftime('%d/%m/%Y')}  (PostgreSQL)
-- Jeu de données : {cfg.get('dataset_name', '')}
-- Variable cible : {tgt} | Explicatives : {', '.join(feats) or '(aucune)'}
--
-- Le SQL permet la préparation, les statistiques descriptives, la corrélation, les régressions simples,
-- les rendements et les agrégats de panel. Les modèles de machine learning, de deep learning et de classification
-- avancée ne s'expriment pas en SQL : utilisez les scripts Python ou R pour ceux-ci.

-- ===== 1. Table source (chargez le fichier avec COPY ou l'import de votre outil) =====
-- CREATE TABLE donnees (...);
-- \\copy donnees FROM '{cfg.get('file', 'donnees.csv')}' CSV HEADER

-- ===== 2. Valeurs manquantes =====
SELECT COUNT(*) AS n,''']
    cols = [tgt] + feats + cat_feats
    out.append('\n'.join(f'       COUNT(*) - COUNT({_ident(c)}) AS manquantes_{i}{"," if i < len(cols) - 1 else ""}  -- {c}' for i, c in enumerate(cols)))
    out.append('FROM donnees;\n')
    # vue préparée
    sel, num_feats = [], feats
    out.append('-- ===== 3. Vue préparée : imputation (médiane), standardisation =====')
    out.append('-- Hypothèse : les variables explicatives listées sont numériques ; pour une variable qualitative, voir l\'encodage plus bas.')
    out.append('CREATE OR REPLACE VIEW donnees_prep AS')
    out.append(f'WITH base AS (SELECT * FROM donnees WHERE {t} IS NOT NULL),  -- la cible n\'est jamais imputée')
    meds = ',\n'.join(f'  med_{i} AS (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY {_ident(f)}) AS m FROM base)' for i, f in enumerate(feats))
    if feats:
        out.append(meds + ',')
    out.append('imput AS (SELECT b.*' + ''.join(f',\n  COALESCE(b.{_ident(f)}, (SELECT m FROM med_{i})) AS {_ident(f + "_imp")}' for i, f in enumerate(feats)) + ' FROM base b)')
    out.append('SELECT i.*' + ''.join(f',\n  ({_ident(f + "_imp")} - AVG({_ident(f + "_imp")}) OVER ()) / NULLIF(STDDEV_SAMP({_ident(f + "_imp")}) OVER (), 0) AS {_ident("z_" + f)}' for f in feats) + '\nFROM imput i;\n')
    # descriptives
    out.append('-- ===== 4. Statistiques descriptives =====')
    for c in [tgt] + feats:
        ci = _ident(c)
        out.append(f'''SELECT '{c}' AS variable, COUNT({ci}) AS n, AVG({ci}) AS moyenne, STDDEV_SAMP({ci}) AS ecart_type, MIN({ci}) AS minimum,
       percentile_cont(0.25) WITHIN GROUP (ORDER BY {ci}) AS q1, percentile_cont(0.5) WITHIN GROUP (ORDER BY {ci}) AS mediane,
       percentile_cont(0.75) WITHIN GROUP (ORDER BY {ci}) AS q3, MAX({ci}) AS maximum
FROM donnees;''')
    for c in cat_feats:
        ci = _ident(c)
        out.append(f'-- Fréquences de la variable qualitative {c}\nSELECT {ci} AS modalite, COUNT(*) AS effectif, ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pourcentage FROM donnees GROUP BY {ci} ORDER BY effectif DESC;')
    if feats:
        out.append('\n-- Corrélations avec la cible')
        out.append('SELECT ' + '\n       '.join(f"CORR({t}, {_ident(f)}) AS corr_{i}{',' if i < len(feats) - 1 else ''}  -- {f}" for i, f in enumerate(feats)) + '\nFROM donnees;')
    out.append('''
-- Partition train / validation / test (60 / 20 / 20), reproductible par hachage
CREATE OR REPLACE VIEW donnees_split AS
SELECT *, CASE WHEN h < 0.6 THEN 'train' WHEN h < 0.8 THEN 'validation' ELSE 'test' END AS echantillon
FROM (SELECT p.*, (ABS(hashtext(p::text)) % 1000) / 1000.0 AS h FROM donnees_prep p) s;
''')
    for m in ids:
        out.append(f'-- ===== Modèle : {_name(m)} =====\n' + _sql_model(m, cfg))
    return '\n'.join(out) + '\n'


def _sql_model(m, cfg):
    T, E = cfg.get('time_col'), cfg.get('entity_col')
    tgt = cfg['target']
    t = _ident(tgt)
    feats = [f for f in cfg['features'] if f not in set(cfg.get('cat_features') or [])]
    if m in ('ols', 'ridge', 'lasso', 'elasticnet'):
        rows = '\nUNION ALL\n'.join(f"SELECT '{f}' AS variable, REGR_SLOPE({t}, {_ident(f)}) AS pente, REGR_INTERCEPT({t}, {_ident(f)}) AS constante, REGR_R2({t}, {_ident(f)}) AS r2, CORR({t}, {_ident(f)}) AS corr FROM donnees" for f in feats)
        return ('-- Régression linéaire simple pour chaque variable explicative (la régression multiple s\'estime avec les scripts Python, R ou Stata).\n' + (rows + ';\n' if rows else '-- aucune variable explicative\n'))
    if m in ('poisson', 'negbin', 'logit', 'mlogit') or m in ML_REG + ML_CLF or m in ('mlp_reg', 'mlp_clf', 'mlp_ts'):
        extra = ''
        if m in ('logit', 'mlogit') or m.endswith('_clf'):
            extra = '\n'.join(f"-- Profil moyen de {f} selon les classes de la cible\nSELECT {t} AS classe, COUNT(*) AS n, AVG({_ident(f)}) AS moyenne FROM donnees GROUP BY {t} ORDER BY {t};" for f in feats[:3])
        return ('-- Ce modèle ne peut pas être estimé en SQL : utilisez les scripts Python ou R. La vue donnees_split ci-dessus fournit la partition train / validation / test.\n' + extra + '\n')
    if m.startswith('panel_'):
        f = feats[0] if feats else None
        if not (E and T and f):
            return '-- colonnes unité / temps absentes\n'
        fi = _ident(f)
        return f'''-- Estimateur à effets fixes (within) pour {f} : régression sur les données centrées par unité
WITH centre AS (
  SELECT {t} - AVG({t}) OVER (PARTITION BY {_ident(E)}) AS y_c, {fi} - AVG({fi}) OVER (PARTITION BY {_ident(E)}) AS x_c
  FROM donnees WHERE {t} IS NOT NULL AND {fi} IS NOT NULL)
SELECT REGR_SLOPE(y_c, x_c) AS coef_effets_fixes, REGR_R2(y_c, x_c) AS r2_within FROM centre;

-- Moyennes par unité (hétérogénéité entre unités)
SELECT {_ident(E)} AS unite, COUNT(*) AS n, AVG({t}) AS moyenne, STDDEV_SAMP({t}) AS ecart_type FROM donnees GROUP BY {_ident(E)} ORDER BY moyenne DESC;
'''
    if m in TS_IDS or m in ('holtwinters', 'var'):
        if not T:
            return '-- colonne temporelle absente\n'
        ti = _ident(T)
        return f'''-- Dynamique de la série : retards, variations, moyennes mobiles et autocorrélation d'ordre 1
WITH s AS (
  SELECT {ti} AS t, {t} AS y, LAG({t}) OVER (ORDER BY {ti}) AS y_1, LAG({t}, 12) OVER (ORDER BY {ti}) AS y_12,
         AVG({t}) OVER (ORDER BY {ti} ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS moy_mobile_12
  FROM donnees WHERE {t} IS NOT NULL)
SELECT t, y, y - y_1 AS variation, moy_mobile_12 FROM s ORDER BY t;

SELECT CORR(y, y_1) AS autocorr_1, CORR(y, y_12) AS autocorr_12 FROM (
  SELECT {t} AS y, LAG({t}) OVER (ORDER BY {ti}) AS y_1, LAG({t}, 12) OVER (ORDER BY {ti}) AS y_12 FROM donnees) q;
-- L'estimation ARIMA / SARIMA / Holt-Winters / VAR se fait avec les scripts Python, R ou Stata.
'''
    if m in ('garch', 'arch', 'egarch', 'gjr', 'risk'):
        if not T:
            return '-- colonne temporelle absente\n'
        ti = _ident(T)
        return f'''-- Rendements logarithmiques en % (série de niveaux : prix, indice) et volatilité glissante
CREATE OR REPLACE VIEW rendements AS
SELECT {ti} AS t, {t} AS niveau,
       100 * LN({t} / NULLIF(LAG({t}) OVER (ORDER BY {ti}), 0)) AS rendement
FROM donnees WHERE {t} > 0;

SELECT COUNT(rendement) AS n, AVG(rendement) AS moyenne, STDDEV_SAMP(rendement) AS volatilite,
       percentile_cont(0.05) WITHIN GROUP (ORDER BY rendement) AS var_95_hist, percentile_cont(0.01) WITHIN GROUP (ORDER BY rendement) AS var_99_hist
FROM rendements;

SELECT t, rendement, STDDEV_SAMP(rendement) OVER (ORDER BY t ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS volatilite_20
FROM rendements ORDER BY t;
-- Les modèles ARCH / GARCH / EGARCH / GJR s'estiment avec les scripts Python, R ou Stata.
'''
    return '-- modèle non pris en charge\n'


BUILDERS = {
    'python': (make_python, 'text/x-python', 'py'),
    'notebook': (make_notebook, 'application/x-ipynb+json', 'ipynb'),
    'r': (make_r, 'text/plain', 'R'),
    'stata': (make_stata, 'text/plain', 'do'),
    'sql': (make_sql, 'application/sql', 'sql'),
}
