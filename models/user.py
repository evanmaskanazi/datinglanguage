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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships - use string names to avoid circular imports
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    preferences = db.relationship('UserPreferences', backref='user', uselist=False, cascade='all, delete-orphan')
    matches_initiated = db.relationship('Match', foreign_keys='Match.user1_id', backref='initiator')
    matches_received = db.relationship('Match', foreign_keys='Match.user2_id', backref='receiver')
    reservations = db.relationship('Reservation', backref='user', lazy='dynamic')
    feedbacks = db.relationship('DateFeedback', foreign_keys='DateFeedback.user_id', backref='user', lazy='dynamic')
    payments = db.relationship('Payment', backref='user', lazy='dynamic')
