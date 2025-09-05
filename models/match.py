from datetime import datetime
from dating_backend import db

class MatchStatus:
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    DECLINED = 'declined'
    EXPIRED = 'expired'
    COMPLETED = 'completed'

class Match(db.Model):
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    table_id = db.Column(db.Integer, db.ForeignKey('restaurant_tables.id'))
    proposed_datetime = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default=MatchStatus.PENDING)
    compatibility_score = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)
    
    # Relationships
    table = db.relationship('RestaurantTable', backref='matches')
    reservation = db.relationship('Reservation', backref='match', uselist=False)
