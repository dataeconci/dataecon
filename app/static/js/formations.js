// ============================================
// FORMATION PRATIQUE - Logique JavaScript
// ============================================

let outilActif = null;
let niveauActif = 'debutant';

// ============================================
// CHARGER UN OUTIL
// ============================================
function chargerOutil(outil) {
    outilActif = outil;
    
    // Mettre à jour la classe active sur les boutons
    document.querySelectorAll('.outil-card').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`.outil-card[data-outil="${outil}"]`).classList.add('active');
    
    // Mettre à jour le label
    mettreAJourLabel();
    
    // Charger l'éditeur correspondant
    const editeur = document.getElementById('editeur');
    
    if (outil === 'python') {
        editeur.innerHTML = `
            <iframe src="https://jupyterlite.github.io/demo/repl/index.html?kernel=python&toolbar=1"
                    title="Python REPL"
                    allow="cross-origin-isolated">
            </iframe>`;
    } 
    else if (outil === 'r') {
        editeur.innerHTML = `
            <div class="placeholder">
                <i class="fas fa-r-project"></i>
                <p>R / RStudio - En cours d'intégration</p>
                <small style="margin-top:10px; color:#aaa;">
                    L'environnement R sera disponible prochainement.
                    En attendant, posez vos questions à l'instructeur IA !
                </small>
            </div>`;
    }
    else if (outil === 'sql') {
        editeur.innerHTML = `
            <div class="placeholder">
                <i class="fas fa-database"></i>
                <p>SQL - En cours d'intégration</p>
                <small style="margin-top:10px; color:#aaa;">
                    L'éditeur SQL sera disponible prochainement.
                </small>
            </div>`;
    }
    else if (outil === 'tableau') {
        editeur.innerHTML = `
            <div class="placeholder">
                <i class="fas fa-chart-bar"></i>
                <p>Tableau - En cours d'intégration</p>
                <small style="margin-top:10px; color:#aaa;">
                    Les tableaux de bord Tableau seront disponibles prochainement.
                </small>
            </div>`;
    }
}

// ============================================
// CHANGER DE NIVEAU
// ============================================
function changerNiveau(niveau) {
    niveauActif = niveau;
    
    document.querySelectorAll('.niveau-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`.niveau-btn[data-niveau="${niveau}"]`).classList.add('active');
    
    mettreAJourLabel();
    
    // Message de l'IA quand on change de niveau
    const messages = {
        debutant: "Niveau **Débutant** activé 🌱 Je vais vous expliquer les concepts pas à pas, avec des exemples simples.",
        intermediaire: "Niveau **Intermédiaire** activé 🚀 On va approfondir les concepts et faire des exercices plus poussés.",
        avance: "Niveau **Avancé** activé 🎯 On va travailler sur des cas complexes et des optimisations."
    };
    
    ajouterMessageIA(messages[niveau]);
}

// ============================================
// METTRE À JOUR LE LABEL
// ============================================
function mettreAJourLabel() {
    const label = document.getElementById('outil-actif-label');
    if (outilActif) {
        const noms = { python: 'Python', r: 'R', sql: 'SQL', tableau: 'Tableau' };
        const niveaux = { debutant: 'Débutant', intermediaire: 'Intermédiaire', avance: 'Avancé' };
        label.textContent = `${noms[outilActif]} - ${niveaux[niveauActif]}`;
    } else {
        label.textContent = 'Aucun outil sélectionné';
    }
}

// ============================================
// ENVOYER UNE QUESTION À L'IA
// ============================================
async function envoyerQuestion() {
    const input = document.getElementById('question-ia');
    const question = input.value.trim();
    
    if (!question) return;
    
    // Afficher la question
    ajouterMessageUtilisateur(question);
    input.value = '';
    
    // Afficher l'indicateur de chargement
    const loadingId = ajouterMessageIA('...', true);
    
    try {
        const response = await fetch('/api/tutor', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: question,
                outil: outilActif || 'general',
                niveau: niveauActif
            })
        });
        
        const data = await response.json();
        
        // Supprimer l'indicateur de chargement
        document.getElementById(loadingId).remove();
        
        // Afficher la réponse
        ajouterMessageIA(data.reponse);
        
    } catch (error) {
        document.getElementById(loadingId).remove();
        ajouterMessageIA("❌ Désolé, une erreur est survenue. Veuillez réessayer.");
        console.error('Erreur:', error);
    }
}

// ============================================
// AJOUTER UN MESSAGE DE L'IA
// ============================================
function ajouterMessageIA(texte, isLoading = false) {
    const container = document.getElementById('chat-messages');
    const id = 'msg-' + Date.now() + Math.random().toString(36).substr(2, 5);
    
    const div = document.createElement('div');
    div.className = 'msg-ia';
    div.id = id;
    
    if (isLoading) {
        div.innerHTML = `<strong>🤖 EconBot</strong><p class="loading-dots">${texte}</p>`;
    } else {
        // Convertir les **gras** en <strong>
        const html = texte
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
        div.innerHTML = `<strong>🤖 EconBot</strong><p>${html}</p>`;
    }
    
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    
    return id;
}

// ============================================
// AJOUTER UN MESSAGE UTILISATEUR
// ============================================
function ajouterMessageUtilisateur(texte) {
    const container = document.getElementById('chat-messages');
    
    const div = document.createElement('div');
    div.className = 'msg-user';
    div.innerHTML = `<strong>Vous</strong><p>${escapeHtml(texte)}</p>`;
    
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// ============================================
// SÉCURITÉ : échapper le HTML
// ============================================
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// INITIALISATION
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('📚 Section Formation chargée');
});