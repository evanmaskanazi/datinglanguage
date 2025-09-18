// i18n.js - Internationalization support for TableForTwo
(function() {
    'use strict';
    
    // Translation dictionaries
    const translations = {
        en: {
            nav: {
                overview: 'Overview',
                browse: 'Browse Tables',
                matches: 'My Matches',
                dates: 'Upcoming Dates',
                desired_times: 'Desired Times',
                history: 'Date History',
                profile: 'Profile',
                restaurants: 'Restaurants',
                settings: 'Settings',
                logout: 'Logout'
            }
        },
        he: {
            nav: {
                overview: 'סקירה כללית',
                browse: 'דפדוף שולחנות',
                matches: 'ההתאמות שלי',
                dates: 'פגישות קרובות',
                desired_times: 'זמנים רצויים',
                history: 'היסטוריית פגישות',
                profile: 'פרופיל',
                restaurants: 'מסעדות',
                settings: 'הגדרות',
                logout: 'יציאה'
            }
        },
        ar: {
            nav: {
                overview: 'نظرة عامة',
                browse: 'تصفح الطاولات',
                matches: 'مبارياتي',
                dates: 'المواعيد القادمة',
                desired_times: 'الأوقات المرغوبة',
                history: 'سجل المواعيد',
                profile: 'الملف الشخصي',
                restaurants: 'المطاعم',
                settings: 'الإعدادات',
                logout: 'تسجيل خروج'
            }
        },
        ru: {
            nav: {
                overview: 'Обзор',
                browse: 'Просмотр столиков',
                matches: 'Мои совпадения',
                dates: 'Предстоящие свидания',
                desired_times: 'Желаемое время',
                history: 'История свиданий',
                profile: 'Профиль',
                restaurants: 'Рестораны',
                settings: 'Настройки',
                logout: 'Выход'
            }
        }
    };
    
    // i18n object
    window.i18n = {
        currentLang: localStorage.getItem('userLanguage') || 'en',
        translations: translations,
        
        init: function() {
            console.log('i18n initializing with language:', this.currentLang);
            this.createLanguageSwitcher();
            this.applyLanguage();
            this.translatePage();
        },
        
        createLanguageSwitcher: function() {
            // Check if switcher already exists
            if (document.querySelector('.language-switcher')) {
                console.log('Language switcher already exists');
                return;
            }
            
            const switcher = document.createElement('div');
            switcher.className = 'language-switcher';
            switcher.style.cssText = `
                position: fixed;
                top: 2rem;
                right: 2rem;
                z-index: 1000;
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                padding: 0.5rem;
                display: flex;
                gap: 0.5rem;
            `;
            
            const languages = [
                { code: 'en', label: 'EN' },
                { code: 'he', label: 'HE' },
                { code: 'ar', label: 'AR' },
                { code: 'ru', label: 'RU' }
            ];
            
            languages.forEach(lang => {
                const btn = document.createElement('button');
                btn.className = 'lang-btn';
                btn.textContent = lang.label;
                if (lang.code === this.currentLang) {
                    btn.classList.add('active');
                }
                btn.style.cssText = `
                    padding: 0.5rem 1rem;
                    border: none;
                    background: ${lang.code === this.currentLang ? '#FF6B6B' : 'transparent'};
                    color: ${lang.code === this.currentLang ? 'white' : '#2D3436'};
                    cursor: pointer;
                    border-radius: 8px;
                    font-weight: 500;
                    transition: all 0.3s;
                `;
                
                btn.onmouseover = function() {
                    if (!this.classList.contains('active')) {
                        this.style.background = '#F8F9FA';
                    }
                };
                
                btn.onmouseout = function() {
                    if (!this.classList.contains('active')) {
                        this.style.background = 'transparent';
                    }
                };
                
                btn.onclick = () => this.changeLanguage(lang.code);
                switcher.appendChild(btn);
            });
            
            document.body.appendChild(switcher);
            console.log('Language switcher created');
        },
        
        changeLanguage: function(lang) {
            console.log('Changing language to:', lang);
            this.currentLang = lang;
            localStorage.setItem('userLanguage', lang);
            
            // Update active button styling
            document.querySelectorAll('.lang-btn').forEach((btn, index) => {
                const isActive = (
                    (lang === 'en' && btn.textContent === 'EN') ||
                    (lang === 'he' && btn.textContent === 'HE') ||
                    (lang === 'ar' && btn.textContent === 'AR') ||
                    (lang === 'ru' && btn.textContent === 'RU')
                );
                
                if (isActive) {
                    btn.classList.add('active');
                    btn.style.background = '#FF6B6B';
                    btn.style.color = 'white';
                } else {
                    btn.classList.remove('active');
                    btn.style.background = 'transparent';
                    btn.style.color = '#2D3436';
                }
            });
            
            this.applyLanguage();
            this.translatePage();
            
            // Dispatch event for other scripts to listen to
            window.dispatchEvent(new CustomEvent('languageChanged', {
                detail: { language: lang }
            }));
        },
        
        applyLanguage: function() {
            // Apply RTL for Hebrew and Arabic
            if (this.currentLang === 'he' || this.currentLang === 'ar') {
                document.body.classList.add('rtl');
                document.body.style.direction = 'rtl';
                
                // Move language switcher to left for RTL
                const switcher = document.querySelector('.language-switcher');
                if (switcher) {
                    switcher.style.right = 'auto';
                    switcher.style.left = '2rem';
                }
            } else {
                document.body.classList.remove('rtl');
                document.body.style.direction = 'ltr';
                
                // Move language switcher back to right for LTR
                const switcher = document.querySelector('.language-switcher');
                if (switcher) {
                    switcher.style.left = 'auto';
                    switcher.style.right = '2rem';
                }
            }
        },
        
        translatePage: function() {
            // Translate elements with data-translate attribute
            document.querySelectorAll('[data-translate]').forEach(element => {
                const keys = element.getAttribute('data-translate').split('.');
                let translation = this.translations[this.currentLang];
                
                for (const key of keys) {
                    if (translation && translation[key]) {
                        translation = translation[key];
                    }
                }
                
                if (typeof translation === 'string') {
                    element.textContent = translation;
                }
            });
        },
        
        // Helper function to get translation
        t: function(key) {
            const keys = key.split('.');
            let translation = this.translations[this.currentLang];
            
            for (const k of keys) {
                if (translation && translation[k]) {
                    translation = translation[k];
                } else {
                    return key; // Return key if translation not found
                }
            }
            
            return translation;
        }
    };
    
    // Initialize when DOM is ready
   // Initialize when DOM is ready
    if (document.readyState === 'complete') {
        // Page fully loaded, initialize immediately
        window.i18n.init();
    } else if (document.readyState === 'interactive') {
        // DOM ready but resources still loading
        setTimeout(() => window.i18n.init(), 0);
    } else {
        // Wait for DOM
        document.addEventListener('DOMContentLoaded', () => {
            window.i18n.init();
        });
    }
})();
