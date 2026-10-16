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
            <div class="r-editor-wrapper">
                <div class="r-toolbar">
                    <span class="r-label">📝 Éditeur R (WebR)</span>
                    <button class="r-run-btn" onclick="executerR()">
                        <i class="fas fa-play"></i> Exécuter
                    </button>
                </div>
                <textarea id="r-input" class="r-textarea" placeholder="-- Écrivez votre code R ici"># Exemple : statistiques descriptives
ventes <- data.frame(
  produit = c('Cacao', 'Café', 'Anacarde', 'Coton', 'Cacao'),
  quantite = c(120, 85, 150, 95, 200),
  prix = c(1500, 1200, 800, 950, 1520)
)
ventes$total <- ventes$quantite * ventes$prix
summary(ventes$total)
mean(ventes$total)</textarea>
                <div class="r-result-header">
                    <span>📊 Console R</span>
                    <span id="r-status" class="r-status"></span>
                </div>
                <div id="r-result" class="r-result">
                    <p class="r-placeholder">Cliquez sur "Exécuter" pour lancer le code.</p>
                </div>
            </div>`;
        chargerWebR();
    }
        else if (outil === 'sql') {
        editeur.innerHTML = `
            <div class="sql-editor-wrapper">
                <div class="sql-toolbar">
                    <span class="sql-label">📝 Éditeur SQL (SQLite)</span>
                    <button class="sql-run-btn" onclick="executerSQL()">
                        <i class="fas fa-play"></i> Exécuter
                    </button>
                </div>
                <textarea id="sql-input" class="sql-textarea" placeholder="-- Écrivez votre requête SQL ici
-- Exemple : SELECT * FROM ventes LIMIT 5;

