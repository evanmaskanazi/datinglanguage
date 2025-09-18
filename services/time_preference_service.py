"""Time preference service for Table for Two"""
from datetime import datetime, timedelta
from flask import jsonify
from sqlalchemy import and_, or_

# Use absolute imports
from dating_backend import db
from models.time_preference import UserTimePreference
from models.user import User


class TimePreferenceService:
    """Service for managing user time preferences"""
    
    def __init__(self, db, cache, logger):
        self.db = db
        self.cache = cache
        self.logger = logger
    
    def add_time_preference(self, user_id, data):
        """Add a new time preference for user"""
        try:
            date_str = data.get('date')
            time_str = data.get('time')
            
            if not date_str or not time_str:
                return jsonify({'error': 'Date and time are required'}), 400
            
            # Parse date
            preferred_date = datetime.fromisoformat(date_str).date()
            
            # Check if preference already exists
            existing = UserTimePreference.query.filter_by(
                user_id=user_id,
                preferred_date=preferred_date,
                preferred_time=time_str
            ).first()
            
            if existing:
                return jsonify({'error': 'This time preference already exists'}), 400
            
            # Create new preference
            preference = UserTimePreference(
                user_id=user_id,
                preferred_date=preferred_date,
                preferred_time=time_str
            )
            
            self.db.session.add(preference)
            self.db.session.commit()
            
            return jsonify({
                'success': True,
                'preference': preference.to_dict()
            }), 201
            
        except Exception as e:
            self.logger.error(f"Add time preference error: {str(e)}")
            self.db.session.rollback()
            return jsonify({'error': 'Failed to add time preference'}), 500
    
    def get_user_preferences(self, user_id, include_matches=False):
        """Get all time preferences for a user"""
        try:
            preferences = UserTimePreference.query.filter_by(
                user_id=user_id
            ).order_by(UserTimePreference.preferred_date).all()
            
            result = []
            for pref in preferences:
                pref_dict = pref.to_dict()
                
                if include_matches:
                    # Count potential matches for this time slot
                    matching_users = UserTimePreference.query.filter(
                        and_(
                            UserTimePreference.user_id != user_id,
                            UserTimePreference.preferred_date == pref.preferred_date,
                            UserTimePreference.preferred_time == pref.preferred_time
                        )
                    ).count()
                    
                    pref_dict['potential_matches'] = matching_users
                
                result.append(pref_dict)
            
            return jsonify(result), 200
            
        except Exception as e:
            self.logger.error(f"Get time preferences error: {str(e)}")
            return jsonify({'error': 'Failed to get time preferences'}), 500
    
    def remove_time_preference(self, user_id, preference_id):
        """Remove a time preference"""
        try:
            preference = UserTimePreference.query.filter_by(
                id=preference_id,
                user_id=user_id
            ).first()
            
            if not preference:
                return jsonify({'error': 'Preference not found'}), 404
            
            self.db.session.delete(preference)
            self.db.session.commit()
            
            return jsonify({'success': True, 'message': 'Preference removed'}), 200
            
        except Exception as e:
            self.logger.error(f"Remove time preference error: {str(e)}")
            self.db.session.rollback()
            return jsonify({'error': 'Failed to remove preference'}), 500
    
    def get_matching_users(self, user_id):
        """Get users with matching time preferences"""
        try:
            # Get user's preferences
            user_preferences = UserTimePreference.query.filter_by(
                user_id=user_id
            ).all()
            
            if not user_preferences:
                return jsonify({'message': 'No time preferences set'}), 200
            
            # Find matching users
            matches = []
            for pref in user_preferences:
                matching_prefs = UserTimePreference.query.filter(
                    and_(
                        UserTimePreference.user_id != user_id,
                        UserTimePreference.preferred_date == pref.preferred_date,
                        UserTimePreference.preferred_time == pref.preferred_time
                    )
                ).all()
                
                for match_pref in matching_prefs:
                    user = User.query.get(match_pref.user_id)
                    if user and user.is_active:
                        matches.append({
                            'user_id': user.id,
                            'user_name': user.email.split('@')[0],
                            'date': pref.preferred_date.isoformat(),
                            'time': pref.preferred_time
                        })
            
            return jsonify({'matches': matches}), 200
            
        except Exception as e:
            self.logger.error(f"Get matching users error: {str(e)}")
            return jsonify({'error': 'Failed to get matching users'}), 500
