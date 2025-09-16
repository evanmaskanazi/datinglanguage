"""Restaurant management models for analytics and booking management"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Decimal, ForeignKey
from sqlalchemy.orm import relationship
from dating_backend import db

class RestaurantAnalytics(db.Model):
    """Store restaurant analytics data"""
    __tablename__ = 'restaurant_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    total_matches = db.Column(db.Integer, default=0)
    confirmed_matches = db.Column(db.Integer, default=0)
    completed_dates = db.Column(db.Integer, default=0)
    revenue = db.Column(db.Decimal(10, 2), default=0.00)
    average_rating = db.Column(db.Decimal(3, 2), default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    restaurant = relationship("Restaurant", backref="analytics")

class RestaurantBooking(db.Model):
    """Track all restaurant bookings from the dating app"""
    __tablename__ = 'restaurant_bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=True)
    table_id = db.Column(db.Integer, db.ForeignKey('restaurant_tables.id'), nullable=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    booking_datetime = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, confirmed, completed, cancelled
    party_size = db.Column(db.Integer, default=2)
    special_requests = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    restaurant = relationship("Restaurant", backref="bookings")
    match = relationship("Match", backref="restaurant_booking")
    table = relationship("RestaurantTable", backref="bookings")
    user1 = relationship("User", foreign_keys=[user1_id], backref="bookings_as_user1")
    user2 = relationship("User", foreign_keys=[user2_id], backref="bookings_as_user2")

class RestaurantSettings(db.Model):
    """Restaurant owner settings and preferences"""
    __tablename__ = 'restaurant_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False, unique=True)
    notification_email = db.Column(db.String(255))
    auto_accept_bookings = db.Column(db.Boolean, default=False)
    max_advance_days = db.Column(db.Integer, default=30)
    min_advance_hours = db.Column(db.Integer, default=2)
    special_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    restaurant = relationship("Restaurant", backref="settings", uselist=False)
