
(function() {
    'use strict';
    
    const API_URL = '/api/chat';
    const SUGGESTIONS = [
        'Comment s\'inscrire ?',
        'Voir les cours',
        'Comment payer ?',
        'Mot de passe oublié'
    ];
    
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
    
    function init() {
        toggleBtn.addEventListener('click', toggleChat);
        closeBtn.addEventListener('click', closeChat);
        
        sendBtn.addEventListener('click', sendMessage);
        inputField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        renderSuggestions();
        
        loadHistory();
    }
    
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
        
        if (badge) {
            badge.style.display = 'none';
        }
        
        if (isFirstOpen) {
            setTimeout(() => {
                addBotMessage(`Bonjour ! Je suis l'assistant **DataEcon.Ci**.

Je peux vous aider sur :
• Inscription et connexion
• Cours et formations
• Abonnements et paiement
• Données et modèles

Comment puis-je vous aider ?`);
                isFirstOpen = false;
            }, 300);
        }
        
        setTimeout(() => inputField.focus(), 400);
    }
    
    function closeChat() {
        isOpen = false;
        chatWindow.classList.remove('active');
        toggleBtn.classList.remove('active');
        toggleBtn.innerHTML = '<i class="fas fa-comments"></i>';
    }
    
    function sendMessage() {
        const message = inputField.value.trim();
        if (!message) return;
        
        addUserMessage(message);
        inputField.value = '';
        
        sendBtn.disabled = true;
        
        showTyping();
        
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
                <i class="fas fa-headset"></i>
            </div>
            <div class="chatbot-message-content">
                ${formattedText}
                ${whatsappBtn}
            </div>
        `;
        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }
    
    function showTyping() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chatbot-message bot';
        typingDiv.id = 'chatbotTyping';
        typingDiv.innerHTML = `
            <div class="chatbot-message-avatar">
                <i class="fas fa-headset"></i>
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
    
    function loadHistory() {
        const history = localStorage.getItem('chatbot_history');
        if (history) {
            try {
                const messages = JSON.parse(history);
                messages.slice(-3).forEach(msg => {
                });
            } catch (e) {
                console.error('Erreur chargement historique:', e);
            }
        }
    }
    
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
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
})();