SELECT * FROM ventes LIMIT 5;">SELECT * FROM ventes LIMIT 5;</textarea>
                <div class="sql-result-header">
                    <span>📊 Résultat</span>
                    <span id="sql-status" class="sql-status"></span>
                </div>
                <div id="sql-result" class="sql-result">
                    <p class="sql-placeholder">Cliquez sur "Exécuter" pour lancer la requête.</p>
                </div>
            </div>`;
        chargerSQLJS();
    }
       else if (outil === 'tableau') {
        editeur.innerHTML = `
            <div class="tableau-wrapper">
                <div class="tableau-toolbar">
                    <span class="tableau-label">📊 Mini-Tableau interactif</span>
                    <div class="tableau-controls">
                        <select id="tableau-type" class="tableau-select">
                            <option value="bar">Barres</option>
                            <option value="line">Lignes</option>
                            <option value="pie">Camembert</option>
                            <option value="doughnut">Anneau</option>
                            <option value="scatter">Nuage de points</option>
                        </select>
                        <button class="tableau-run-btn" onclick="genererGraphique()">
                            <i class="fas fa-chart-line"></i> Générer
                        </button>
                    </div>
                </div>
                <div class="tableau-config">
                    <div class="tableau-config-item">
                        <label>📌 Dimension (Axe X)</label>
                        <select id="tableau-dim" class="tableau-select">
                            <option value="ville">Ville</option>
                            <option value="produit">Produit</option>
                            <option value="date">Date</option>
                        </select>
                    </div>
                    <div class="tableau-config-item">
                        <label>📈 Mesure (Axe Y)</label>
                        <select id="tableau-mesure" class="tableau-select">
                            <option value="quantite">Quantité totale</option>
                            <option value="prix_unitaire">Prix unitaire moyen</option>
                            <option value="chiffre_affaires">Chiffre d'affaires</option>
                        </select>
                    </div>
                </div>
                <div class="tableau-canvas-container">
                    <canvas id="tableau-canvas"></canvas>
                </div>
                <div class="tableau-tip">
                    💡 <strong>Astuce :</strong> dans Tableau, on glisse une <strong>dimension</strong> sur l'axe X et une <strong>mesure</strong> sur l'axe Y. Ici, on simule ce workflow avec les menus ci-dessus.
                </div>
            </div>`;
        setTimeout(initialiserTableau, 100);
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

// ============================================
// SQL.JS - MOTEUR SQL DANS LE NAVIGATEUR
// ============================================

let sqlDb = null;
let sqlJsLoaded = false;

function chargerSQLJS() {
    if (sqlJsLoaded) {
        return;
    }
    
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/sql-wasm.js';
    script.onload = initialiserBaseSQL;
    script.onerror = function() {
        document.getElementById('sql-result').innerHTML = 
            '<p style="color:#d33;">❌ Impossible de charger SQL.js. Vérifiez votre connexion.</p>';
    };
    document.head.appendChild(script);
    sqlJsLoaded = true;
}

function initialiserBaseSQL() {
    const SQL = window.initSqlJs;
    
    SQL({
        locateFile: file => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/${file}`
    }).then(function(SQLModule) {
        sqlDb = new SQLModule.Database();
        
        // Création de la table ventes avec données fictives ivoiriennes
        sqlDb.run(`
            CREATE TABLE ventes (
                id INTEGER PRIMARY KEY,
                date TEXT,
                produit TEXT,
                quantite INTEGER,
                prix_unitaire REAL,
                ville TEXT
            );
        `);
        
        // Insertion de 20 lignes de données fictives
        sqlDb.run(`
            INSERT INTO ventes VALUES
            (1, '2024-01-15', 'Cacao', 120, 1500.00, 'Abidjan'),
            (2, '2024-01-20', 'Café', 85, 1200.00, 'Abidjan'),
            (3, '2024-02-05', 'Cacao', 200, 1520.00, 'San-Pédro'),
            (4, '2024-02-12', 'Anacarde', 150, 800.00, 'Bouaké'),
            (5, '2024-02-18', 'Café', 60, 1180.00, 'Daloa'),
            (6, '2024-03-02', 'Cacao', 180, 1550.00, 'Abidjan'),
            (7, '2024-03-10', 'Anacarde', 220, 820.00, 'Korhogo'),
            (8, '2024-03-22', 'Coton', 95, 950.00, 'Bouaké'),
            (9, '2024-04-05', 'Cacao', 250, 1600.00, 'San-Pédro'),
            (10, '2024-04-14', 'Café', 110, 1250.00, 'Man'),
            (11, '2024-05-03', 'Coton', 130, 980.00, 'Korhogo'),
            (12, '2024-05-19', 'Anacarde', 175, 850.00, 'Bouaké'),
            (13, '2024-06-08', 'Cacao', 300, 1650.00, 'Abidjan'),
            (14, '2024-06-25', 'Café', 90, 1220.00, 'Daloa'),
            (15, '2024-07-11', 'Coton', 140, 1000.00, 'Korhogo'),
            (16, '2024-07-28', 'Cacao', 210, 1680.00, 'San-Pédro'),
            (17, '2024-08-15', 'Anacarde', 190, 870.00, 'Bouaké'),
            (18, '2024-09-02', 'Café', 75, 1150.00, 'Man'),
            (19, '2024-09-20', 'Cacao', 280, 1700.00, 'Abidjan'),
            (20, '2024-10-05', 'Coton', 160, 1020.00, 'Bouaké');
        `);
        
        console.log('✅ Base SQL initialisée avec 20 lignes dans la table "ventes"');
        
    }).catch(function(err) {
        console.error('Erreur SQL.js:', err);
    });
}

