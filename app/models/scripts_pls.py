# -*- coding: utf-8 -*-
"""Scripts reproductibles d'un modèle PLS-SEM : R (seminr) et Python (plspm)."""
import re
import unicodedata
from datetime import datetime


def _safe(name):
    t = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    t = re.sub(r'[^A-Za-z0-9]+', '_', t).strip('_')
    return t or 'construit'


def _names(cfg):
    spec = cfg['pls']
    m = {}
    used = set()
    for c in spec['constructs']:
        s = _safe(c['name'])
        base, i = s, 2
        while s in used:
            s = f'{base}_{i}'; i += 1
        used.add(s)
        m[c['name']] = s
    return spec, m


def make_pls_r(cfg):
    spec, nm = _names(cfg)
    f = cfg.get('file') or 'donnees.csv'
    scheme = {'path': 'path_weighting', 'factorial': 'path_factorial', 'centroid': 'centroid_weighting'}.get(cfg.get('scheme', 'path'), 'path_weighting')
    L = [f'# Modèle PLS-SEM : {cfg.get("dataset_name", "")}', f'# Généré par DataEcon.ci le {datetime.now().strftime("%d/%m/%Y")}', '',
         'if (!require("seminr")) install.packages("seminr")', 'library(seminr)', '',
         f'donnees <- read.csv("{f}", stringsAsFactors = FALSE)', '', '# Modèle de mesure',
         'modele_mesure <- constructs(']
    cs = []
    for c in spec['constructs']:
        items = ', '.join(f'"{i}"' for i in c['indicators'])
        w = 'mode_B' if (str(c.get('mode', 'A')).upper() == 'B' and len(c['indicators']) > 1) else 'mode_A'
        cs.append(f'  composite("{nm[c["name"]]}", c({items}), weights = {w})')
    L.append(',\n'.join(cs))
    L += [')', '', '# Modèle structurel']
    byfrom = {}
    for a, b in spec['paths']:
        byfrom.setdefault(a, []).append(b)
    ps = []
    for a, bs in byfrom.items():
        tos = ', '.join(f'"{nm[b]}"' for b in bs)
        ps.append(f'  paths(from = "{nm[a]}", to = c({tos}))')
    L += ['modele_structurel <- relationships(', ',\n'.join(ps), ')', '',
          'pls <- estimate_pls(data = donnees, measurement_model = modele_mesure, structural_model = modele_structurel,',
          f'                    inner_weights = {scheme})', 'resume <- summary(pls)', '',
          '# Résultats principaux', 'print(resume$loadings)', 'print(resume$reliability)', 'print(resume$validity$htmt)',
          'print(resume$vif_antecedents)', 'print(resume$paths)', '',
          f'# Bootstrapping ({cfg.get("n_boot", 1000)} échantillons)',
          f'boot <- bootstrap_model(seminr_model = pls, nboot = {cfg.get("n_boot", 1000)}, cores = 1, seed = 123)',
          'resume_boot <- summary(boot)', 'print(resume_boot$bootstrapped_paths)', 'print(resume_boot$bootstrapped_loadings)',
          'print(resume_boot$total_indirect_effects)', '', 'plot(boot, title = "Modèle structurel")', '']
    return '\n'.join(L)


def make_pls_python(cfg):
    spec, nm = _names(cfg)
    f = cfg.get('file') or 'donnees.csv'
    scheme = {'path': 'Scheme.PATH', 'factorial': 'Scheme.FACTORIAL', 'centroid': 'Scheme.CENTROID'}.get(cfg.get('scheme', 'path'), 'Scheme.PATH')
    L = ['# -*- coding: utf-8 -*-', f'# Modèle PLS-SEM : {cfg.get("dataset_name", "")}', f'# Généré par DataEcon.ci le {datetime.now().strftime("%d/%m/%Y")}',
         '# Installation : pip install plspm pandas', '',
         'import pandas as pd', 'import plspm.config as c', 'from plspm.plspm import Plspm', 'from plspm.scheme import Scheme', 'from plspm.mode import Mode', '',
         f'donnees = pd.read_csv("{f}")', '', '# Modèle structurel', 'structure = c.Structure()']
    byfrom = {}
    for a, b in spec['paths']:
        byfrom.setdefault(a, []).append(b)
    for a, bs in byfrom.items():
        L.append(f'structure.add_path(["{nm[a]}"], [{", ".join(chr(34) + nm[b] + chr(34) for b in bs)}])')
    L += ['', '# Modèle de mesure', 'config = c.Config(structure.path(), scaled=True)']
    for c_ in spec['constructs']:
        mode = 'Mode.B' if (str(c_.get('mode', 'A')).upper() == 'B' and len(c_['indicators']) > 1) else 'Mode.A'
        L.append(f'config.add_lv("{nm[c_["name"]]}", {mode}, ' + ', '.join(f'c.MV("{i}")' for i in c_['indicators']) + ')')
    L += ['', f'modele = Plspm(donnees, config, {scheme}, 300, 1e-7, bootstrap=True, bootstrap_iterations={cfg.get("n_boot", 1000)})', '',
          'print("Coefficients de chemin"); print(modele.path_coefficients())',
          'print("Résumé du modèle interne (R², etc.)"); print(modele.inner_summary())',
          'print("Modèle externe (poids, loadings)"); print(modele.outer_model())',
          'print("Effets"); print(modele.effects())',
          'print("Bootstrap des chemins"); print(modele.bootstrap().paths())', '']
    return '\n'.join(L)


PLS_BUILDERS = {'r': (make_pls_r, 'text/plain', 'R'), 'python': (make_pls_python, 'text/x-python', 'py')}
