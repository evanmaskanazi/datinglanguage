from datetime import datetime
from dating_backend import db

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    display_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    bio = db.Column(db.Text)
    occupation = db.Column(db.String(100))
    education = db.Column(db.String(100))
    height = db.Column(db.Integer)
    profile_photo = db.Column(db.String(500))
    verified_photo = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserPreferences(db.Model):
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    min_age = db.Column(db.Integer, default=18)
    max_age = db.Column(db.Integer, default=99)
    preferred_gender = db.Column(db.String(20))
    max_distance = db.Column(db.Integer, default=50)
    interests = db.Column(db.JSON)
    values = db.Column(db.JSON)
    dealbreakers = db.Column(db.JSON)
    preferred_cuisines = db.Column(db.JSON)
    dietary_restrictions = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
