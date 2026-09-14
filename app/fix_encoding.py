#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour corriger l'encodage UTF-8 cassé dans la base de données
"""

import os
import sys
sys.path.append('/app')

from app import app, db, Course
import re

def fix_encoding_text(text):
    """Corriger les caractères mal encodés"""
    if not text:
        return text
    
    # Mapping des caractères cassés les plus courants
    replacements = {
        'Ã©': 'é', 'Ã¨': 'è', 'Ã ': 'à', 'Ã¢': 'â', 'Ãª': 'ê', 'Ã®': 'î',
        'Ã´': 'ô', 'Ã¹': 'ù', 'Ã»': 'û', 'Ã§': 'ç', 'Ã«': 'ë', 'Ã¯': 'ï',
        'Ã¼': 'ü', 'Ã¶': 'ö', 'Ã¤': 'ä', 'Ã‰': 'É', 'Ã€': 'À', 'Ã‡': 'Ç',
        'â€™': "'", 'â€œ': '"', 'â€': '"', 'â€"': '—', 'â€"': '–',
        '??': 'é',  # Les ?? sont probablement des é
        '?': '?',
    }
    
    result = text
    for broken, correct in replacements.items():
        result = result.replace(broken, correct)
    
    # Remplacer les séquences de ? par é (heuristique)
    # Si on a "math??matique" -> "mathématique"
    result = re.sub(r'(\w)\?\?(\w)', r'\1é\2', result)
    
    return result


def fix_all():
    with app.app_context():
        courses = Course.query.all()
        print(f"📚 {len(courses)} cours à corriger", flush=True)
        
        for course in courses:
            changed = False
            
            # Corriger le titre
            new_title = fix_encoding_text(course.title)
            if new_title != course.title:
                print(f"  Titre: {course.title!r} → {new_title!r}", flush=True)
                course.title = new_title
                changed = True
            
            # Corriger la description
            new_desc = fix_encoding_text(course.description)
            if new_desc != course.description:
                print(f"  Desc:  {course.description!r} → {new_desc!r}", flush=True)
                course.description = new_desc
                changed = True
            
            # Corriger le niveau (CRITIQUE pour les filtres)
            new_level = fix_encoding_text(course.level)
            # Normaliser le niveau
            if 'butant' in new_level.lower() or 'ebutant' in new_level.lower():
                new_level = 'Débutant'
            elif 'interm' in new_level.lower():
                new_level = 'Intermédiaire'
            elif 'avanc' in new_level.lower():
                new_level = 'Avancé'
            
            if new_level != course.level:
                print(f"  Niveau: {course.level!r} → {new_level!r}", flush=True)
                course.level = new_level
                changed = True
            
            # Corriger le nom du fichier
            if course.file_name:
                new_fname = fix_encoding_text(course.file_name)
                if new_fname != course.file_name:
                    print(f"  Fichier: {course.file_name!r} → {new_fname!r}", flush=True)
                    course.file_name = new_fname
                    changed = True
        
        db.session.commit()
        print(f"✅ Correction terminée !", flush=True)


if __name__ == '__main__':
    fix_all()