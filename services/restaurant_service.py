from flask import jsonify
from models.restaurant import Restaurant, RestaurantTable
from datetime import datetime

class RestaurantService:
    def __init__(self, db, cache, logger):
        self.db = db
        self.cache = cache
        self.logger = logger

    def get_restaurant(self, restaurant_id):
        """Get restaurant details by ID"""
        try:
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant or not restaurant.is_active:
                return jsonify({'error': 'Restaurant not found'}), 404
        
            # Get available tables count
            available_tables = RestaurantTable.query.filter_by(
                restaurant_id=restaurant_id,
                is_available=True
            ).count()
        
            result = restaurant.to_dict()
            result['available_tables'] = available_tables
        
            return jsonify(result)
        
        except Exception as e:
            self.logger.error(f"Get restaurant error: {str(e)}")
            return jsonify({'error': 'Failed to get restaurant'}), 500
    
    def get_available_restaurants(self, params):
        """Get available restaurants based on filters"""
        try:
            # Check cache first
            cache_key = f"restaurants:{params.get('cuisine')}:{params.get('price_range')}"
            cached = self.cache.get(cache_key)
            if cached:
                return jsonify(cached)
            
            # Build query
            query = Restaurant.query.filter_by(is_active=True)
            
            if params.get('cuisine_type'):
                query = query.filter_by(cuisine_type=params['cuisine_type'])
            
            if params.get('price_range'):
                query = query.filter_by(price_range=int(params['price_range']))
            
            if params.get('ambiance'):
                query = query.filter_by(ambiance=params['ambiance'])
            
            # Execute query
            restaurants = query.all()
            
            result = {
                'success': True,
                'restaurants': [r.to_dict() for r in restaurants],
                'total': len(restaurants)
            }
            
            # Cache for 5 minutes
            self.cache.set(cache_key, result, 300)
            
            return jsonify(result)
            
        except Exception as e:
            self.logger.error(f"Get restaurants error: {str(e)}")
            return jsonify({'error': 'Failed to get restaurants'}), 500
    
    def get_available_tables(self, restaurant_id, params):
        """Get available tables for a restaurant"""
        try:
            date_str = params.get('date')
            time_slot = params.get('time_slot')
            
            if not date_str or not time_slot:
                return jsonify({'error': 'Date and time slot required'}), 400
            
            # Get restaurant
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant or not restaurant.is_active:
                return jsonify({'error': 'Restaurant not found'}), 404
            
            # Get available tables
            tables = RestaurantTable.query.filter_by(
                restaurant_id=restaurant_id,
                is_available=True
            ).all()
            
            return jsonify({
                'success': True,
                'restaurant': restaurant.to_dict(),
                'tables': [t.to_dict() for t in tables],
                'date': date_str,
                'time_slot': time_slot
            })
            
        except Exception as e:
            self.logger.error(f"Get tables error: {str(e)}")
            return jsonify({'error': 'Failed to get tables'}), 500

    def get_available_slots(self, restaurant_id, params):
        """Get available time slots for a restaurant"""
        try:
            date_str = params.get('date')
            
            if not date_str:
                return jsonify({'error': 'Date required'}), 400
            
            # Get restaurant
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant or not restaurant.is_active:
                return jsonify({'error': 'Restaurant not found'}), 404
            
            # Generate time slots (simplified version)
            time_slots = [
                {'time': '12:00', 'available': True},
                {'time': '12:30', 'available': True},
                {'time': '13:00', 'available': False},
                {'time': '13:30', 'available': True},
                {'time': '18:00', 'available': True},
                {'time': '18:30', 'available': True},
                {'time': '19:00', 'available': True},
                {'time': '19:30', 'available': False},
                {'time': '20:00', 'available': True},
                {'time': '20:30', 'available': True}
            ]
            
            return jsonify(time_slots)
            
        except Exception as e:
            self.logger.error(f"Get slots error: {str(e)}")
            return jsonify({'error': 'Failed to get time slots'}), 500
