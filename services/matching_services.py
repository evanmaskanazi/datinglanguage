from datetime import datetime, timedelta
from flask import jsonify
from sqlalchemy import and_, or_
from models.user import User
from models.match import Match, MatchStatus
from models.profile import UserProfile, UserPreferences
from models.restaurant import RestaurantTable
from models.reservation import Reservation

class MatchingService:
    def __init__(self, db, cache, logger):
        self.db = db
        self.cache = cache
        self.logger = logger
    
    def get_user_matches(self, user_id):
        """Get user's matches - placeholder for now"""
        try:
            # TODO: Implement actual match retrieval logic
            return jsonify([])
        except Exception as e:
            self.logger.error(f"Get user matches error: {str(e)}")
            return jsonify({'error': 'Failed to get matches'}), 500
    
    def browse_matches(self, user_id, params):
        """Browse potential matches for available tables"""
        try:
            # Get user preferences
            user_prefs = UserPreferences.query.filter_by(user_id=user_id).first()
            if not user_prefs:
                return jsonify({'error': 'Please complete your preferences first'}), 400
            
            # Parse parameters
            date_str = params.get('date')
            time_slot = params.get('time_slot')
            restaurant_id = params.get('restaurant_id')
            
            # Get available tables
            tables_query = RestaurantTable.query.filter_by(is_available=True)
            if restaurant_id:
                tables_query = tables_query.filter_by(restaurant_id=restaurant_id)
            
            available_tables = tables_query.all()
            
            # Get potential matches based on preferences
            matches_query = self._build_matches_query(user_id, user_prefs)
            potential_matches = matches_query.limit(20).all()
            
            # Format results
            results = []
            for table in available_tables:
                table_matches = []
                for match_user in potential_matches:
                    if self._is_compatible(user_prefs, match_user):
                        table_matches.append({
                            'user_id': match_user.id,
                            'display_name': match_user.profile.display_name,
                            'age': match_user.profile.age,
                            'bio': match_user.profile.bio[:100] + '...' if match_user.profile.bio and len(match_user.profile.bio) > 100 else match_user.profile.bio or '',
                            'compatibility_score': self._calculate_compatibility(user_prefs, match_user.preferences)
                        })
                
                if table_matches:
                    results.append({
                        'table_id': table.id,
                        'restaurant': {
                            'id': table.restaurant.id,
                            'name': table.restaurant.name,
                            'cuisine': table.restaurant.cuisine_type,
                            'address': table.restaurant.address
                        },
                        'capacity': table.capacity,
                        'time_slot': time_slot,
                        'potential_matches': sorted(table_matches, key=lambda x: x['compatibility_score'], reverse=True)[:5]
                    })
            
            return jsonify({
                'success': True,
                'results': results,
                'total': len(results)
            })
            
        except Exception as e:
            self.logger.error(f"Browse matches error: {str(e)}")
            return jsonify({'error': 'Failed to browse matches'}), 500
    
    def _build_matches_query(self, user_id, user_prefs):
        """Build query for potential matches"""
        query = UserProfile.query.join(User).filter(
            User.id != user_id,
            User.is_active == True,
            User.is_verified == True
        )
        
        # Apply preference filters
        if user_prefs.min_age:
            query = query.filter(UserProfile.age >= user_prefs.min_age)
        if user_prefs.max_age:
            query = query.filter(UserProfile.age <= user_prefs.max_age)
        if user_prefs.preferred_gender:
            query = query.filter(UserProfile.gender == user_prefs.preferred_gender)
        
        return query
    
    def _is_compatible(self, user_prefs, match_user):
        """Check if two users are compatible"""
        # Check mutual preferences
        match_prefs = match_user.preferences
        if not match_prefs:
            return False
        
        # Check age preferences
        if user_prefs.min_age and match_user.profile.age < user_prefs.min_age:
            return False
        if user_prefs.max_age and match_user.profile.age > user_prefs.max_age:
            return False
        
        # Check if they match each other's preferences
        if match_prefs.preferred_gender and match_prefs.preferred_gender != user_prefs.gender:
            return False
        
        return True
    
    def _calculate_compatibility(self, prefs1, prefs2):
        """Calculate compatibility score between two users"""
        score = 50  # Base score
        
        # Add points for matching interests
        if prefs1.interests and prefs2.interests:
            common_interests = set(prefs1.interests) & set(prefs2.interests)
            score += len(common_interests) * 10
        
        # Add points for similar values
        if prefs1.values and prefs2.values:
            common_values = set(prefs1.values) & set(prefs2.values)
            score += len(common_values) * 15
        
        return min(score, 100)  # Cap at 100
