// Fallback translation for browsers without ConveyThis support
const fallbackTranslations = {
    he: {
        "Table for Two": "שולחן לשניים",
        "Real Dates. Real People. Real Connections.": "דייטים אמיתיים. אנשים אמיתיים. קשרים אמיתיים.",
        "Login": "התחברות", 
        "Sign Up": "הרשמה",
        "Browse Tables": "עיון בשולחנות",
        "My Matches": "ההתאמות שלי",
        "Upcoming Dates": "דייטים קרובים",
        "Restaurant": "מסעדה",
        "Date": "תאריך",
        "Time": "זמן"
    },
    ar: {
        "Table for Two": "طاولة لاثنين",
        "Real Dates. Real People. Real Connections.": "مواعيد حقيقية. أشخاص حقيقيون. روابط حقيقية.",
        "Login": "تسجيل الدخول",
        "Sign Up": "اشتراك", 
        "Browse Tables": "تصفح الطاولات",
        "My Matches": "مطابقاتي",
        "Upcoming Dates": "المواعيد القادمة",
        "Restaurant": "مطعم",
        "Date": "التاريخ",
        "Time": "الوقت"
    },
    ru: {
        "Table for Two": "Столик на двоих",
        "Real Dates. Real People. Real Connections.": "Настоящие свидания. Настоящие люди. Настоящие связи.",
        "Login": "Вход",
        "Sign Up": "Регистрация",
        "Browse Tables": "Обзор столиков", 
        "My Matches": "Мои совпадения",
        "Upcoming Dates": "Предстоящие свидания",
        "Restaurant": "Ресторан",
        "Date": "Дата",
        "Time": "Время"
    }
};

// Simple fallback function
function applyFallbackTranslation(language) {
    if (!fallbackTranslations[language]) return;
    
    const translations = fallbackTranslations[language];
    
    Object.keys(translations).forEach(english => {
        const elements = document.querySelectorAll('*');
        elements.forEach(element => {
            if (element.textContent === english) {
                element.textContent = translations[english];
            }
        });
    });
}

// Detect if ConveyThis failed to load
setTimeout(() => {
    if (!window.ConveyThis) {
        console.log('ConveyThis not loaded, using fallback');
        // You could implement basic language switching here
    }
}, 3000);
