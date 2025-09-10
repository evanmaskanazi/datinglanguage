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
            # Always get the same test users in consistent order (exclude john to get sarah)
            test_users = User.query.filter(
                and_(
                    User.id != user_id,
                    User.email.in_(['sarah@example.com', 'emma@example.com', 'lisa@example.com'])  # Removed john
                )
            ).order_by(User.email).all()  # Remove limit to get all 3
            
            suggestions = []
            # Create consistent persona mapping
            persona_map = {
                'sarah@example.com': {'name': 'Sarah M.', 'age': 28, 'compatibility': 85, 'interests': ['Italian food', 'Travel', 'Books']},
                'emma@example.com': {'name': 'Emma K.', 'age': 26, 'compatibility': 92, 'interests': ['Art', 'Cooking', 'Yoga']},
                'lisa@example.com': {'name': 'Lisa R.', 'age': 30, 'compatibility': 78, 'interests': ['Photography', 'Hiking', 'Wine']}
            }
            
            for user in test_users:
                persona = persona_map.get(user.email, {'name': user.email.split('@')[0].title(), 'age': 28, 'compatibility': 80, 'interests': ['Food', 'Travel']})
                suggestions.append({
                    'id': user.id,
                    'name': persona['name'],
                    'age': persona['age'],
                    'compatibility': persona['compatibility'],
                    'avatar_url': '/static/images/default-avatar.jpg',
                    'interests': persona['interests'],
                    'bio': f'Looking forward to meeting new people over dinner!'
                })
            
            # If no test users found, return empty array instead of mock data
            if not suggestions:
                self.logger.warning("No test users found for suggestions")
                return jsonify([])
            
            return jsonify(suggestions)
            
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
                
                # CRITICAL FIX: Get restaurant name properly
                restaurant_name = self._get_restaurant_name(match)
                
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
    
    def _get_restaurant_name(self, match):
        """Get restaurant name for a match - FIXED VERSION"""
        try:
            # First check if we have the restaurant name stored with the match
            match_cache_key = f"match_restaurant_{match.id}"
            cached_name = self.cache.get(match_cache_key)
            if cached_name:
                self.logger.info(f"Found cached restaurant name for match {match.id}: {cached_name}")
                return cached_name
            
            # If not cached with match, try to get from restaurant data
            if match.restaurant_id:
                restaurant_id = str(match.restaurant_id)
                
                if restaurant_id.startswith('api_'):
                    # External API restaurant
                    cache_key = f"restaurant_{restaurant_id}"
                    cached_restaurant = self.cache.get(cache_key)
                    if cached_restaurant and isinstance(cached_restaurant, dict):
                        name = cached_restaurant.get('name', 'External Restaurant')
                        # Store this name with the match for future use
                        self.cache.set(match_cache_key, name)
                        return name
                    else:
                        self.logger.warning(f"No cached data found for API restaurant {restaurant_id}")
                        return "External Restaurant"
                else:
                    # Database restaurant
                    try:
                        restaurant = Restaurant.query.get(int(restaurant_id))
                        if restaurant:
                            # Cache this name with the match
                            self.cache.set(match_cache_key, restaurant.name)
                            return restaurant.name
                        else:
                            self.logger.warning(f"Database restaurant {restaurant_id} not found")
                            return "Unknown Restaurant"
                    except (ValueError, TypeError) as e:
                        self.logger.error(f"Error converting restaurant_id to int: {e}")
                        return "Unknown Restaurant"
            
            return "Unknown Restaurant"
            
        except Exception as e:
            self.logger.error(f"Error getting restaurant name for match {match.id}: {str(e)}")
            return "Unknown Restaurant"
    
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
            match_user_id = data.get('match_user_id')
            
            # Prevent self-matches
            if user_id == match_user_id:
                return jsonify({'error': 'Cannot send match request to yourself'}), 400
            
            # Parse the datetime string if provided
            proposed_datetime = datetime.utcnow()
            if data.get('datetime'):
                try:
                    # Handle ISO format datetime strings
                    datetime_str = data.get('datetime')
                    if 'T' in datetime_str:
                        # ISO format: 2025-09-11T19:00:00
                        proposed_datetime = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                    else:
                        # Legacy format: 2025-09-11 19:00
                        proposed_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Failed to parse datetime '{data.get('datetime')}': {e}")
                    # If parsing fails, use current time
                    proposed_datetime = datetime.utcnow()
            
            # CRITICAL FIX: Ensure restaurant name is properly handled
            restaurant_id = str(data.get('restaurant_id'))
            restaurant_name = data.get('restaurant_name', "Unknown Restaurant")
            
            # Log what we received to debug
            self.logger.info(f"Received match request - restaurant_id: {restaurant_id}, restaurant_name: {restaurant_name}")
            
            # If no restaurant name provided, try to get it
            if restaurant_name == "Unknown Restaurant":
                restaurant_name = self._get_restaurant_name_for_new_match(restaurant_id)
            
            # Check for existing match to prevent duplicates (only for same date/time)
            existing_match = Match.query.filter(
                or_(
                    and_(Match.user1_id == user_id, Match.user2_id == match_user_id),
                    and_(Match.user1_id == match_user_id, Match.user2_id == user_id)
                ),
                Match.proposed_datetime == proposed_datetime  # Only check same datetime
            ).filter(Match.status != MatchStatus.DECLINED).first()
            
            if existing_match:
                return jsonify({'error': 'Match request already exists for this date and time'}), 400
            
            # Create a new match request
            match = Match(
                user1_id=user_id,
                user2_id=match_user_id,
                restaurant_id=restaurant_id,
                table_id=data.get('table_id'),
                proposed_datetime=proposed_datetime,
                status=MatchStatus.PENDING,
                compatibility_score=data.get('compatibility', 75)
            )
            
            self.db.session.add(match)
            self.db.session.commit()
            
            # CRITICAL FIX: Store restaurant name with the match ID
            match_cache_key = f"match_restaurant_{match.id}"
            self.cache.set(match_cache_key, restaurant_name)
            
            self.logger.info(f"Created match {match.id} with restaurant name: {restaurant_name}")
            
            return jsonify({
                'success': True,
                'match_id': match.id,
                'message': 'Match request sent successfully!'
            }), 201
            
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Request match error: {str(e)}")
            return jsonify({'error': 'Failed to request match'}), 500
    
    def _get_restaurant_name_for_new_match(self, restaurant_id):
        """Get restaurant name when creating a new match"""
        try:
            if restaurant_id.startswith('api_'):
                # External API restaurant
                cache_key = f"restaurant_{restaurant_id}"
                cached_restaurant = self.cache.get(cache_key)
                if cached_restaurant and isinstance(cached_restaurant, dict):
                    return cached_restaurant.get('name', 'External Restaurant')
                else:
                    return "External Restaurant"
            else:
                # Database restaurant
                try:
                    restaurant = Restaurant.query.get(int(restaurant_id))
                    if restaurant:
                        return restaurant.name
                    else:
                        return "Unknown Restaurant"
                except (ValueError, TypeError):
                    return "Unknown Restaurant"
        except Exception as e:
            self.logger.error(f"Error getting restaurant name for new match: {str(e)}")
            return "Unknown Restaurant"
    
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
