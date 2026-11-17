# -*- coding: utf-8 -*-
"""Catalogue WDI (World Development Indicators, Banque mondiale) : indicateurs, pays et extraction en panel."""
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

API = 'https://api.worldbank.org/v2'
TIMEOUT = 25

# (code WDI, nom de colonne, libellé)
CATALOG = {
    'Croissance et production': [
        ('NY.GDP.MKTP.CD', 'pib_usd', 'PIB (USD courants)'),
        ('NY.GDP.MKTP.KD.ZG', 'croissance_pib', 'Croissance du PIB (% annuel)'),
        ('NY.GDP.PCAP.CD', 'pib_par_hab_usd', 'PIB par habitant (USD courants)'),
        ('NY.GDP.PCAP.KD.ZG', 'croissance_pib_hab', 'Croissance du PIB par habitant (% annuel)'),
        ('NY.GDP.PCAP.PP.CD', 'pib_hab_ppa', 'PIB par habitant, PPA (USD internationaux courants)'),
        ('NV.AGR.TOTL.ZS', 'agriculture_pct_pib', 'Agriculture, valeur ajoutée (% du PIB)'),
        ('NV.IND.TOTL.ZS', 'industrie_pct_pib', 'Industrie, valeur ajoutée (% du PIB)'),
        ('NV.SRV.TOTL.ZS', 'services_pct_pib', 'Services, valeur ajoutée (% du PIB)'),
        ('NE.GDI.TOTL.ZS', 'fbcf_pct_pib', 'Formation brute de capital (% du PIB)'),
    ],
    'Prix, monnaie et finance': [
        ('FP.CPI.TOTL.ZG', 'inflation', 'Inflation, prix à la consommation (% annuel)'),
        ('PA.NUS.FCRF', 'taux_change', 'Taux de change officiel (UML par USD, moyenne annuelle)'),
        ('FR.INR.RINR', 'taux_interet_reel', "Taux d'intérêt réel (%)"),
        ('FS.AST.PRVT.GD.ZS', 'credit_prive_pct_pib', 'Crédit intérieur au secteur privé (% du PIB)'),
        ('FM.LBL.BMNY.GD.ZS', 'monnaie_large_pct_pib', 'Monnaie au sens large (% du PIB)'),
        ('FB.AST.NPER.ZS', 'creances_douteuses', 'Créances douteuses (% des prêts bruts)'),
        ('CM.MKT.LCAP.GD.ZS', 'capitalisation_pct_pib', 'Capitalisation boursière (% du PIB)'),
        ('FX.OWN.TOTL.ZS', 'inclusion_financiere', 'Titulaires de compte (% des 15 ans et plus)'),
    ],
    'Commerce et investissement': [
        ('NE.EXP.GNFS.ZS', 'exportations_pct_pib', 'Exportations (% du PIB)'),
        ('NE.IMP.GNFS.ZS', 'importations_pct_pib', 'Importations (% du PIB)'),
        ('NE.TRD.GNFS.ZS', 'ouverture_commerciale', 'Commerce (% du PIB)'),
        ('BX.KLT.DINV.WD.GD.ZS', 'ide_entrees_pct_pib', 'IDE, entrées nettes (% du PIB)'),
        ('BX.TRF.PWKR.DT.GD.ZS', 'transferts_migrants_pct_pib', 'Transferts de fonds reçus (% du PIB)'),
        ('DT.ODA.ODAT.GN.ZS', 'aide_pct_rnb', 'Aide publique au développement reçue (% du RNB)'),
        ('BN.CAB.XOKA.GD.ZS', 'compte_courant_pct_pib', 'Solde du compte courant (% du PIB)'),
    ],
    'Finances publiques et dette': [
        ('GC.DOD.TOTL.GD.ZS', 'dette_centrale_pct_pib', "Dette de l'administration centrale (% du PIB)"),
        ('DT.DOD.DECT.GN.ZS', 'dette_externe_pct_rnb', 'Dette extérieure (% du RNB)'),
        ('GC.REV.XGRT.GD.ZS', 'recettes_pct_pib', 'Recettes publiques hors dons (% du PIB)'),
        ('GC.TAX.TOTL.GD.ZS', 'recettes_fiscales_pct_pib', 'Recettes fiscales (% du PIB)'),
        ('GC.XPN.TOTL.GD.ZS', 'depenses_pct_pib', 'Dépenses publiques (% du PIB)'),
        ('GC.BAL.CASH.GD.ZS', 'solde_budgetaire_pct_pib', 'Solde budgétaire (% du PIB)'),
        ('FI.RES.TOTL.CD', 'reserves_usd', 'Réserves totales (USD courants)'),
    ],
    'Population et emploi': [
        ('SP.POP.TOTL', 'population', 'Population totale'),
        ('SP.POP.GROW', 'croissance_pop', 'Croissance de la population (% annuel)'),
        ('SP.URB.TOTL.IN.ZS', 'urbanisation', 'Population urbaine (% du total)'),
        ('SP.POP.DPND', 'dependance', 'Rapport de dépendance (% de la population active)'),
        ('SL.UEM.TOTL.ZS', 'chomage', 'Chômage (% de la population active, ILO)'),
        ('SL.TLF.CACT.ZS', 'participation_active', "Taux d'activité (% des 15 ans et plus, ILO)"),
        ('SL.TLF.CACT.FE.ZS', 'participation_femmes', "Taux d'activité des femmes (%)"),
        ('SL.UEM.1524.ZS', 'chomage_jeunes', 'Chômage des jeunes (% de la population active 15-24 ans)'),
        ('SL.AGR.EMPL.ZS', 'emploi_agriculture', "Emploi dans l'agriculture (% de l'emploi total)"),
    ],
    'Pauvreté et inégalités': [
        ('SI.POV.DDAY', 'pauvrete_215', 'Taux de pauvreté à 2,15 USD par jour (% de la population)'),
        ('SI.POV.GINI', 'gini', 'Indice de Gini'),
        ('SI.DST.FRST.20', 'part_revenu_20_plus_pauvres', 'Part du revenu des 20 % les plus pauvres'),
        ('SI.DST.05TH.20', 'part_revenu_20_plus_riches', 'Part du revenu des 20 % les plus riches'),
    ],
    'Éducation': [
        ('SE.ADT.LITR.ZS', 'alphabetisation', "Taux d'alphabétisation des adultes (%)"),
        ('SE.PRM.ENRR', 'scolarisation_primaire', 'Taux de scolarisation brut, primaire (%)'),
        ('SE.SEC.ENRR', 'scolarisation_secondaire', 'Taux de scolarisation brut, secondaire (%)'),
        ('SE.TER.ENRR', 'scolarisation_superieur', 'Taux de scolarisation brut, supérieur (%)'),
        ('SE.XPD.TOTL.GD.ZS', 'depenses_education_pct_pib', "Dépenses d'éducation (% du PIB)"),
    ],
    'Santé': [
        ('SP.DYN.LE00.IN', 'esperance_vie', 'Espérance de vie à la naissance (années)'),
        ('SP.DYN.IMRT.IN', 'mortalite_infantile', 'Mortalité infantile (pour 1 000 naissances)'),
        ('SP.DYN.TFRT.IN', 'fecondite', 'Indice de fécondité (naissances par femme)'),
        ('SH.XPD.CHEX.GD.ZS', 'depenses_sante_pct_pib', 'Dépenses de santé courantes (% du PIB)'),
        ('SH.STA.MMRT', 'mortalite_maternelle', 'Mortalité maternelle (pour 100 000 naissances)'),
    ],
    'Énergie, environnement et infrastructures': [
        ('EG.ELC.ACCS.ZS', 'acces_electricite', "Accès à l'électricité (% de la population)"),
        ('EN.ATM.CO2E.PC', 'co2_par_hab', 'Émissions de CO2 (tonnes par habitant)'),
        ('EG.USE.PCAP.KG.OE', 'energie_par_hab', "Consommation d'énergie (kg équivalent pétrole par habitant)"),
        ('AG.LND.FRST.ZS', 'superficie_forestiere', 'Superficie forestière (% du territoire)'),
        ('AG.LND.AGRI.ZS', 'terres_agricoles', 'Terres agricoles (% du territoire)'),
        ('IT.NET.USER.ZS', 'internet', "Utilisateurs d'Internet (% de la population)"),
        ('IT.CEL.SETS.P2', 'telephonie_mobile', 'Abonnements mobiles (pour 100 habitants)'),
    ],
    'Gouvernance': [
        ('GE.EST', 'efficacite_gouvernement', "Efficacité du gouvernement (estimation WGI)"),
        ('CC.EST', 'controle_corruption', 'Contrôle de la corruption (estimation WGI)'),
        ('RL.EST', 'etat_de_droit', 'État de droit (estimation WGI)'),
        ('PV.EST', 'stabilite_politique', 'Stabilité politique (estimation WGI)'),
    ],
}

