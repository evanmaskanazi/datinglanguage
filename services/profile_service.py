from flask import jsonify
from models.profile import UserProfile, UserPreferences, db
from utils.security import sanitize_input

class ProfileService:
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
    
    def get_profile(self, user_id):
        """Get user profile"""
        try:
            profile = UserProfile.query.filter_by(user_id=user_id).first()
            preferences = UserPreferences.query.filter_by(user_id=user_id).first()
            
            if not profile:
                return jsonify({'error': 'Profile not found'}), 404
            
            return jsonify({
                'success': True,
                'profile': profile.to_dict(),
                'preferences': preferences.to_dict() if preferences else None
            })
            
        except Exception as e:
            self.logger.error(f"Get profile error: {str(e)}")
            return jsonify({'error': 'Failed to get profile'}), 500
    
    def update_profile(self, user_id, data):
        """Update user profile"""
        try:
            profile = UserProfile.query.filter_by(user_id=user_id).first()
            if not profile:
                return jsonify({'error': 'Profile not found'}), 404
            
            # Update profile fields
            allowed_fields = ['display_name', 'age', 'gender', 'bio', 'occupation', 'education', 'height']
            for field in allowed_fields:
                if field in data:
                    setattr(profile, field, sanitize_input(data[field]))
            
            # Update preferences if provided
            if 'preferences' in data:
                prefs = UserPreferences.query.filter_by(user_id=user_id).first()
                if not prefs:
                    prefs = UserPreferences(user_id=user_id)
                    self.db.session.add(prefs)
                
                pref_fields = ['min_age', 'max_age', 'preferred_gender', 'max_distance', 
                              'interests', 'values', 'dealbreakers', 'preferred_cuisines', 
                              'dietary_restrictions']
                
                for field in pref_fields:
                    if field in data['preferences']:
                        setattr(prefs, field, data['preferences'][field])
            
            self.db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully'
            })
            
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Update profile error: {str(e)}")
            return jsonify({'error': 'Failed to update profile'}), 500