function executerSQL() {
    if (!sqlDb) {
        document.getElementById('sql-result').innerHTML = 
            '<p style="color:#d33;">⏳ La base de données est en cours de chargement. Réessayez dans quelques secondes.</p>';
        return;
    }
    
    const input = document.getElementById('sql-input').value.trim();
    if (!input) return;
    
    const status = document.getElementById('sql-status');
    const resultDiv = document.getElementById('sql-result');
    const start = performance.now();
    
    try {
        const resultats = sqlDb.exec(input);
        const duree = (performance.now() - start).toFixed(1);
        
        if (resultats.length === 0) {
            resultDiv.innerHTML = '<p style="color:#666;">✅ Requête exécutée (aucun résultat retourné).</p>';
            status.textContent = `⚡ ${duree} ms`;
            return;
        }
        
        // Construire le tableau HTML
        let html = '';
        resultats.forEach(function(resultat) {
            html += '<table class="sql-table"><thead><tr>';
            resultat.columns.forEach(function(col) {
                html += `<th>${escapeHtml(col)}</th>`;
            });
            html += '</tr></thead><tbody>';
            
            resultat.values.forEach(function(row) {
                html += '<tr>';
                row.forEach(function(cell) {
                    html += `<td>${cell === null ? '<em>NULL</em>' : escapeHtml(String(cell))}</td>`;
                });
                html += '</tr>';
            });
            html += '</tbody></table>';
        });
        
        resultDiv.innerHTML = html;
        status.textContent = `✅ ${resultats[0].values.length} ligne(s) en ${duree} ms`;
        
    } catch (error) {
        resultDiv.innerHTML = `<p style="color:#d33;">❌ Erreur SQL : ${escapeHtml(error.message)}</p>`;
        status.textContent = '';
    }
}




// ============================================
// R - MOTEUR WEBR DANS LE NAVIGATEUR
// ============================================

let webRInstance = null;
let webRLoaded = false;

async function chargerWebR() {
    if (webRLoaded && webRInstance) {
        return;
    }
    
    const status = document.getElementById('r-status');
    if (status) status.textContent = '⏳ Chargement de R...';
    
    try {
        // Utilisation d'une version spécifique et stable
        const webRVersion = 'v0.4.2';
        const webRUrl = `https://webr.r-wasm.org/${webRVersion}/webr.mjs`;
        
        // Import dynamique du module WebR
        const { WebR } = await import(webRUrl);
        
        // Forcer le channel PostMessage pour éviter les problèmes de SharedArrayBuffer
        webRInstance = new WebR({
            channelType: 'PostMessage'
        });
        
        await webRInstance.init();
        
        webRLoaded = true;
        if (status) status.textContent = '✅ R prêt';
        console.log('✅ WebR initialisé (version ' + webRVersion + ')');
        
        const resultDiv = document.getElementById('r-result');
        if (resultDiv) {
            resultDiv.innerHTML = '<p style="color:#27ae60;">✅ R est prêt. Cliquez sur "Exécuter" pour lancer votre code.</p>';
        }
        
    } catch (error) {
        console.error('Erreur WebR:', error);
        const status = document.getElementById('r-status');
        if (status) status.textContent = '❌ Erreur';
        const resultDiv = document.getElementById('r-result');
        if (resultDiv) {
            resultDiv.innerHTML = '<p style="color:#d33;">❌ Impossible de charger R. Vérifiez votre connexion internet.</p>';
        }
    }
}
async function executerR() {
    const resultDiv = document.getElementById('r-result');
    const status = document.getElementById('r-status');
    
    if (!webRInstance) {
        resultDiv.innerHTML = '<p style="color:#d33;">⏳ R est en cours de chargement. Patientez quelques secondes.</p>';
        return;
    }
    
    const input = document.getElementById('r-input').value.trim();
    if (!input) return;
    
    const start = performance.now();
    resultDiv.innerHTML = '<p class="r-placeholder">⏳ Exécution en cours...</p>';
    status.textContent = '';
    
    try {
        // Utiliser Shelter pour capturer stdout + résultat
        const shelter = await new webRInstance.Shelter();
        let html = '';
        let duration;
        
        try {
            const captured = await shelter.captureR(input);
            duration = (performance.now() - start).toFixed(0);
            
            // Sortie console (print, cat, etc.)
            if (captured.output && captured.output.length > 0) {
                captured.output.forEach(item => {
                    if (item.type === 'stdout' || item.type === 'stderr') {
                        html += `<pre class="r-output">${escapeHtml(item.data)}</pre>`;
                    }
                });
            }
            
            // Valeur de retour du code R
            if (captured.result) {
                const jsValue = await captured.result.toJs();
                const valueStr = formaterValeurR(jsValue);
                if (valueStr) {
                    html += `<pre class="r-output r-value">${escapeHtml(valueStr)}</pre>`;
                }
            }
        } finally {
            shelter.purge();
        }
        
        if (!html) {
            html = '<p style="color:#666;">✅ Code exécuté (aucun résultat affiché).</p>';
        }
        
        resultDiv.innerHTML = html;
        status.textContent = `✅ ${duration} ms`;
        
    } catch (error) {
        console.error('Erreur R:', error);
        resultDiv.innerHTML = `<p style="color:#d33;">❌ Erreur R : ${escapeHtml(error.message)}</p>`;
        status.textContent = '';
    }
}