UEMOA = ['BEN', 'BFA', 'CIV', 'GNB', 'MLI', 'NER', 'SEN', 'TGO']
CEDEAO = UEMOA + ['CPV', 'GHA', 'GIN', 'LBR', 'NGA', 'SLE', 'GMB']
CEMAC = ['CMR', 'CAF', 'TCD', 'COG', 'GAB', 'GNQ']
GROUPS = {'uemoa': ('UEMOA (8 pays)', UEMOA), 'cedeao': ('CEDEAO', CEDEAO), 'cemac': ('CEMAC (6 pays)', CEMAC)}

COUNTRIES = [
    ('BEN', 'Bénin'), ('BFA', 'Burkina Faso'), ('CIV', "Côte d'Ivoire"), ('GNB', 'Guinée-Bissau'), ('MLI', 'Mali'),
    ('NER', 'Niger'), ('SEN', 'Sénégal'), ('TGO', 'Togo'), ('CPV', 'Cabo Verde'), ('GHA', 'Ghana'), ('GIN', 'Guinée'),
    ('LBR', 'Libéria'), ('NGA', 'Nigeria'), ('SLE', 'Sierra Leone'), ('GMB', 'Gambie'), ('CMR', 'Cameroun'),
    ('CAF', 'Centrafrique'), ('TCD', 'Tchad'), ('COG', 'Congo'), ('COD', 'RD Congo'), ('GAB', 'Gabon'),
    ('GNQ', 'Guinée équatoriale'), ('DZA', 'Algérie'), ('EGY', 'Égypte'), ('MAR', 'Maroc'), ('TUN', 'Tunisie'),
    ('ETH', 'Éthiopie'), ('KEN', 'Kenya'), ('TZA', 'Tanzanie'), ('UGA', 'Ouganda'), ('RWA', 'Rwanda'),
    ('ZAF', 'Afrique du Sud'), ('AGO', 'Angola'), ('MOZ', 'Mozambique'), ('ZMB', 'Zambie'), ('ZWE', 'Zimbabwe'),
    ('MDG', 'Madagascar'), ('MUS', 'Maurice'), ('FRA', 'France'), ('DEU', 'Allemagne'), ('GBR', 'Royaume-Uni'),
    ('USA', 'États-Unis'), ('CHN', 'Chine'), ('IND', 'Inde'), ('JPN', 'Japon'), ('BRA', 'Brésil'),
]

