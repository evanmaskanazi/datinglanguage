"""Time preference model for Table for Two"""
from datetime import datetime
from sqlalchemy import Column, Integer, Date, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

# Use absolute import instead of relative
from dating_backend import db


class UserTimePreference(db.Model):
    """Model for user time preferences"""
    __tablename__ = 'user_time_preferences'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    preferred_date = Column(Date, nullable=False)
    preferred_time = Column(String(10), nullable=False)  # Format: "HH:MM"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', backref='time_preferences')
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.preferred_date.isoformat() if self.preferred_date else None,
            'time': self.preferred_time,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
