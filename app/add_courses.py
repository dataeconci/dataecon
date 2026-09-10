#!/usr/bin/env python
import sys
import os
sys.path.append('/app')
from app import app, db, Course, Progress
from datetime import datetime

def add_courses():
    with app.app_context():
        # 1. Supprimer les progressions d'abord
        print("🗑️ Suppression des progressions...")
        Progress.query.delete()
        db.session.commit()
        print("✅ Progressions supprimées")

        # 2. Supprimer les anciens cours
        courses = Course.query.all()
        for course in courses:
            if course.file_path and os.path.exists(course.file_path):
                os.remove(course.file_path)
            db.session.delete(course)
        db.session.commit()
        print("🗑️ Anciens cours supprimés")

        # 3. Ajouter les nouveaux cours
        print("📚 Ajout des nouveaux cours...")
        courses_data = [
            {
                'title': 'Économétrie Fondamentale',
                'description': 'Les bases de l\'économétrie : régression linéaire, hypothèses, interprétation.',
                'level': 'Débutant',
                'content': '<p>Cours complet d\'économétrie fondamentale.</p>',
                'file_name': 'econometrie_fondamentale.pdf',
                'file_path': '/app/data/pdfs/econometrie_fondamentale.pdf'
            },
            {
                'title': 'Régression Linéaire Multiple',
                'description': 'Modèles avec plusieurs variables, tests d\'hypothèses.',
                'level': 'Intermédiaire',
                'content': '<p>Cours complet sur la régression linéaire multiple.</p>',
                'file_name': 'regression_multiple.pdf',
                'file_path': '/app/data/pdfs/regression_multiple.pdf'
            },
            {
                'title': 'Analyse des Séries Temporelles',
                'description': 'ARIMA, stationnarité, prévisions économiques.',
                'level': 'Avancé',
                'content': '<p>Cours complet sur les séries temporelles.</p>',
                'file_name': 'series_temporelles.pdf',
                'file_path': '/app/data/pdfs/series_temporelles.pdf'
            },
            {
                'title': 'Modèles à Équations Simultanées',
                'description': 'Variables instrumentales, identification.',
                'level': 'Avancé',
                'content': '<p>Cours complet sur les modèles à équations simultanées.</p>',
                'file_name': 'equations_simultanees.pdf',
                'file_path': '/app/data/pdfs/equations_simultanees.pdf'
            },
            {
                'title': 'Économétrie des Données de Panel',
                'description': 'Effets fixes, effets aléatoires, panel dynamique.',
                'level': 'Avancé',
                'content': '<p>Cours complet sur les données de panel.</p>',
                'file_name': 'donnees_panel.pdf',
                'file_path': '/app/data/pdfs/donnees_panel.pdf'
            }
        ]

        for c in courses_data:
            course = Course(**c)
            db.session.add(course)
        
        db.session.commit()
        print(f"✅ {len(courses_data)} cours ajoutés avec succès !")

if __name__ == '__main__':
    add_courses()
#!/usr/bin/env python
import sys
import os
sys.path.append('/app')
from app import app, db, Course, Progress
from datetime import datetime

