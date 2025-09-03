from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY

db = SQLAlchemy()

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    bio = db.Column(db.Text)
    occupation = db.Column(db.String(100))
    education = db.Column(db.String(100))
    height = db.Column(db.Integer)  # in cm
    profile_photo = db.Column(db.String(500))
    verified_photo = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'display_name': self.display_name,
            'age': self.age,
            'gender': self.gender,
            'bio': self.bio,
            'occupation': self.occupation,
            'education': self.education,
            'height': self.height,
            'profile_photo': self.profile_photo,
            'verified_photo': self.verified_photo
        }

class UserPreferences(db.Model):
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    min_age = db.Column(db.Integer, default=18)
    max_age = db.Column(db.Integer, default=99)
    preferred_gender = db.Column(db.String(20))
    max_distance = db.Column(db.Integer, default=50)  # in km
    interests = db.Column(ARRAY(db.String))
    values = db.Column(ARRAY(db.String))
    dealbreakers = db.Column(ARRAY(db.String))
    preferred_cuisines = db.Column(ARRAY(db.String))
    dietary_restrictions = db.Column(ARRAY(db.String))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'min_age': self.min_age,
            'max_age': self.max_age,
            'preferred_gender': self.preferred_gender,
            'max_distance': self.max_distance,
            'interests': self.interests,
            'values': self.values,
            'dealbreakers': self.dealbreakers,
            'preferred_cuisines': self.preferred_cuisines,
            'dietary_restrictions': self.dietary_restrictions
        }
