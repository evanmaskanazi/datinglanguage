"""Date feedback and rating models"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from dating_backend import db

class DateFeedback(db.Model):
    """Store user feedback and ratings for restaurant dates"""
    __tablename__ = 'date_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Updated to use restaurant_bookings instead of reservations
    booking_id = db.Column(db.Integer, db.ForeignKey('restaurant_bookings.id'), nullable=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservations.id'), nullable=True)  # Keep for backward compatibility
    
    match_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    
    # Original rating fields (keep for backward compatibility)
    rating = db.Column(db.Integer)  # 1-5 (overall restaurant rating)
    showed_up = db.Column(db.Boolean)
    would_meet_again = db.Column(db.Boolean)
    chemistry_level = db.Column(db.Integer)  # 1-5
    conversation_quality = db.Column(db.Integer)  # 1-5
    overall_experience = db.Column(db.Integer)  # 1-5
    comments = db.Column(db.Text)
    
    # New fields for enhanced restaurant ratings
    restaurant_rating = db.Column(db.Integer)  # 1-5 stars for restaurant
    food_quality = db.Column(db.Integer)  # 1-5
    service_quality = db.Column(db.Integer)  # 1-5
    ambiance_rating = db.Column(db.Integer)  # 1-5
    value_for_money = db.Column(db.Integer)  # 1-5
    restaurant_review = db.Column(db.Text)  # Detailed restaurant review
    
    # Date experience fields
    date_success = db.Column(db.Boolean)  # Was the date successful?
    recommend_restaurant = db.Column(db.Boolean)  # Would recommend restaurant for dates?
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="given_feedback")
    match_user = relationship("User", foreign_keys=[match_user_id], backref="received_feedback")
    restaurant = relationship("Restaurant", backref="user_feedback")
    
    # Handle both booking_id and reservation_id
    booking = relationship("RestaurantBooking", backref="feedback", foreign_keys=[booking_id])
    
    # Create unique constraint to prevent duplicate feedback
    __table_args__ = (
        db.UniqueConstraint('user_id', 'booking_id', name='unique_user_booking_feedback'),
        db.UniqueConstraint('user_id', 'reservation_id', name='unique_user_reservation_feedback'),
    )
    
    def to_dict(self):
        """Convert feedback to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'booking_id': self.booking_id,
            'reservation_id': self.reservation_id,
            'match_user_id': self.match_user_id,
            'restaurant_id': self.restaurant_id,
            
            # Original fields
            'rating': self.rating,
            'showed_up': self.showed_up,
            'would_meet_again': self.would_meet_again,
            'chemistry_level': self.chemistry_level,
            'conversation_quality': self.conversation_quality,
            'overall_experience': self.overall_experience,
            'comments': self.comments,
            
            # Restaurant-specific ratings
            'restaurant_rating': self.restaurant_rating,
            'food_quality': self.food_quality,
            'service_quality': self.service_quality,
            'ambiance_rating': self.ambiance_rating,
            'value_for_money': self.value_for_money,
            'restaurant_review': self.restaurant_review,
            
            # Date experience
            'date_success': self.date_success,
            'recommend_restaurant': self.recommend_restaurant,
            
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_overall_restaurant_score(self):
        """Calculate overall restaurant score from individual ratings"""
        ratings = [
            self.restaurant_rating,
            self.food_quality,
            self.service_quality,
            self.ambiance_rating,
            self.value_for_money
        ]
        
        # Filter out None values
        valid_ratings = [r for r in ratings if r is not None]
        
        if not valid_ratings:
            return None
        
        return round(sum(valid_ratings) / len(valid_ratings), 1)
    
    def is_positive_review(self):
        """Determine if this is a positive review"""
        overall_score = self.get_overall_restaurant_score()
        if overall_score is None:
            return None
        
        return overall_score >= 4.0 and self.recommend_restaurant is True
