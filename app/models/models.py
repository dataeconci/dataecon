#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module des modèles économétriques et machine learning
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

class EconometricModels:
    """Classe regroupant tous les modèles économétriques"""
    
    def __init__(self, data):
        self.data = data
        self.results = {}
    
    def time_series_analysis(self, target_col, date_col=None, forecast_steps=12):
        """
        Analyse de séries temporelles
        - ARIMA
        - Prévisions
        - Tests de stationnarité
        """
        results = {
            'type': 'time_series',
            'tests': {},
            'model': {},
            'forecast': {},
            'economic_interpretation': [],
            'financial_interpretation': [],
            'strategic_decisions': []
        }
        
        try:
            # Test de stationnarité (ADF)
            series = self.data[target_col].dropna()
            adf_result = adfuller(series)
            results['tests']['adf'] = {
                'statistic': adf_result[0],
                'pvalue': adf_result[1],
                'critical_values': adf_result[4],
                'stationary': adf_result[1] < 0.05
            }
            
            # ACF et PACF
            fig, axes = plt.subplots(1, 2, figsize=(12, 4))
            plot_acf(series, ax=axes[0])
            plot_pacf(series, ax=axes[1])
            results['acf_pacf_plot'] = fig
            
            # Modèle ARIMA
            try:
                model = ARIMA(series, order=(1, 1, 1))
                fitted_model = model.fit()
                results['model']['arima'] = {
                    'summary': fitted_model.summary().as_text(),
                    'aic': fitted_model.aic,
                    'bic': fitted_model.bic,
                    'params': fitted_model.params.to_dict()
                }
                
                # Prévisions
                forecast = fitted_model.forecast(steps=forecast_steps)
                results['forecast']['values'] = forecast.tolist()
                results['forecast']['steps'] = forecast_steps
                
                # Interprétation économique
                results['economic_interpretation'].append(
                    f"La série {target_col} présente une tendance {'stationnaire' if results['tests']['adf']['stationary'] else 'non stationnaire'}. "
                    f"Le test ADF donne une statistique de {adf_result[0]:.4f} avec une p-value de {adf_result[1]:.4f}."
                )
                results['economic_interpretation'].append(
                    f"Le modèle ARIMA(1,1,1) sélectionné a un AIC de {fitted_model.aic:.2f} et un BIC de {fitted_model.bic:.2f}, "
                    f"indiquant une bonne qualité d'ajustement."
                )
                
                # Interprétation financière
                results['financial_interpretation'].append(
                    f"Les prévisions pour les {forecast_steps} prochaines périodes sont : {[round(x, 2) for x in forecast.tolist()]}."
                )
                results['financial_interpretation'].append(
                    "Ces prévisions peuvent être utilisées pour la planification financière et la gestion des risques."
                )
                
                # Décisions stratégiques
                results['strategic_decisions'].append(
                    "Sur la base de l'analyse de séries temporelles, il est recommandé de :"
                )
                results['strategic_decisions'].append(
                    "• Renforcer la surveillance des indicateurs clés pour anticiper les retournements"
                )
                results['strategic_decisions'].append(
                    "• Ajuster les prévisions en fonction des cycles économiques identifiés"
                )
                
            except Exception as e:
                results['model']['error'] = str(e)
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    def regression_analysis(self, target_col, feature_cols, model_type='linear'):
        """
        Analyse de régression
        - Linéaire
        - Ridge
        - Lasso
        - Random Forest
        - Gradient Boosting
        """
        results = {
            'type': 'regression',
            'models': {},
            'comparison': {},
            'economic_interpretation': [],
            'financial_interpretation': [],
            'strategic_decisions': []
        }
        
        try:
            # Préparation des données
            X = self.data[feature_cols]
            y = self.data[target_col]
            
            # Split train/test
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Standardisation
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            models = {
                'linear': LinearRegression(),
                'ridge': Ridge(alpha=1.0),
                'lasso': Lasso(alpha=1.0),
                'random_forest': RandomForestRegressor(n_estimators=100, random_state=42),
                'gradient_boosting': GradientBoostingRegressor(n_estimators=100, random_state=42)
            }
            
            model_names = {
                'linear': 'Régression Linéaire',
                'ridge': 'Régression Ridge',
                'lasso': 'Régression Lasso',
                'random_forest': 'Random Forest',
                'gradient_boosting': 'Gradient Boosting'
            }
            
            best_model = None
            best_score = -np.inf
            best_name = None
            
            for name, model in models.items():
                if name == model_type or model_type == 'all':
                    model.fit(X_train_scaled, y_train)
                    y_pred = model.predict(X_test_scaled)
                    
                    r2 = r2_score(y_test, y_pred)
                    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                    mae = mean_absolute_error(y_test, y_pred)
                    
                    results['models'][name] = {
                        'r2': r2,
                        'rmse': rmse,
                        'mae': mae,
                        'coefficients': dict(zip(feature_cols, model.coef_)) if hasattr(model, 'coef_') else None,
                        'intercept': model.intercept_ if hasattr(model, 'intercept_') else None
                    }
                    
                    if r2 > best_score:
                        best_score = r2
                        best_model = model
                        best_name = name
            
            # Comparaison des modèles
            results['comparison']['best_model'] = model_names.get(best_name, best_name)
            results['comparison']['best_r2'] = best_score
            
            # Interprétation économique
            if best_model and hasattr(best_model, 'coef_'):
                for col, coef in zip(feature_cols, best_model.coef_):
                    signe = "positif" if coef > 0 else "négatif"
                    results['economic_interpretation'].append(
                        f"La variable {col} a un impact {signe} sur {target_col}, avec un coefficient de {coef:.4f}."
                    )
            
            results['economic_interpretation'].append(
                f"Le meilleur modèle est {model_names.get(best_name, best_name)} avec un R² de {best_score:.4f}."
            )
            
            # Interprétation financière
            results['financial_interpretation'].append(
                f"Le modèle explique {best_score*100:.1f}% de la variance de {target_col}."
            )
            results['financial_interpretation'].append(
                "Ces résultats permettent d'identifier les facteurs clés influençant la variable cible."
            )
            
            # Décisions stratégiques
            results['strategic_decisions'].append(
                "Sur la base de l'analyse de régression, il est recommandé de :"
            )
            results['strategic_decisions'].append(
                "• Concentrer les efforts sur les variables ayant le plus grand impact"
            )
            results['strategic_decisions'].append(
                "• Mettre en place un suivi régulier des indicateurs identifiés"
            )
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    def machine_learning_analysis(self, target_col, feature_cols):
        """
        Analyse de machine learning avancée
        """
        results = self.regression_analysis(target_col, feature_cols, model_type='all')
        results['type'] = 'machine_learning'
        
        # Ajout d'interprétations spécifiques au ML
        results['economic_interpretation'].append(
            "L'utilisation de modèles de machine learning permet de capturer des relations non-linéaires complexes."
        )
        results['financial_interpretation'].append(
            "Ces modèles offrent une meilleure capacité prédictive pour les séries financières volatiles."
        )
        results['strategic_decisions'].append(
            "• Intégrer les prévisions du modèle ML dans le processus de décision"
        )
        results['strategic_decisions'].append(
            "• Mettre à jour régulièrement les modèles avec les nouvelles données"
        )
        
        return results
    
    def deep_learning_analysis(self, target_col, feature_cols):
        """
        Analyse de deep learning
        """
        results = self.machine_learning_analysis(target_col, feature_cols)
        results['type'] = 'deep_learning'
        
        # Ajout d'interprétations spécifiques au DL
        results['economic_interpretation'].append(
            "Les modèles de deep learning sont capables d'apprendre des représentations complexes des données."
        )
        results['financial_interpretation'].append(
            "Ces modèles sont particulièrement adaptés aux données financières à haute fréquence."
        )
        results['strategic_decisions'].append(
            "• Exploiter la puissance du deep learning pour les prévisions à court terme"
        )
        results['strategic_decisions'].append(
            "• Combiner les approches traditionnelles et deep learning pour une robustesse accrue"
        )
        
        return results
    
    def financial_series_analysis(self, target_col, volatility_col=None):
        """
        Analyse spécifique aux séries financières
        """
        results = {
            'type': 'financial_series',
            'returns_analysis': {},
            'volatility_analysis': {},
            'risk_metrics': {},
            'economic_interpretation': [],
            'financial_interpretation': [],
            'strategic_decisions': []
        }
        
        try:
            # Analyse des rendements
            returns = self.data[target_col].pct_change().dropna()
            
            results['returns_analysis']['mean'] = returns.mean()
            results['returns_analysis']['std'] = returns.std()
            results['returns_analysis']['skewness'] = returns.skew()
            results['returns_analysis']['kurtosis'] = returns.kurtosis()
            
            # Métriques de risque
            results['risk_metrics']['sharpe_ratio'] = returns.mean() / returns.std() * np.sqrt(252)
            results['risk_metrics']['var_95'] = returns.quantile(0.05)
            results['risk_metrics']['max_drawdown'] = (returns.cumsum() - returns.cumsum().cummax()).min()
            
            # Interprétation économique
            results['economic_interpretation'].append(
                f"Le rendement moyen de {target_col} est de {returns.mean()*100:.2f}% avec un écart-type de {returns.std()*100:.2f}%."
            )
            results['economic_interpretation'].append(
                f"L'asymétrie (skewness) de {returns.skew():.2f} indique une distribution {'asymétrique à droite' if returns.skew() > 0 else 'asymétrique à gauche'}."
            )
            
            # Interprétation financière
            results['financial_interpretation'].append(
                f"Le ratio de Sharpe est de {results['risk_metrics']['sharpe_ratio']:.2f}, indiquant une {'bonne' if results['risk_metrics']['sharpe_ratio'] > 1 else 'moyenne'} performance ajustée au risque."
            )
            results['financial_interpretation'].append(
                f"La Value at Risk (VaR) à 95% est de {results['risk_metrics']['var_95']*100:.2f}%."
            )
            
            # Décisions stratégiques
            results['strategic_decisions'].append(
                "Sur la base de l'analyse financière, il est recommandé de :"
            )
            results['strategic_decisions'].append(
                f"• Ajuster l'allocation d'actifs en fonction du ratio de Sharpe ({results['risk_metrics']['sharpe_ratio']:.2f})"
            )
            results['strategic_decisions'].append(
                "• Mettre en place des stratégies de couverture pour limiter la VaR"
            )
            
        except Exception as e:
            results['error'] = str(e)
        
        return results