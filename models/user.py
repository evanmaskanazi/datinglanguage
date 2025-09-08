from datetime import datetime
from dating_backend import db
from sqlalchemy.ext.hybrid import hybrid_property

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255))
    reset_token = db.Column(db.String(255))  # ADDED
    reset_token_created = db.Column(db.DateTime)  # ADDED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships - use string names to avoid circular imports
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    preferences = db.relationship('UserPreferences', backref='user', uselist=False, cascade='all, delete-orphan')
    matches_initiated = db.relationship('Match', foreign_keys='Match.user1_id', backref='initiator')
    matches_received = db.relationship('Match', foreign_keys='Match.user2_id', backref='receiver')
    feedbacks = db.relationship('DateFeedback', foreign_keys='DateFeedback.user_id', backref='user', lazy='dynamic')
    payments = db.relationship('Payment', backref='user', lazy='dynamic')
    
    @hybrid_property
    def all_matches(self):
        """Get all matches where user is involved"""
        return self.matches_initiated + self.matches_received
    
    @hybrid_property
    def reservations_through_matches(self):
        """Get reservations through matches"""
        # This is a property to access reservations indirectly
        from models.reservation import Reservation
        from models.match import Match
        return Reservation.query.join(Match).filter(
            (Match.user1_id == self.id) | (Match.user2_id == self.id)
        ).all()
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
