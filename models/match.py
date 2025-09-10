from datetime import datetime
from dating_backend import db
from enum import Enum

class MatchStatus(Enum):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    DECLINED = 'declined'
    EXPIRED = 'expired'
    COMPLETED = 'completed'

class Match(db.Model):
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'))
    table_id = db.Column(db.Integer, db.ForeignKey('restaurant_tables.id'))
    proposed_datetime = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.Enum(MatchStatus), default=MatchStatus.PENDING)
    compatibility_score = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)
    
    # Relationships
    user1 = db.relationship('User', foreign_keys=[user1_id], backref='sent_matches')
    user2 = db.relationship('User', foreign_keys=[user2_id], backref='received_matches')
    restaurant = db.relationship('Restaurant', backref='matches')
    table = db.relationship('RestaurantTable', backref='matches')
    
    # Create unique constraint
    __table_args__ = (
        db.UniqueConstraint('user1_id', 'user2_id', 'proposed_datetime'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user1_id': self.user1_id,
            'user2_id': self.user2_id,
            'restaurant_id': self.restaurant_id,
            'table_id': self.table_id,
            'proposed_datetime': self.proposed_datetime.isoformat() if self.proposed_datetime else None,
            'status': self.status.value if self.status else None,
            'compatibility_score': self.compatibility_score,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
