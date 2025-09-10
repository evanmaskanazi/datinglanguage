from datetime import datetime, timedelta
from flask import jsonify
from sqlalchemy import and_, or_
from models.user import User
from models.match import Match, MatchStatus
from models.profile import UserProfile, UserPreferences
from models.restaurant import Restaurant, RestaurantTable
from models.reservation import Reservation

class MatchingService:
    def __init__(self, db, cache, logger):
        self.db = db
        self.cache = cache
        self.logger = logger
    
    def get_suggestions(self, user_id, data):
        """Get suggested matches for a time slot"""
        try:
            # Generate mock matches for now since we don't have real users
            mock_matches = [
                {
                    'id': 1,
                    'name': 'Sarah M.',
                    'age': 28,
                    'compatibility': 85,
                    'avatar_url': '/static/images/default-avatar.jpg',
                    'interests': ['Italian food', 'Travel', 'Books'],
                    'bio': 'Love trying new restaurants and exploring the city!'
                },
                {
                    'id': 2,
                    'name': 'Emma K.',
                    'age': 26,
                    'compatibility': 92,
                    'avatar_url': '/static/images/default-avatar.jpg',
                    'interests': ['Art', 'Cooking', 'Yoga'],
                    'bio': 'Foodie and art enthusiast looking for dinner conversations.'
                },
                {
                    'id': 3,
                    'name': 'Lisa R.',
                    'age': 30,
                    'compatibility': 78,
                    'avatar_url': '/static/images/default-avatar.jpg',
                    'interests': ['Photography', 'Hiking', 'Wine'],
                    'bio': 'Wine lover who enjoys great company and good food.'
                }
            ]
            
            return jsonify(mock_matches)
            
        except Exception as e:
            self.logger.error(f"Get suggestions error: {str(e)}")
            return jsonify({'error': 'Failed to get suggestions'}), 500
    
    def get_user_matches(self, user_id):
        """Get user's matches"""
        try:
            matches = Match.query.filter(
                or_(Match.user1_id == user_id, Match.user2_id == user_id)
            ).order_by(Match.created_at.desc()).all()
            
            result = []
            for match in matches:
                # Determine the other user
                other_user_id = match.user2_id if match.user1_id == user_id else match.user1_id
                other_user = User.query.get(other_user_id)
                
                # Get restaurant info (handle both DB and API restaurants)
                restaurant_name = "Unknown Restaurant"
                if match.restaurant_id:
                    if str(match.restaurant_id).startswith('api_'):
                        # For API restaurants, we'll need to store the name separately or fetch it
                        # For now, use a placeholder
                        restaurant_name = "API Restaurant"
                    else:
                        try:
                            restaurant = Restaurant.query.get(int(match.restaurant_id))
                            if restaurant:
                                restaurant_name = restaurant.name
                        except (ValueError, TypeError):
                            pass
                
                if other_user:
                    # Convert status to string if it's an enum
                    status_str = match.status.value if hasattr(match.status, 'value') else str(match.status)
                    
                    result.append({
                        'id': match.id,
                        'user_id': other_user.id,
                        'name': other_user.email.split('@')[0],  # Use email prefix as name
                        'status': status_str,
                        'restaurant_name': restaurant_name,
                        'restaurant_id': match.restaurant_id,
                        'date': match.proposed_datetime.isoformat() if match.proposed_datetime else None,
                        'compatibility_score': match.compatibility_score or 0,
                        'avatar_url': '/static/images/default-avatar.jpg'
                    })
            
            return jsonify(result)
            
        except Exception as e:
            self.logger.error(f"Get user matches error: {str(e)}")
            return jsonify({'error': 'Failed to get matches'}), 500
    
    def browse_matches(self, user_id, params):
        """Browse potential matches for available tables"""
        try:
            # For now, return empty array - this would be implemented with real user data
            return jsonify([])
            
        except Exception as e:
            self.logger.error(f"Browse matches error: {str(e)}")
            return jsonify({'error': 'Failed to browse matches'}), 500
    
    def request_match(self, user_id, data):
        """Request a match with another user"""
        try:
            # Parse the datetime string if provided
            proposed_datetime = datetime.utcnow()
            if data.get('datetime'):
                try:
                    proposed_datetime = datetime.fromisoformat(data.get('datetime').replace('Z', '+00:00'))
                except ValueError:
                    # If parsing fails, use current time
                    proposed_datetime = datetime.utcnow()
            
            # Create a new match request
            match = Match(
                user1_id=user_id,
                user2_id=data.get('match_user_id'),
                restaurant_id=str(data.get('restaurant_id')),  # Convert to string to handle both types
                table_id=data.get('table_id'),
                proposed_datetime=proposed_datetime,
                status=MatchStatus.PENDING,
                compatibility_score=data.get('compatibility', 75)
            )
            
            self.db.session.add(match)
            self.db.session.commit()
            
            return jsonify({
                'success': True,
                'match_id': match.id,
                'message': 'Match request sent successfully!'
            }), 201
            
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Request match error: {str(e)}")
            return jsonify({'error': 'Failed to request match'}), 500
    
    def respond_to_match(self, user_id, match_id, response_data):
        """Accept or decline a match"""
        try:
            match = Match.query.get(match_id)
            if not match:
                return jsonify({'error': 'Match not found'}), 404
            
            # Verify user is part of this match
            if user_id not in [match.user1_id, match.user2_id]:
                return jsonify({'error': 'Unauthorized'}), 403
            
            if response_data.get('accept'):
                match.status = MatchStatus.ACCEPTED
                message = 'Match accepted!'
                
                # TODO: Create reservation when match is accepted
                # reservation = Reservation(
                #     user1_id=match.user1_id,
                #     user2_id=match.user2_id,
                #     restaurant_id=match.restaurant_id,
                #     table_id=match.table_id,
                #     reservation_datetime=match.proposed_datetime,
                #     status='confirmed'
                # )
                # self.db.session.add(reservation)
                
            else:
                match.status = MatchStatus.DECLINED
                message = 'Match declined'
            
            match.responded_at = datetime.utcnow()
            self.db.session.commit()
            
            return jsonify({
                'success': True,
                'message': message
            })
            
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Respond to match error: {str(e)}")
            return jsonify({'error': 'Failed to respond to match'}), 500
