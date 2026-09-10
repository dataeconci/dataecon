// ============================================
// DataEcon.Ci - Scripts principaux
// ============================================

document.addEventListener('DOMContentLoaded', function() {

    // ========================================
    // 1. AUTO-DISMISS DES ALERTES
    // ========================================
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, 500);
        }, 5000);
    });

    // ========================================
    // 2. SMOOTH SCROLL POUR LES ANCRES
    // ========================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // ========================================
    // 3. PREVISUALISATION DES FICHIERS UPLOAD
    // ========================================
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const fileName = this.files[0]?.name || 'Aucun fichier sélectionné';
            const fileSize = this.files[0]?.size || 0;
            
            // Afficher le nom du fichier
            const label = this.closest('.form-group')?.querySelector('.file-label') || 
                          this.nextElementSibling;
            if (label && label.classList.contains('file-label')) {
                label.textContent = fileName;
            }

            // Afficher la taille si disponible
            const sizeDisplay = this.closest('.form-group')?.querySelector('.file-size');
            if (sizeDisplay) {
                if (fileSize > 0) {
                    const sizeInKB = (fileSize / 1024).toFixed(1);
                    const sizeInMB = (fileSize / (1024 * 1024)).toFixed(1);
                    sizeDisplay.textContent = sizeInMB > 1 ? 
                        `${sizeInMB} MB` : 
                        `${sizeInKB} KB`;
                    sizeDisplay.style.display = 'block';
                } else {
                    sizeDisplay.style.display = 'none';
                }
            }
        });
    });

    // ========================================
    // 4. CONFIRMATION DE SUPPRESSION
    // ========================================
    document.querySelectorAll('.delete-confirm').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const message = this.dataset.confirmMessage || 'Êtes-vous sûr de vouloir supprimer cet élément ?';
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });

    // ========================================
    // 5. TOOLTIPS (Bootstrap 5)
    // ========================================
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // ========================================
    // 6. ANIMATION AU SCROLL (Intersection Observer)
    // ========================================
    const animateElements = document.querySelectorAll('.fade-in, .slide-up');
    
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    // Si on veut une animation unique, on peut arrêter l'observation
                    // observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        animateElements.forEach(el => {
            observer.observe(el);
        });
    } else {
        // Fallback pour les navigateurs plus anciens
        animateElements.forEach(el => {
            el.classList.add('visible');
        });
    }

    // ========================================
    // 7. VALIDATION DE FORMULAIRE EN TEMPS RÉEL
    // ========================================
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!this.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            this.classList.add('was-validated');
        });
    });

    // ========================================
    // 8. MASQUER/AFFICHER LE MOT DE PASSE
    // ========================================
    document.querySelectorAll('.toggle-password').forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.dataset.target;
            const input = document.getElementById(targetId);
            if (input) {
                const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
                input.setAttribute('type', type);
                this.textContent = type === 'password' ? '👁️' : '👁️‍🗨️';
            }
        });
    });

    // ========================================
    // 9. BARRE DE PROGRESSION DES COURS
    // ========================================
    document.querySelectorAll('.progress-simulate').forEach(container => {
        const progressBar = container.querySelector('.progress-bar');
        if (progressBar) {
            let width = parseInt(progressBar.getAttribute('data-progress')) || 0;
            const targetWidth = parseInt(progressBar.getAttribute('data-target')) || 100;
            
            if (width < targetWidth) {
                const interval = setInterval(() => {
                    width += Math.random() * 8 + 2;
                    if (width >= targetWidth) {
                        width = targetWidth;
                        clearInterval(interval);
                    }
                    progressBar.style.width = width + '%';
                    progressBar.textContent = Math.round(width) + '%';
                    progressBar.setAttribute('aria-valuenow', width);
                }, 200);
            }
        }
    });

    // ========================================
    // 10. DARK MODE TOGGLE (optionnel)
    // ========================================
    const darkModeToggle = document.querySelector('#darkModeToggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            const isDark = document.body.classList.contains('dark-mode');
            localStorage.setItem('darkMode', isDark);
            this.textContent = isDark ? '☀️' : '🌙';
        });

        // Vérifier la préférence stockée
        if (localStorage.getItem('darkMode') === 'true') {
            document.body.classList.add('dark-mode');
            darkModeToggle.textContent = '☀️';
        }
    }

    // ========================================
    // 11. COPY TO CLIPBOARD
    // ========================================
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.dataset.target;
            const target = document.getElementById(targetId);
            if (target) {
                const text = target.textContent || target.value;
                navigator.clipboard.writeText(text).then(() => {
                    const originalText = this.textContent;
                    this.textContent = '✅ Copié !';
                    setTimeout(() => {
                        this.textContent = originalText;
                    }, 2000);
                }).catch(() => {
                    // Fallback
                    const range = document.createRange();
                    range.selectNode(target);
                    window.getSelection().removeAllRanges();
                    window.getSelection().addRange(range);
                    document.execCommand('copy');
                });
            }
        });
    });

    // ========================================
    // 12. GESTION DES TABS PERSISTANTS
    // ========================================
    const activeTab = localStorage.getItem('activeTab');
    if (activeTab) {
        const tab = document.querySelector(`[data-bs-target="${activeTab}"]`);
        if (tab) {
            const tabInstance = new bootstrap.Tab(tab);
            tabInstance.show();
        }
    }

    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(e) {
            localStorage.setItem('activeTab', this.getAttribute('data-bs-target'));
        });
    });

    // ========================================
    // 13. DATE HEURE EN TEMPS RÉEL (si présent)
    // ========================================
    const clockElement = document.querySelector('#live-clock');
    if (clockElement) {
        function updateClock() {
            const now = new Date();
            const options = {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            };
            clockElement.textContent = now.toLocaleDateString('fr-FR', options);
        }
        updateClock();
        setInterval(updateClock, 1000);
    }

    // ========================================
    // 14. SCROLL TO TOP BUTTON
    // ========================================
    const scrollTopBtn = document.querySelector('#scrollTopBtn');
    if (scrollTopBtn) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 300) {
                scrollTopBtn.style.display = 'block';
                scrollTopBtn.style.opacity = '1';
            } else {
                scrollTopBtn.style.opacity = '0';
                setTimeout(() => {
                    if (window.scrollY <= 300) {
                        scrollTopBtn.style.display = 'none';
                    }
                }, 300);
            }
        });

        scrollTopBtn.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // ========================================
    // 15. CHART.JS INITIALIZATION (si présent)
    // ========================================
    if (typeof Chart !== 'undefined') {
        document.querySelectorAll('.chart-canvas').forEach(canvas => {
            const chartType = canvas.dataset.chartType || 'line';
            const chartData = canvas.dataset.chartData ? JSON.parse(canvas.dataset.chartData) : {};
            const chartOptions = canvas.dataset.chartOptions ? JSON.parse(canvas.dataset.chartOptions) : {};
            
            try {
                new Chart(canvas, {
                    type: chartType,
                    data: chartData,
                    options: chartOptions
                });
            } catch (e) {
                console.warn('Chart initialization error:', e);
            }
        });
    }

    console.log('🚀 DataEcon.Ci - Application chargée avec succès !');
});