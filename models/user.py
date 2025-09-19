from datetime import datetime
from dating_backend import db
from sqlalchemy.ext.hybrid import hybrid_property
from flask_login import UserMixin

# Junction tables for following relationships
user_follows = db.Table('user_follows',
    db.Column('follower_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('following_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow),
    db.Column('is_active', db.Boolean, default=True)
)

user_restaurant_follows = db.Table('user_restaurant_follows',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('restaurant_id', db.Integer, db.ForeignKey('restaurants.id'), primary_key=True),
    db.Column('followed_at', db.DateTime, default=datetime.utcnow),
    db.Column('notification_enabled', db.Boolean, default=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255))
    reset_token = db.Column(db.String(255))
    reset_token_created = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Original relationships - use string names to avoid circular imports
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    preferences = db.relationship('UserPreferences', backref='user', uselist=False, cascade='all, delete-orphan')
    matches_initiated = db.relationship('Match', foreign_keys='Match.user1_id', backref='initiator')
    matches_received = db.relationship('Match', foreign_keys='Match.user2_id', backref='receiver')
    feedbacks = db.relationship('DateFeedback', foreign_keys='DateFeedback.user_id', backref='user', lazy='dynamic')
    payments = db.relationship('Payment', backref='user', lazy='dynamic')
    
    # Following relationships
    following = db.relationship('User',
        secondary=user_follows,
        primaryjoin=(user_follows.c.follower_id == id),
        secondaryjoin=(user_follows.c.following_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )
    
    # Restaurant following
    followed_restaurants = db.relationship('Restaurant',
        secondary=user_restaurant_follows,
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )
    
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
    
    # Following methods
    def follow_user(self, user):
        """Follow another user"""
        if not self.is_following_user(user):
            self.following.append(user)
    
    def unfollow_user(self, user):
        """Unfollow a user"""
        if self.is_following_user(user):
            self.following.remove(user)
    
    def is_following_user(self, user):
        """Check if following a user"""
        return self.following.filter(user_follows.c.following_id == user.id).count() > 0
    
    def follow_restaurant(self, restaurant):
        """Follow a restaurant"""
        if not self.is_following_restaurant(restaurant):
            self.followed_restaurants.append(restaurant)
    
    def unfollow_restaurant(self, restaurant):
        """Unfollow a restaurant"""
        if self.is_following_restaurant(restaurant):
            self.followed_restaurants.remove(restaurant)
    
    def is_following_restaurant(self, restaurant):
        """Check if following a restaurant"""
        return self.followed_restaurants.filter_by(id=restaurant.id).count() > 0
    
    def get_compatibility_boost(self, other_user):
        """Calculate compatibility boost based on shared restaurant follows"""
        shared_restaurants = self.followed_restaurants.intersect(other_user.followed_restaurants).count()
        # Each shared restaurant adds 5% compatibility, max 25%
        return min(shared_restaurants * 0.05, 0.25)
    
    def get_followers_count(self):
        """Get count of followers for this user"""
        return self.followers.count()
    
    def get_following_count(self):
        """Get count of users this user is following"""
        return self.following.count()
    
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
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'followers_count': self.get_followers_count(),
            'following_count': self.get_following_count()
        }
