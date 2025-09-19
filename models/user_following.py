"""User following relationships model"""
from dating_backend import db
from datetime import datetime

class UserFollow(db.Model):
    __tablename__ = 'user_follows'
    
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate follows
    __table_args__ = (
        db.UniqueConstraint('follower_id', 'followed_id', name='unique_user_follow'),
    )