// Formater les valeurs retournées par R
function formaterValeurR(jsValue) {
    if (jsValue === null || jsValue === undefined) return null;
    
    // Cas simple : valeur unique
    if (typeof jsValue === 'number' || typeof jsValue === 'boolean' || typeof jsValue === 'string') {
        return `[1] ${jsValue}`;
    }
    
    // Cas avec structure { type, names, values }
    if (jsValue.values) {
        const values = jsValue.values;
        const names = jsValue.names || [];
        
        // Tableau de valeurs
        if (Array.isArray(values)) {
            // Cas data frame
            if (values.length > 0 && Array.isArray(values[0])) {
                let output = '';
                values.forEach((col, i) => {
                    const colName = names[i] || `Col${i + 1}`;
                    output += `${colName}: ${col.join(', ')}\n`;
                });
                return output.trim();
            }
            // Cas vecteur simple
            return `[1] ${values.join(' ')}`;
        }
        
        // Objet
        if (typeof values === 'object') {
            return JSON.stringify(values, null, 2);
        }
    }
    
    // Cas par défaut
    return String(jsValue);
}



// ============================================
// MINI-TABLEAU INTERACTIF (Chart.js)
// ============================================

let tableauChart = null;
let chartJsLoaded = false;

const TABLEAU_DATA = [
    { ville: 'Abidjan',   produit: 'Cacao',    date: '2024-01', quantite: 120, prix_unitaire: 1500 },
    { ville: 'Abidjan',   produit: 'Café',     date: '2024-01', quantite: 85,  prix_unitaire: 1200 },
    { ville: 'San-Pédro', produit: 'Cacao',    date: '2024-02', quantite: 200, prix_unitaire: 1520 },
    { ville: 'Bouaké',    produit: 'Anacarde', date: '2024-02', quantite: 150, prix_unitaire: 800  },
    { ville: 'Daloa',     produit: 'Café',     date: '2024-02', quantite: 60,  prix_unitaire: 1180 },
    { ville: 'Abidjan',   produit: 'Cacao',    date: '2024-03', quantite: 180, prix_unitaire: 1550 },
    { ville: 'Korhogo',   produit: 'Anacarde', date: '2024-03', quantite: 220, prix_unitaire: 820  },
    { ville: 'Bouaké',    produit: 'Coton',    date: '2024-03', quantite: 95,  prix_unitaire: 950  },
    { ville: 'San-Pédro', produit: 'Cacao',    date: '2024-04', quantite: 250, prix_unitaire: 1600 },
    { ville: 'Man',       produit: 'Café',     date: '2024-04', quantite: 110, prix_unitaire: 1250 },
    { ville: 'Korhogo',   produit: 'Coton',    date: '2024-05', quantite: 130, prix_unitaire: 980  },
    { ville: 'Bouaké',    produit: 'Anacarde', date: '2024-05', quantite: 175, prix_unitaire: 850  },
    { ville: 'Abidjan',   produit: 'Cacao',    date: '2024-06', quantite: 300, prix_unitaire: 1650 },
    { ville: 'Daloa',     produit: 'Café',     date: '2024-06', quantite: 90,  prix_unitaire: 1220 },
    { ville: 'Korhogo',   produit: 'Coton',    date: '2024-07', quantite: 140, prix_unitaire: 1000 }
];

