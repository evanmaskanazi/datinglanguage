// ConveyThis Configuration
window.conveyThisConfig = {
    api_key: "pub_b4f4ddeec8a41da8ad98b4b8c5f1e0ad",
    source_language: "en",
    target_languages: ["he", "ar", "ru"],
    display_mode: "dropdown",
    switcher_active: true,
    position_switcher: "top-right",
    custom_switcher: true,
    switcher_text_color: "#2c3e50",
    switcher_background_color: "#ffffff",
    switcher_border_color: "#e74c3c",
    auto_switch: false,
    translate_mode: "live",
    cache: true
};

// Initialize ConveyThis when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (window.ConveyThis) {
        window.ConveyThis.init(window.conveyThisConfig);
    }
});

// Handle language switching for restaurant data
function handleRestaurantTranslation() {
    // Mark restaurant content for translation
    const restaurantCards = document.querySelectorAll('.restaurant-card');
    restaurantCards.forEach(card => {
        card.setAttribute('data-translate', 'yes');
    });
    
    // Mark Yelp data for translation
    const restaurantNames = document.querySelectorAll('.restaurant-name');
    restaurantNames.forEach(name => {
        name.setAttribute('data-translate', 'yes');
    });
    
    const restaurantDetails = document.querySelectorAll('.restaurant-details');
    restaurantDetails.forEach(detail => {
        detail.setAttribute('data-translate', 'yes');
    });
}

// Call after restaurant data loads
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(handleRestaurantTranslation, 1000);
});
