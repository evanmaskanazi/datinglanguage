import requests
from flask import jsonify
import os
from datetime import datetime

class RestaurantAPIService:
    def __init__(self, logger):
        self.logger = logger
        # FIX 1: Changed GOOGLE_PLACES_KEY to GOOGLE_PLACES_API_KEY
        self.yelp_api_key = os.environ.get('YELP_API_KEY')
        self.google_places_key = os.environ.get('GOOGLE_PLACES_API_KEY')  # FIXED!
        
    def search_restaurants_yelp(self, location, cuisine=None, price=None):
        """Search restaurants using Yelp API"""
        if not self.yelp_api_key:
            self.logger.warning("Yelp API key not found")
            return []
            
        url = "https://api.yelp.com/v3/businesses/search"
        headers = {
            "Authorization": f"Bearer {self.yelp_api_key}"
        }
        
        # FIX 2: Try multiple location formats for better coverage
        locations_to_try = [
            f"{location}, Israel",  # Add country
            location,               # Original
            f"{location}-Yafo, Israel" if "Tel Aviv" in location else location
        ]
        
        for loc in locations_to_try:
            # FIX 3: Simplified categories parameter - no concatenation
            params = {
                "location": loc,
                "categories": "restaurants",  # Keep simple, don't concatenate
                "limit": 20,
                "radius": 5000,
                "sort_by": "rating"
            }
            
            # FIX 4: Add price filter properly
            if price and price.isdigit():
                price_num = int(price)
                if 1 <= price_num <= 4:
                    params["price"] = ",".join([str(i) for i in range(1, price_num + 1)])
                
            try:
                self.logger.info(f"Trying Yelp search for location: {loc}")
                response = requests.get(url, headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    businesses = data.get('businesses', [])
                    if businesses:
                        self.logger.info(f"Yelp found {len(businesses)} restaurants for {loc}")
                        return self.format_yelp_restaurants(businesses)
                    else:
                        self.logger.warning(f"Yelp returned no businesses for {loc}")
                        continue  # Try next location
                else:
                    # FIX 5: Better error logging with actual response
                    self.logger.error(f"Yelp API error for {loc}: {response.status_code}")
                    self.logger.error(f"Yelp API response: {response.text}")
                    continue  # Try next location
                    
            except Exception as e:
                self.logger.error(f"Yelp API request failed for {loc}: {e}")
                continue  # Try next location
                
        # If all locations failed
        self.logger.warning("All Yelp location attempts failed")
        return []
    
    def search_restaurants_google(self, location, cuisine=None):
        """Search restaurants using Google Places API"""
        if not self.google_places_key:
            self.logger.warning("Google Places API key not found")
            return []
            
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        
        # FIX 6: Try multiple query formats for better results
        queries_to_try = []
        
        if cuisine:
            queries_to_try.extend([
                f"{cuisine} restaurants in {location}",
                f"{cuisine} food {location}",
                f"restaurants {location} {cuisine}"
            ])
        
        queries_to_try.extend([
            f"restaurants in {location}",
            f"dining {location}",
            f"food {location}"
        ])
        
        for query in queries_to_try:
            params = {
                "query": query,
                "type": "restaurant",
                "key": self.google_places_key,
                "fields": "place_id,name,formatted_address,rating,price_level,types"
            }
            
            try:
                self.logger.info(f"Trying Google Places search: {query}")
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'OK':
                        results = data.get('results', [])
                        if results:
                            self.logger.info(f"Google Places found {len(results)} restaurants for: {query}")
                            return self.format_google_restaurants(results)
                        else:
                            self.logger.warning(f"Google Places returned no results for: {query}")
                            continue
                    else:
                        self.logger.error(f"Google Places API status: {data.get('status')} for query: {query}")
                        continue
                else:
                    self.logger.error(f"Google Places API error: {response.status_code}")
                    self.logger.error(f"Google Places API response: {response.text}")
                    continue
                    
            except Exception as e:
                self.logger.error(f"Google Places API request failed for '{query}': {e}")
                continue
                
        self.logger.warning("All Google Places query attempts failed")
        return []
    
    def format_yelp_restaurants(self, businesses):
        """Format Yelp API response to our restaurant format"""
        restaurants = []
        for business in businesses:
            restaurant = {
                'external_id': business.get('id'),
                'name': business.get('name'),
                'cuisine_type': self.extract_cuisine(business.get('categories', [])),
                'address': self.format_address(business.get('location', {})),
                'latitude': business.get('coordinates', {}).get('latitude'),
                'longitude': business.get('coordinates', {}).get('longitude'),
                'phone': business.get('phone'),
                'website': business.get('url'),
                'price_range': len(business.get('price', '$')),
                'rating': business.get('rating', 0),
                'image_url': business.get('image_url'),
                'is_active': True,
                'source': 'yelp'
            }
            restaurants.append(restaurant)
        return restaurants
    
    def format_google_restaurants(self, places):
        """Format Google Places API response to our restaurant format"""
        restaurants = []
        for place in places:
            restaurant = {
                'external_id': place.get('place_id'),
                'name': place.get('name'),
                'cuisine_type': self.extract_cuisine_google(place.get('types', [])),
                'address': place.get('formatted_address'),
                'latitude': place.get('geometry', {}).get('location', {}).get('lat'),
                'longitude': place.get('geometry', {}).get('location', {}).get('lng'),
                'rating': place.get('rating', 0),
                'price_range': place.get('price_level', 2),
                'is_active': True,
                'source': 'google'
            }
            restaurants.append(restaurant)
        return restaurants
    
    def extract_cuisine(self, categories):
        """Extract cuisine type from Yelp categories"""
        cuisine_map = {
            'italian': 'Italian',
            'mexican': 'Mexican',
            'chinese': 'Chinese',
            'japanese': 'Japanese',
            'indian': 'Indian',
            'thai': 'Thai',
            'french': 'French',
            'mediterranean': 'Mediterranean',
            'american': 'American'
        }
        
        for category in categories:
            alias = category.get('alias', '').lower()
            if alias in cuisine_map:
                return cuisine_map[alias]
        return 'International'
    
    def extract_cuisine_google(self, types):
        """Extract cuisine type from Google Places types"""
        # FIX 7: Better cuisine extraction from Google types
        type_map = {
            'italian_restaurant': 'Italian',
            'chinese_restaurant': 'Chinese',
            'japanese_restaurant': 'Japanese',
            'mexican_restaurant': 'Mexican',
            'indian_restaurant': 'Indian',
            'thai_restaurant': 'Thai',
            'french_restaurant': 'French',
            'mediterranean_restaurant': 'Mediterranean',
            'american_restaurant': 'American'
        }
        
        for place_type in types:
            if place_type in type_map:
                return type_map[place_type]
        return 'International'
    
    def format_address(self, location):
        """Format Yelp address"""
        if not location:
            return ''
        address_parts = location.get('display_address', [])
        return ', '.join(address_parts)
