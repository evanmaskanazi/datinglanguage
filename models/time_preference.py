"""
Time preference model for users to set desired meeting times
"""
from datetime import datetime
from sqlalchemy import and_
from .. import db

class UserTimePreference(db.Model):
    __tablename__ = 'user_time_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    restaurant_id = db.Column(db.String(255))  # Can be API restaurant ID or internal
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('time_preferences', lazy='dynamic'))
    
    def __repr__(self):
        return f'<TimePreference {self.user.email} - {self.date} {self.time}>'
    
    @classmethod
    def get_user_preferences(cls, user_id, date_range=None):
        """Get user's time preferences, optionally filtered by date range"""
        query = cls.query.filter_by(user_id=user_id, is_active=True)
        if date_range:
            start_date, end_date = date_range
            query = query.filter(and_(cls.date >= start_date, cls.date <= end_date))
        return query.order_by(cls.date, cls.time).all()
    
    @classmethod
    def get_matching_preferences(cls, user_id, exclude_user_ids=None):
        """Find other users with matching time preferences"""
        user_prefs = cls.query.filter_by(user_id=user_id, is_active=True).all()
        matching_users = set()
        
        for pref in user_prefs:
            matches = cls.query.filter(
                cls.date == pref.date,
                cls.time == pref.time,
                cls.user_id != user_id,
                cls.is_active == True
            )
            
            if exclude_user_ids:
                matches = matches.filter(~cls.user_id.in_(exclude_user_ids))
            
            for match in matches:
                matching_users.add(match.user_id)
        
        return list(matching_users)