_ALL_IND = {'t': 0, 'data': None}


def slug(txt):
    t = unicodedata.normalize('NFKD', txt).encode('ascii', 'ignore').decode()
    t = re.sub(r'[^A-Za-z0-9]+', '_', t).strip('_').lower()
    return (t or 'indicateur')[:40]


def code_to_col(code):
    for items in CATALOG.values():
        for c, col, _ in items:
            if c == code:
                return col
    return slug(code.replace('.', '_'))


def label_of(code):
    for items in CATALOG.values():
        for c, _, lab in items:
            if c == code:
                return lab
    return code


def _get(url, params):
    last = None
    for _ in range(3):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT, headers={'User-Agent': 'DataEcon.ci'})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            time.sleep(0.8)
    raise RuntimeError(f"API Banque mondiale injoignable : {last}")


def all_indicators():
    """Liste complète des indicateurs WDI (mise en cache 12 h)."""
    if _ALL_IND['data'] and time.time() - _ALL_IND['t'] < 43200:
        return _ALL_IND['data']
    out, page = [], 1
    while True:
        js = _get(f'{API}/sources/2/indicators', {'format': 'json', 'per_page': 1000, 'page': page})
        if not isinstance(js, list) or len(js) < 2 or not js[1]:
            break
        out += [{'id': x['id'], 'name': x.get('name', '')} for x in js[1]]
        if page >= js[0].get('pages', 1):
            break
        page += 1
    _ALL_IND.update(t=time.time(), data=out)
    return out


def search_indicators(q, limit=40):
    q = (q or '').strip().lower()
    if len(q) < 3:
        return []
    try:
        pool = all_indicators()
    except Exception:
        pool = [{'id': c, 'name': lab} for items in CATALOG.values() for c, _, lab in items]
    words = q.split()
    res = [x for x in pool if all(w in (x['name'] + ' ' + x['id']).lower() for w in words)]
    return res[:limit]


def fetch_indicator(code, countries, y0, y1):
    """Retourne un DataFrame (code_pays, pays, annee, valeur) pour un indicateur."""
    cs = ';'.join(countries) if countries else 'all'
    rows, page = [], 1
    while True:
        js = _get(f'{API}/country/{cs}/indicator/{code}',
                  {'format': 'json', 'per_page': 20000, 'page': page, 'date': f'{y0}:{y1}'})
        if not isinstance(js, list) or len(js) < 2:
            msg = js[0].get('message') if isinstance(js, list) and js and isinstance(js[0], dict) else None
            if msg:
                raise ValueError(f"{code} : {msg[0].get('value', 'indicateur introuvable')}")
            break
        meta, data = js[0], js[1] or []
        for d in data:
            if d.get('value') is None:
                continue
            reg = (d.get('country') or {}).get('id', '')
            rows.append((d.get('countryiso3code') or reg, (d.get('country') or {}).get('value'), int(d['date']), d['value']))
        if page >= meta.get('pages', 1):
            break
        page += 1
    return pd.DataFrame(rows, columns=['code_pays', 'pays', 'annee', code])


def build_panel(codes, countries, y0, y1):
    """Panel large : une ligne par pays-année, une colonne par indicateur."""
    codes = list(dict.fromkeys(codes))
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {c: ex.submit(fetch_indicator, c, countries, y0, y1) for c in codes}
        frames, errors = [], []
        for c, f in futs.items():
            try:
                frames.append((c, f.result()))
            except Exception as e:
                errors.append(str(e))
    if not frames:
        raise RuntimeError('; '.join(errors) or 'Aucune donnée reçue.')
    df = None
    for c, f in frames:
        f = f.rename(columns={c: code_to_col(c)})
        df = f if df is None else df.merge(f, on=['code_pays', 'pays', 'annee'], how='outer')
    df = df[df['code_pays'].str.len() == 3] if countries else df
    cols = [code_to_col(c) for c, _ in frames]
    df = df.dropna(subset=cols, how='all').sort_values(['pays', 'annee']).reset_index(drop=True)
    return df, errors
