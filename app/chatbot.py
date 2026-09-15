#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module Chatbot pour DataEcon.Ci
Base de connaissances + redirection WhatsApp
"""

import os
import re
from difflib import SequenceMatcher

# Numéro WhatsApp admin (au format international, sans +)
WHATSAPP_ADMIN = "https://wa.me/qr/NIDJGSRVJTJTM1"

# ==================== BASE DE CONNAISSANCES ====================
KNOWLEDGE_BASE = {
    # Salutations
    "salutation": {
        "keywords": ["bonjour", "salut", "bonsoir", "hello", "hi", "coucou", "hey"],
        "response": "Bonjour ! 👋 Je suis **EconBot**, votre assistant DataEcon.Ci. Comment puis-je vous aider aujourd'hui ?"
    },
    "remerciement": {
        "keywords": ["merci", "thanks", "thank you", "super", "parfait"],
        "response": "Avec plaisir ! 😊 N'hésitez pas si vous avez d'autres questions."
    },
    "au_revoir": {
        "keywords": ["au revoir", "bye", "à bientôt", "ciao", "bonne journée"],
        "response": "Au revoir ! Bonne continuation dans votre formation en économétrie. 👋"
    },
    
    # Inscription et connexion
    "inscription": {
        "keywords": ["inscrire", "inscription", "créer un compte", "s'inscrire", "enregistrer", "register"],
        "response": """Pour créer un compte sur DataEcon.Ci :
1. Cliquez sur **"Inscription"** en haut à droite
2. Remplissez le formulaire (nom, email, mot de passe)
3. **Confirmez votre email** en cliquant sur le lien reçu
4. Connectez-vous avec vos identifiants