def add_courses():
    with app.app_context():
        # 1. Supprimer les progressions
        print("🗑️ Suppression des progressions...")
        Progress.query.delete()
        db.session.commit()
        print("✅ Progressions supprimées")

        # 2. Supprimer les anciens cours
        courses = Course.query.all()
        for course in courses:
            if course.file_path and os.path.exists(course.file_path):
                os.remove(course.file_path)
            db.session.delete(course)
        db.session.commit()
        print("🗑️ Anciens cours supprimés")

        # 3. Ajouter les nouveaux cours avec TOUS vos PDF
        print("📚 Ajout des nouveaux cours...")
        courses_data = [
            {
                'title': 'Econométrie - Cours complet M1',
                'description': 'Cours complet d\'économétrie niveau Master 1.',
                'level': 'Débutant',
                'content': '<p>Cours complet d\'économétrie niveau Master 1.</p>',
                'file_name': 'Econometrie -- m1.pdf',
                'file_path': '/app/data/pdfs/Econometrie -- m1.pdf'
            },
            {
                'title': 'Introduction à l\'Économétrie - Wooldridge',
                'description': 'Cours d\'introduction à l\'économétrie par Wooldridge.',
                'level': 'Débutant',
                'content': '<p>Introduction à l\'économétrie par Wooldridge.</p>',
                'file_name': '20260903_115542_Introduction_a_leconometrie_wooldrid.pdf',
                'file_path': '/app/data/pdfs/20260903_115542_Introduction_a_leconometrie_wooldrid.pdf'
            },
            {
                'title': 'Econométrie Appliquée avec R',
                'description': 'Manuel des cas pratiques sur R.',
                'level': 'Intermédiaire',
                'content': '<p>Manuel d\'économétrie appliquée avec R.</p>',
                'file_name': '20260903_134410_economtrie_aplique_R.pdf',
                'file_path': '/app/data/pdfs/20260903_134410_economtrie_aplique_R.pdf'
            },
            {
                'title': 'Introductory Econometrics - A Modern Approach',
                'description': 'Manuel de référence en économétrie par Wooldridge.',
                'level': 'Intermédiaire',
                'content': '<p>Introductory Econometrics par Wooldridge.</p>',
                'file_name': 'Introductory Econometrics- A modern Approach.pdf',
                'file_path': '/app/data/pdfs/Introductory Econometrics- A modern Approach.pdf'
            },
            {
                'title': 'Econometric Methods - 4th Edition',
                'description': 'Méthodes économétriques avancées.',
                'level': 'Avancé',
                'content': '<p>Econometric Methods - 4ème édition.</p>',
                'file_name': 'Econometric Methods, Fourth Edition ( PDFDrive ).pdf',
                'file_path': '/app/data/pdfs/Econometric Methods, Fourth Edition ( PDFDrive ).pdf'
            },
            {
                'title': 'Greene - Econometric Analysis 8th Edition',
                'description': 'Analyse économétrique avancée.',
                'level': 'Avancé',
                'content': '<p>Greene Econometric Analysis 8th Edition.</p>',
                'file_name': 'Greene_Econometric_Analysis _8th Ed-3.pdf',
                'file_path': '/app/data/pdfs/Greene_Econometric_Analysis _8th Ed-3.pdf'
            },
            {
                'title': 'Maddala - Introduction to Econometrics',
                'description': 'Introduction à l\'économétrie par Maddala.',
                'level': 'Intermédiaire',
                'content': '<p>Maddala Introduction to Econometrics.</p>',
                'file_name': 'Maddala-Introduction to Econometrics.pdf',
                'file_path': '/app/data/pdfs/Maddala-Introduction to Econometrics.pdf'
            },
            {
                'title': 'Econométrie - 10e édition',
                'description': 'Cours complet d\'économétrie.',
                'level': 'Intermédiaire',
                'content': '<p>Économétrie 10e édition.</p>',
                'file_name': 'Econométrie 10e edition.pdf',
                'file_path': '/app/data/pdfs/Econométrie 10e edition.pdf'
            },
            {
                'title': 'Econométrie - Cours et Exercices',
                'description': 'Cours d\'économétrie avec exercices corrigés.',
                'level': 'Intermédiaire',
                'content': '<p>Econométrie cours et exercices.</p>',
                'file_name': 'econometrie cours et exo.pdf',
                'file_path': '/app/data/pdfs/econometrie cours et exo.pdf'
            },
            {
                'title': 'Analyse des Séries Temporelles - Tsay',
                'description': 'Analyse des séries temporelles financières.',
                'level': 'Avancé',
                'content': '<p>Analysis of Financial Time Series par Tsay.</p>',
                'file_name': 'Partager Tsay_Analysis_of_Financial_Time_Series.pdf',
                'file_path': '/app/data/pdfs/Partager Tsay_Analysis_of_Financial_Time_Series.pdf'
            },
            {
                'title': '100 fiches pour comprendre les sciences économiques',
                'description': 'Fiches de synthèse en sciences économiques.',
                'level': 'Débutant',
                'content': '<p>100 fiches pour comprendre les sciences économiques.</p>',
                'file_name': '100 fiches pour comprendre les sciences écomomiques.pdf',
                'file_path': '/app/data/pdfs/100 fiches pour comprendre les sciences écomomiques.pdf'
            },
            {
                'title': 'Analyse et gestion du risque bancaire',
                'description': 'Cours sur le risque bancaire.',
                'level': 'Avancé',
                'content': '<p>Analyse et gestion du risque bancaire.</p>',
                'file_name': 'Analyse et gestion du risque bancaire.pdf',
                'file_path': '/app/data/pdfs/Analyse et gestion du risque bancaire.pdf'
            },
            {
                'title': 'Banques centrales - Nouveaux outils de politique monétaire',
                'description': 'Les nouveaux outils de politique monétaire.',
                'level': 'Avancé',
                'content': '<p>Banques centrales et politique monétaire.</p>',
                'file_name': 'Banques centrales les nouveaux outils de politique monétaire.pdf',
                'file_path': '/app/data/pdfs/Banques centrales les nouveaux outils de politique monétaire.pdf'
            },
            {
                'title': 'Comptabilité analytique',
                'description': 'Cours de comptabilité analytique.',
                'level': 'Débutant',
                'content': '<p>Comptabilité analytique.</p>',
                'file_name': 'Comptabilité analytique.pdf',
                'file_path': '/app/data/pdfs/Comptabilité analytique.pdf'
            },
            {
                'title': 'L\'optimisation mathématique pour les fonctions à plusieurs variables',
                'description': 'Cours d\'optimisation mathématique.',
                'level': 'Intermédiaire',
                'content': '<p>Optimisation mathématique pour les fonctions à plusieurs variables.</p>',
                'file_name': "L'optimisation mathématique pour les fonctions à plusieurs variables..pdf",
                'file_path': "/app/data/pdfs/L'optimisation mathématique pour les fonctions à plusieurs variables..pdf"
            },
            {
                'title': 'Les théories économiques et leurs applications',
                'description': 'Théories économiques et applications.',
                'level': 'Débutant',
                'content': '<p>Les théories économiques et leurs applications.</p>',
                'file_name': 'Les théories économiques et leurs applications.pdf',
                'file_path': '/app/data/pdfs/Les théories économiques et leurs applications.pdf'
            },
            {
                'title': 'Mathématiques financières',
                'description': 'Cours de mathématiques financières.',
                'level': 'Intermédiaire',
                'content': '<p>Mathématiques financières.</p>',
                'file_name': 'Mathématiques financières.pdf',
                'file_path': '/app/data/pdfs/Mathématiques financières.pdf'
            },
            {
                'title': 'Programmation linéaire et Optimisation',
                'description': 'Cours de programmation linéaire.',
                'level': 'Intermédiaire',
                'content': '<p>Programmation linéaire et Optimisation.</p>',
                'file_name': 'Programmation linéaire et Optimisation.pdf',
                'file_path': '/app/data/pdfs/Programmation linéaire et Optimisation.pdf'
            },
            {
                'title': 'Théorie des jeux',
                'description': 'Introduction à la théorie des jeux.',
                'level': 'Intermédiaire',
                'content': '<p>Théorie des jeux.</p>',
                'file_name': 'théorie des jeux.pdf',
                'file_path': '/app/data/pdfs/théorie des jeux.pdf'
            },
            {
                'title': 'Théorie des jeux et économie de l\'information',
                'description': 'Théorie des jeux appliquée à l\'économie.',
                'level': 'Avancé',
                'content': '<p>Théorie des jeux et économie de l\'information.</p>',
                'file_name': "théorie des jeux et économie de l'information.pdf",
                'file_path': "/app/data/pdfs/théorie des jeux et économie de l'information.pdf"
            },
            {
                'title': 'Économie de l\'environnement et économie écologique',
                'description': 'Économie de l\'environnement.',
                'level': 'Avancé',
                'content': '<p>Économie de l\'environnement et économie écologique.</p>',
                'file_name': "Économie de l'environnement et économie écologique.pdf",
                'file_path': "/app/data/pdfs/Économie de l'environnement et économie écologique.pdf"
            },
            {
                'title': 'Économétrie Appliquée - Manuel des cas pratiques sur EViews',
                'description': 'Manuel des cas pratiques sur EViews.',
                'level': 'Intermédiaire',
                'content': '<p>Économétrie Appliquée - Manuel des cas pratiques sur EViews.</p>',
                'file_name': 'Économétrie_Appliquée_Manuel_des_cas_pratiques_sur_EViews_Jonas.pdf',
                'file_path': '/app/data/pdfs/Économétrie_Appliquée_Manuel_des_cas_pratiques_sur_EViews_Jonas.pdf'
            }
        ]

        for c in courses_data:
            # Vérifier si le fichier existe
            if os.path.exists(c['file_path']):
                course = Course(**c)
                db.session.add(course)
                print(f"✅ Ajout du cours: {c['title']}")
            else:
                print(f"❌ Fichier non trouvé: {c['file_path']}")
        
        db.session.commit()
        print(f"✅ {len(courses_data)} cours ajoutés avec succès !")

if __name__ == '__main__':
    add_courses()