function chargerChartJS(callback) {
    if (chartJsLoaded && window.Chart) {
        callback();
        return;
    }
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
    script.onload = function() {
        chartJsLoaded = true;
        callback();
    };
    script.onerror = function() {
        console.error('Impossible de charger Chart.js');
    };
    document.head.appendChild(script);
}

function initialiserTableau() {
    chargerChartJS(function() {
        genererGraphique();
    });
}

function genererGraphique() {
    const canvas = document.getElementById('tableau-canvas');
    if (!canvas) return;
    
    const type = document.getElementById('tableau-type').value;
    const dimension = document.getElementById('tableau-dim').value;
    const mesure = document.getElementById('tableau-mesure').value;
    
    // Agréger les données
    const agreg = {};
    TABLEAU_DATA.forEach(row => {
        const key = row[dimension];
        if (!agreg[key]) agreg[key] = { quantite: 0, prix_unitaire: 0, chiffre_affaires: 0, count: 0 };
        
        agreg[key].quantite += row.quantite;
        agreg[key].prix_unitaire += row.prix_unitaire;
        agreg[key].chiffre_affaires += row.quantite * row.prix_unitaire;
        agreg[key].count += 1;
    });
    
    // Calculer la valeur finale selon la mesure
    const labels = Object.keys(agreg).sort();
    const data = labels.map(label => {
        if (mesure === 'prix_unitaire') {
            return Math.round(agreg[label].prix_unitaire / agreg[label].count);
        }
        return agreg[label][mesure];
    });
    
    // Couleurs
    const couleurs = [
        '#2a5298', '#27ae60', '#e67e22', '#e74c3c', '#9b59b6',
        '#3498db', '#16a085', '#f39c12', '#c0392b', '#8e44ad'
    ];
    
    // Détruire l'ancien graphique
    if (tableauChart) tableauChart.destroy();
    
    // Créer le graphique
    const ctx = canvas.getContext('2d');
    tableauChart = new Chart(ctx, {
        type: type === 'doughnut' ? 'doughnut' : type,
        data: {
            labels: labels,
            datasets: [{
                label: getLabelMesure(mesure),
                data: data,
                backgroundColor: type === 'line' ? 'rgba(42, 82, 152, 0.2)' : couleurs,
                borderColor: type === 'line' ? '#2a5298' : couleurs,
                borderWidth: 2,
                fill: type === 'line',
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: type === 'pie' || type === 'doughnut',
                    position: 'bottom'
                },
                title: {
                    display: true,
                    text: `${getLabelMesure(mesure)} par ${getLabelDimension(dimension)}`,
                    font: { size: 14, weight: 'bold' },
                    color: '#1e3c72'
                }
            },
            scales: (type === 'pie' || type === 'doughnut') ? {} : {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString('fr-FR');
                        }
                    }
                }
            }
        }
    });
}

function getLabelMesure(mesure) {
    const labels = {
        quantite: 'Quantité totale',
        prix_unitaire: 'Prix unitaire moyen (FCFA)',
        chiffre_affaires: 'Chiffre d\'affaires (FCFA)'
    };
    return labels[mesure] || mesure;
}

function getLabelDimension(dim) {
    const labels = { ville: 'ville', produit: 'produit', date: 'date' };
    return labels[dim] || dim;
}