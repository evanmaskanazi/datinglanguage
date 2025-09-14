"""
Service for handling user time preferences
"""
from flask import jsonify
from datetime import datetime, date, timedelta
from ..models.time_preference import UserTimePreference
from ..models.user import User
from .. import db, cache

class TimePreferenceService:
    def __init__(self, db_session, cache_manager, logger):
        self.db = db_session
        self.cache = cache_manager
        self.logger = logger
    
    def add_time_preference(self, user_id, preference_data):
        """Add a time preference for a user"""
        try:
            # Validate input
            required_fields = ['date', 'time']
            for field in required_fields:
                if field not in preference_data:
                    return jsonify({'error': f'{field} is required'}), 400
            
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Check if user already has 10 preferences (limit)
            current_count = UserTimePreference.query.filter_by(
                user_id=user_id, is_active=True
            ).count()
            
            if current_count >= 10:
                return jsonify({'error': 'Maximum 10 time preferences allowed'}), 400
            
            # Parse date and time
            pref_date = datetime.strptime(preference_data['date'], '%Y-%m-%d').date()
            pref_time = datetime.strptime(preference_data['time'], '%H:%M').time()
            
            # Check if preference already exists
            existing = UserTimePreference.query.filter_by(
                user_id=user_id,
                date=pref_date,
                time=pref_time,
                is_active=True
            ).first()
            
            if existing:
                return jsonify({'error': 'Time preference already exists'}), 400
            
            # Create new preference
            preference = UserTimePreference(
                user_id=user_id,
                date=pref_date,
                time=pref_time,
                restaurant_id=preference_data.get('restaurant_id'),
                is_active=True
            )
            
            self.db.session.add(preference)
            self.db.session.commit()
            
            # Clear cache
            self.cache.delete(f"user_time_preferences_{user_id}")
            
            self.logger.info(f"User {user_id} added time preference: {pref_date} {pref_time}")
            return jsonify({
                'message': 'Time preference added',
                'id': preference.id
            }), 201
            
        except ValueError as e:
            return jsonify({'error': 'Invalid date/time format'}), 400
        except Exception as e:
            self.logger.error(f"Add time preference error: {str(e)}")
            self.db.session.rollback()
            return jsonify({'error': 'Failed to add time preference'}), 500
    
    def get_user_preferences(self, user_id, include_matches=False):
        """Get user's time preferences"""
        try:
            cache_key = f"user_time_preferences_{user_id}"
            cached = self.cache.get(cache_key)
            if cached and not include_matches:
                return jsonify(cached)
            
            preferences = UserTimePreference.get_user_preferences(user_id)
            
            result = []
            for pref in preferences:
                pref_data = {
                    'id': pref.id,
                    'date': pref.date.isoformat(),
                    'time': pref.time.strftime('%H:%M'),
                    'restaurant_id': pref.restaurant_id,
                    'created_at': pref.created_at.isoformat()
                }
                
                if include_matches:
                    # Find other users with matching preferences
                    matching_users = UserTimePreference.query.filter_by(
                        date=pref.date,
                        time=pref.time,
                        is_active=True
                    ).filter(UserTimePreference.user_id != user_id).all()
                    
                    pref_data['potential_matches'] = len(matching_users)
                    pref_data['matching_users'] = [
                        {'id': mu.user_id, 'email': mu.user.email} 
                        for mu in matching_users[:5]  # Limit to 5 for preview
                    ]
                
                result.append(pref_data)
            
            if not include_matches:
                self.cache.set(cache_key, result, timeout=300)
            
            return jsonify(result)
            
        except Exception as e:
            self.logger.error(f"Get preferences error: {str(e)}")
            return jsonify({'error': 'Failed to get preferences'}), 500
    
    def remove_time_preference(self, user_id, preference_id):
        """Remove a time preference"""
        try:
            preference = UserTimePreference.query.filter_by(
                id=preference_id,
                user_id=user_id
            ).first()
            
            if not preference:
                return jsonify({'error': 'Time preference not found'}), 404
            
            preference.is_active = False
            self.db.session.commit()
            
            # Clear cache
            self.cache.delete(f"user_time_preferences_{user_id}")
            
            return jsonify({'message': 'Time preference removed'}), 200
            
        except Exception as e:
            self.logger.error(f"Remove preference error: {str(e)}")
            self.db.session.rollback()
            return jsonify({'error': 'Failed to remove preference'}), 500
    
    def get_matching_users(self, user_id):
        """Get users with matching time preferences"""
        try:
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Get users this user is following
            following_ids = [u.id for u in user.following]
            
            if not following_ids:
                return jsonify([])  # No one to match with
            
            matching_data = []
            user_preferences = UserTimePreference.get_user_preferences(user_id)
            
            for pref in user_preferences:
                matches = UserTimePreference.query.filter_by(
                    date=pref.date,
                    time=pref.time,
                    is_active=True
                ).filter(UserTimePreference.user_id.in_(following_ids)).all()
                
                for match in matches:
                    matching_data.append({
                        'user_id': match.user_id,
                        'email': match.user.email,
                        'date': pref.date.isoformat(),
                        'time': pref.time.strftime('%H:%M'),
                        'restaurant_id': pref.restaurant_id,
                        'compatibility_boost': user.get_compatibility_boost(match.user)
                    })
            
            return jsonify(matching_data)
            
        except Exception as e:
            self.logger.error(f"Get matching users error: {str(e)}")
            return jsonify({'error': 'Failed to get matching users'}), 500
