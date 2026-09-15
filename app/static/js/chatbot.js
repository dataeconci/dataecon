/* ============================================
   CHATBOT DataEcon.Ci - Logique JavaScript
   ============================================ */

(function() {
    'use strict';
    
    // Configuration
    const API_URL = '/api/chat';
    const SUGGESTIONS = [
        'Comment s\'inscrire ?',
        'Voir les cours',
        'Comment payer ?',
        'Mot de passe oublié'
    ];
    
    // Récupérer les éléments du DOM
    const toggleBtn = document.getElementById('chatbotToggle');
    const closeBtn = document.getElementById('chatbotClose');
    const chatWindow = document.getElementById('chatbotWindow');
    const messagesContainer = document.getElementById('chatbotMessages');
    const inputField = document.getElementById('chatbotInput');
    const sendBtn = document.getElementById('chatbotSend');
    const suggestionsContainer = document.getElementById('chatbotSuggestions');
    const badge = document.getElementById('chatbotBadge');
    
    let isOpen = false;
    let isFirstOpen = true;
    
    // ==================== INITIALISATION ====================
    function init() {
        // Ouvrir/Fermer le chat
        toggleBtn.addEventListener('click', toggleChat);
        closeBtn.addEventListener('click', closeChat);
        
        // Envoyer un message
        sendBtn.addEventListener('click', sendMessage);
        inputField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Suggestions
        renderSuggestions();
        
        // Message de bienvenue
        loadHistory();
    }
    
    // ==================== OUVERTURE / FERMETURE ====================
    function toggleChat() {
        if (isOpen) {
            closeChat();
        } else {
            openChat();
        }
    }
    
    function openChat() {
        isOpen = true;
        chatWindow.classList.add('active');
        toggleBtn.classList.add('active');
        toggleBtn.innerHTML = '<i class="fas fa-times"></i>';
        
        // Masquer le badge
        if (badge) {
            badge.style.display = 'none';
        }
        
        // Afficher le message de bienvenue la première fois
        if (isFirstOpen) {
            setTimeout(() => {
                addBotMessage(`Bonjour ! 👋 Je suis **EconBot**, votre assistant DataEcon.Ci.

Je peux vous aider sur :
• 📚 Inscription et connexion
• 🎓 Cours et formations
• 💎 Abonnements et paiement
• 📊 Données et modèles

Comment puis-je vous aider ?`);
                isFirstOpen = false;
            }, 300);
        }
        
        // Focus sur l'input
        setTimeout(() => inputField.focus(), 400);
    }
    
    function closeChat() {
        isOpen = false;
        chatWindow.classList.remove('active');
        toggleBtn.classList.remove('active');
        toggleBtn.innerHTML = '<i class="fas fa-comments"></i>';
    }
    
    // ==================== GESTION DES MESSAGES ====================
    function sendMessage() {
        const message = inputField.value.trim();
        if (!message) return;
        
        // Afficher le message de l'utilisateur
        addUserMessage(message);
        inputField.value = '';
        
        // Désactiver l'envoi
        sendBtn.disabled = true;
        
        // Afficher l'indicateur de saisie
        showTyping();
        
        // Envoyer au serveur
        fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            hideTyping();
            sendBtn.disabled = false;
            
            if (data.success) {
                addBotMessage(data.response, data.needs_whatsapp, data.whatsapp_link);
            } else {
                addBotMessage('Désolé, une erreur est survenue. Veuillez réessayer.', true, 'https://wa.me/qr/NIDJGSRVJTJTM1');
            }
        })
        .catch(error => {
            console.error('Erreur chatbot:', error);
            hideTyping();
            sendBtn.disabled = false;
            addBotMessage('Impossible de contacter le serveur. Vérifiez votre connexion.', true, 'https://wa.me/qr/NIDJGSRVJTJTM1');
        });
    }
    
    function addUserMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message user';
        messageDiv.innerHTML = `
            <div class="chatbot-message-avatar">
                <i class="fas fa-user"></i>
            </div>
            <div class="chatbot-message-content">${escapeHtml(text)}</div>
        `;
        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }
    
    function addBotMessage(text, showWhatsapp = false, whatsappLink = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message bot';
        
        // Convertir le markdown basique (** gras **)
        let formattedText = escapeHtml(text)
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>');
        
        let whatsappBtn = '';
        if (showWhatsapp && whatsappLink) {
            whatsappBtn = `
                <a href="${whatsappLink}" 
                   target="_blank" 
                   class="chatbot-whatsapp-btn">
                    <i class="fab fa-whatsapp"></i> Contacter l'admin sur WhatsApp
                </a>
            `;
        }
        
        messageDiv.innerHTML = `
            <div class="chatbot-message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="chatbot-message-content">
                ${formattedText}
                ${whatsappBtn}
            </div>
        `;
        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }
    
    // ==================== INDICATEUR DE SAISIE ====================
    function showTyping() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chatbot-message bot';
        typingDiv.id = 'chatbotTyping';
        typingDiv.innerHTML = `
            <div class="chatbot-message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="chatbot-typing">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        messagesContainer.appendChild(typingDiv);
        scrollToBottom();
    }
    
    function hideTyping() {
        const typing = document.getElementById('chatbotTyping');
        if (typing) {
            typing.remove();
        }
    }
    
    // ==================== SUGGESTIONS ====================
    function renderSuggestions() {
        if (!suggestionsContainer) return;
        
        suggestionsContainer.innerHTML = '';
        SUGGESTIONS.forEach(suggestion => {
            const btn = document.createElement('button');
            btn.className = 'chatbot-suggestion';
            btn.textContent = suggestion;
            btn.addEventListener('click', () => {
                inputField.value = suggestion;
                sendMessage();
            });
            suggestionsContainer.appendChild(btn);
        });
    }
    
    // ==================== HISTORIQUE ====================
    function loadHistory() {
        // Optionnel : charger l'historique depuis localStorage
        const history = localStorage.getItem('chatbot_history');
        if (history) {
            try {
                const messages = JSON.parse(history);
                // Limiter aux 3 derniers pour éviter surcharge
                messages.slice(-3).forEach(msg => {
                    // Ne pas recharger pour l'instant
                });
            } catch (e) {
                console.error('Erreur chargement historique:', e);
            }
        }
    }
    
    // ==================== UTILITAIRES ====================
    function scrollToBottom() {
        setTimeout(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 100);
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // ==================== DÉMARRAGE ====================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
})();