📌 L'inscription est **gratuite** et donne accès à tous les cours débutants."""
    },
    "connexion": {
        "keywords": ["connexion", "connecter", "login", "se connecter", "identifiant"],
        "response": """Pour vous connecter :
1. Cliquez sur **"Connexion"** en haut à droite
2. Entrez votre nom d'utilisateur et mot de passe
3. Si vous n'avez pas confirmé votre email, vérifiez votre boîte mail

⚠️ Si vous avez oublié votre mot de passe, cliquez sur **"Mot de passe oublié ?"**"""
    },
    "mot_de_passe_oublie": {
        "keywords": ["mot de passe oublié", "réinitialiser", "oublié", "reset", "recuperer"],
        "response": """Pour réinitialiser votre mot de passe :
1. Cliquez sur **"Mot de passe oublié ?"** sur la page de connexion
2. Entrez votre email
3. Vous recevrez un **code à 5 chiffres** par email
4. Saisissez ce code sur la page de vérification
5. Définissez un nouveau mot de passe"""
    },
    
    # Cours
    "cours": {
        "keywords": ["cours", "formation", "apprendre", "économétrie", "leçon"],
        "response": """Nous proposons **3 niveaux** de cours :

🌱 **Débutant** (Gratuit) : Fondamentaux de l'économétrie
📈 **Intermédiaire** (Premium - 2000 FCFA/mois) : Régression multiple, tests
🚀 **Avancé** (Premium Pro - 5000 FCFA/mois) : Séries temporelles, panel

Accédez aux cours ici : **/courses**"""
    },
    "acces_cours": {
        "keywords": ["je vois pas les cours", "cours manquants", "accès aux cours", "niveau premium", "débloquer"],
        "response": """Voici comment débloquer les cours :

🌱 **Cours Débutant** : Gratuit, accessibles dès l'inscription
📈 **Cours Intermédiaire** : Nécessite un abonnement **Premium** (2000 FCFA/mois)
🚀 **Cours Avancé** : Nécessite un abonnement **Premium Pro** (5000 FCFA/mois)

Pour vous abonner, allez sur **/subscription**"""
    },
    "pdf": {
        "keywords": ["pdf", "télécharger", "fichier", "document", "cours pdf"],
        "response": """Les PDF des cours sont accessibles :
- **Lecture en ligne** : depuis la page du cours
- **Téléchargement** : réservé aux membres Premium et Premium Pro

📥 Pour télécharger : cliquez sur "Télécharger le PDF" dans la page du cours."""
    },
    
    # Abonnement
    "abonnement": {
        "keywords": ["abonnement", "premium", "prix", "tarif", "payer", "souscrire", "subscription"],
        "response": """Voici nos formules d'abonnement :

🆓 **Gratuit** (0 FCFA) : Cours Débutant
🌟 **Premium** (2 000 FCFA/mois) : Tous les cours
💎 **Premium Pro** (5 000 FCFA/mois) : Cours + Données + Modèles

📱 Paiement par **Wave Mobile Money**
Pour vous abonner : **/subscription**"""
    },
    "paiement_wave": {
        "keywords": ["wave", "paiement", "mobile money", "payer"],
        "response": """Le paiement se fait via **Wave Mobile Money** :

1. Allez sur **/subscription**
2. Choisissez votre formule
3. Cliquez sur **"Payer avec Wave"** ou scannez le QR Code
4. Confirmez le paiement sur votre téléphone
5. Votre abonnement est activé instantanément ✅"""
    },
    
    # Modèles et analyses
    "modeles": {
        "keywords": ["modèle", "regression", "analyse", "économétrique", "machine learning"],
        "response": """DataEcon.Ci propose plusieurs modèles :

📈 **Séries Temporelles** : ARIMA, prévisions
💰 **Séries Financières** : Rendements, volatilité
📊 **Régression** : Linéaire, Ridge, Lasso
🤖 **Machine Learning** : Random Forest, Gradient Boosting

Accès réservé aux membres **Premium Pro** : **/models**"""
    },
    "donnees": {
        "keywords": ["données", "dataset", "importer", "upload", "fichier csv", "excel"],
        "response": """Pour importer vos données :

1. Allez sur **/datasets**
2. Choisissez un fichier (CSV, Excel, Stata)
3. Donnez-lui un nom et une description
4. Cliquez sur **"Importer"**

📊 Formats supportés : CSV, XLSX, XLS, DTA
🔒 Réservé aux membres Premium Pro et admin."""
    },
    "rapport": {
        "keywords": ["rapport", "word", "latex", "télécharger rapport", "analyse pdf"],
        "response": """Après avoir lancé une analyse, vous pouvez télécharger :

📄 **Rapport Word** (.docx) : 20+ pages avec graphiques
📜 **Fichier LaTeX** (.tex) : pour compilation PDF

Les boutons apparaissent après avoir lancé une analyse sur **/models**."""
    },
    
    # Compte et profil
    "profil": {
        "keywords": ["profil", "modifier", "changer", "photo", "informations"],
        "response": """Pour modifier votre profil :

1. Cliquez sur votre nom en haut à droite
2. Sélectionnez **"Profil"**
3. Modifiez vos informations (nom, prénom, téléphone)
4. Uploadez une photo de profil
5. Cliquez sur **"Enregistrer"**"""
    },
    "supprimer_compte": {
        "keywords": ["supprimer compte", "effacer", "désinscrire"],
        "response": """Pour supprimer votre compte, contactez l'administrateur directement.

💬 Cliquez ici pour contacter l'admin sur WhatsApp"""
    },
    
    # Support technique
    "bug": {
        "keywords": ["bug", "erreur", "problème", "marche pas", "fonctionne pas", "plante"],
        "response": """Désolé pour ce problème ! Pour nous aider à le résoudre, décrivez :

1. La page où le problème se produit
2. Ce que vous essayiez de faire
3. Le message d'erreur exact

💬 Si le problème persiste, contactez l'admin sur WhatsApp"""
    },
    "contact": {
        "keywords": ["contact", "admin", "support", "whatsapp", "aide"],
        "response": """Pour contacter directement l'administrateur :

📱 **WhatsApp** : cliquez sur le bouton ci-dessous

Notre équipe vous répondra dans les plus brefs délais."""
    },
    
    # Fonctionnalités générales
    "fonctionnalites": {
        "keywords": ["fonctionnalités", "que faire", "possibilités", "features"],
        "response": """Sur DataEcon.Ci, vous pouvez :

📚 **Suivre des cours** d'économétrie (3 niveaux)
📊 **Importer vos données** (CSV, Excel, Stata)
🤖 **Lancer des modèles** (régression, ML, séries temporelles)
📄 **Générer des rapports** Word et LaTeX
💡 **Visualiser** vos données avec des graphiques
🎓 **Progresser** dans votre formation"""
    },
}


def find_best_response(user_message):
    """
    Trouver la meilleure réponse à un message utilisateur
    Retourne un tuple (response, confidence, needs_whatsapp)
    """
    if not user_message:
        return None, 0, True
    
    message_lower = user_message.lower().strip()
    
    # Nettoyer le message
    message_lower = re.sub(r'[^\w\s]', ' ', message_lower)
    
    best_match = None
    best_score = 0
    
    for category, data in KNOWLEDGE_BASE.items():
        for keyword in data["keywords"]:
            # Score basé sur la présence du mot-clé
            if keyword in message_lower:
                score = len(keyword) / len(message_lower) * 2
                if score > best_score:
                    best_score = score
                    best_match = data["response"]
            else:
                # Score basé sur la similarité
                similarity = SequenceMatcher(None, keyword, message_lower).ratio()
                if similarity > best_score and similarity > 0.4:
                    best_score = similarity
                    best_match = data["response"]
    
    # Si on a trouvé une réponse avec une bonne confiance
    if best_match and best_score > 0.15:
        return best_match, best_score, False
    
    # Sinon, réponse par défaut avec WhatsApp
    default_response = """Je ne suis pas certain de comprendre votre question. 🤔

Voici ce que je peux vous aider :
• 📚 Inscription et connexion
• 🎓 Cours et niveaux
• 💎 Abonnements et paiement
• 📊 Données et modèles
• 🐛 Problèmes techniques

Si votre question concerne un cas particulier, contactez directement l'administrateur :"""
    
    return default_response, 0, True


def get_whatsapp_link():
    """Retourner le lien WhatsApp de l'admin"""
    return WHATSAPP_ADMIN