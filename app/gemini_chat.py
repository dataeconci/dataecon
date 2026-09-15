#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module Chatbot avec Google Gemini - IA générative
"""

import os

# Lien WhatsApp admin
WHATSAPP_ADMIN = "https://wa.me/qr/NIDJGSRVJTJTM1"

# Configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Contexte système pour l'IA
SYSTEM_CONTEXT = """Tu es EconBot, l'assistant intelligent de DataEcon.Ci, une plateforme ivoirienne de formation en économétrie et science des données.

## Ta mission
Aider les utilisateurs avec bienveillance, précision et professionnalisme sur toutes les questions liées à DataEcon.Ci.

## Informations sur DataEcon.Ci
- **Nom** : DataEcon.Ci
- **Activité** : Plateforme de formation en économétrie et data science
- **Pays** : Côte d'Ivoire
- **Langue** : Français principalement

## Fonctionnalités du site
1. **Cours en 3 niveaux** :
   - Débutant (GRATUIT) : Introduction à l'économétrie
   - Intermédiaire (Premium) : Régression multiple, tests statistiques
   - Avancé (Premium Pro) : Séries temporelles, panel, machine learning

2. **Abonnements** :
   - Gratuit : 0 FCFA - Accès aux cours Débutant
   - Premium : 2 000 FCFA/mois - Tous les cours
   - Premium Pro : 5 000 FCFA/mois - Cours + Données + Modèles

3. **Paiement** : Via Wave Mobile Money sur la page /subscription

4. **Modèles économétriques** : Régression, Séries temporelles, Machine Learning, Deep Learning (Premium Pro)

5. **Données** : Import CSV/Excel/Stata, visualisation (Premium Pro)

6. **Rapports** : Génération de rapports Word et LaTeX après analyse

## Comment utiliser DataEcon.Ci
- **Inscription** : Cliquer sur "Inscription" en haut à droite, remplir le formulaire, confirmer l'email
- **Connexion** : Utiliser nom d'utilisateur + mot de passe
- **Mot de passe oublié** : Cliquer sur "Mot de passe oublié ?", recevoir un code à 5 chiffres par email, saisir le code, définir un nouveau mot de passe
- **Cours** : Page /courses
- **Modèles** : Page /models (Premium Pro)
- **Données** : Page /datasets (Premium Pro)
- **Abonnement** : Page /subscription

## Règles de réponse
1. Réponds toujours en français, de manière amicale et professionnelle
2. Sois concis : entre 2 et 5 phrases pour les questions simples
3. Utilise des emojis avec parcimonie pour rendre la conversation plus chaleureuse
4. Si la question concerne DataEcon.Ci, réponds précisément avec les infos ci-dessus
5. Si tu ne sais pas ou si la question nécessite une intervention humaine (problème de compte spécifique, paiement non reçu, bug technique grave), termine ta réponse par : [WHATSAPP_NEEDED]
6. Ne donne jamais d'informations sensibles (mots de passe, données personnelles)
7. Redirige vers les pages du site en utilisant leur URL (ex: "/subscription" pour l'abonnement)
8. Si la question est hors sujet (politique, religion, sujets sensibles), recentre poliment vers les services de DataEcon.Ci

Réponds toujours de manière utile et chaleureuse !
"""


def chat_with_gemini(user_message, conversation_history=None):
    """
    Envoyer un message à Gemini et récupérer la réponse
    
    Args:
        user_message: Le message de l'utilisateur
        conversation_history: Historique (optionnel)
    
    Returns:
        tuple (response_text, needs_whatsapp)
    """
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY non configurée", flush=True)
        return "Je suis temporairement indisponible. Contactez l'administrateur sur WhatsApp pour une assistance immédiate.", True
    
    try:
        import google.generativeai as genai
        
        # Configurer Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Créer le modèle avec le contexte système
        model = genai.GenerativeModel(
            model_name='gemini-3.5-flash-lite',
            system_instruction=SYSTEM_CONTEXT
        )
        
        # Envoyer le message
        response = model.generate_content(user_message)
        
        if not response or not response.text:
            return "Je n'ai pas pu générer de réponse. Réessayez ou contactez l'admin.", True
        
        response_text = response.text.strip()
        
        # Vérifier si WhatsApp est nécessaire
        needs_whatsapp = '[WHATSAPP_NEEDED]' in response_text
        response_text = response_text.replace('[WHATSAPP_NEEDED]', '').strip()
        
        return response_text, needs_whatsapp
    
    except Exception as e:
        print(f"Erreur Gemini: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return "Je rencontre une difficulté technique. Contactez l'administrateur sur WhatsApp pour une aide immédiate.", True


def get_whatsapp_link():
    """Retourner le lien WhatsApp de l'admin"""
    return WHATSAPP_ADMIN