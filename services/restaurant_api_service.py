import requests
from flask import jsonify
import os
from datetime import datetime

class RestaurantAPIService:
    def __init__(self, logger):
        self.logger = logger
        # You'll need to sign up for these APIs and add keys to environment variables
        self.yelp_api_key = os.environ.get('YELP_API_KEY')
        self.google_places_key = os.environ.get('GOOGLE_PLACES_API_KEY')
        
    def search_restaurants_yelp(self, location, cuisine=None, price=None):
        """Search restaurants using Yelp API"""
        if not self.yelp_api_key:
            return []
            
        url = "https://api.yelp.com/v3/businesses/search"
        headers = {
            "Authorization": f"Bearer {self.yelp_api_key}"
        }
        params = {
            "location": location,
            "categories": "restaurants",
            "limit": 20,
            "radius": 5000  # 5km radius
        }
        
        if cuisine:
            params["categories"] = f"restaurants,{cuisine}"
        if price:
            params["price"] = price
            
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return self.format_yelp_restaurants(data.get('businesses', []))
            else:
                self.logger.error(f"Yelp API error: {response.status_code}")
                return []
        except Exception as e:
            self.logger.error(f"Yelp API request failed: {e}")
            return []
    
    def search_restaurants_google(self, location, cuisine=None):
        """Search restaurants using Google Places API"""
        if not self.google_places_key:
            return []
            
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        query = f"restaurants in {location}"
        if cuisine:
            query = f"{cuisine} restaurants in {location}"
            
        params = {
            "query": query,
            "type": "restaurant",
            "key": self.google_places_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return self.format_google_restaurants(data.get('results', []))
            else:
                self.logger.error(f"Google Places API error: {response.status_code}")
                return []
        except Exception as e:
            self.logger.error(f"Google Places API request failed: {e}")
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
        if 'restaurant' in types:
            return 'International'
        return 'International'
    
    def format_address(self, location):
        """Format Yelp address"""
        if not location:
            return ''
        address_parts = location.get('display_address', [])
        return ', '.join(address_parts)
