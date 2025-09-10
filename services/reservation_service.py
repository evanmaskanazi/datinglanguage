from flask import jsonify
from models.reservation import Reservation, ReservationStatus, db
from models.match import Match, MatchStatus
from datetime import datetime

class ReservationService:
    def __init__(self, db, email_manager, logger):
        self.db = db
        self.email_manager = email_manager
        self.logger = logger
    
    def create_reservation(self, user_id, data):
        """Create reservation after match confirmation"""
        try:
            match_id = data.get('match_id')
            match = Match.query.get(match_id)
            
            if not match:
                return jsonify({'error': 'Match not found'}), 404
            
            # Verify user is part of the match
            if user_id not in [match.user1_id, match.user2_id]:
                return jsonify({'error': 'Unauthorized'}), 403
            
            # Create reservation
            reservation = Reservation(
                match_id=match_id,
                table_id=match.table_id,
                date_time=match.proposed_datetime,
                special_requests=data.get('special_requests')
            )
            
            self.db.session.add(reservation)
            match.status = MatchStatus.ACCEPTED
            self.db.session.commit()
            
            # TODO: Send confirmation emails
            
            return jsonify({
                'success': True,
                'reservation': reservation.to_dict()
            }), 201
            
    # Add this method to the RestaurantService class in restaurant_service.py
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
        
        
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Create reservation error: {str(e)}")
            return jsonify({'error': 'Failed to create reservation'}), 500
