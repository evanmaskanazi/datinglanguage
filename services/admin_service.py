from flask import jsonify
from models.restaurant import Restaurant, db

class AdminService:
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
    
    def add_restaurant(self, data):
        """Add new restaurant partner"""
        try:
            restaurant = Restaurant(
                name=data.get('name'),
                cuisine_type=data.get('cuisine_type'),
                address=data.get('address'),
                price_range=data.get('price_range'),
                ambiance=data.get('ambiance')
            )
            
            self.db.session.add(restaurant)
            self.db.session.commit()
            
            return jsonify({
                'success': True,
                'restaurant': restaurant.to_dict()
            }), 201
            
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Add restaurant error: {str(e)}")
            return jsonify({'error': 'Failed to add restaurant'}), 500
