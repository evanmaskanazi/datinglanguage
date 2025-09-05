from datetime import datetime
from dating_backend import db

class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    cuisine_type = db.Column(db.String(100))
    address = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(255))
    website = db.Column(db.String(500))
    price_range = db.Column(db.Integer)
    ambiance = db.Column(db.String(50))
    rating = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tables = db.relationship('RestaurantTable', backref='restaurant', cascade='all, delete-orphan')

class RestaurantTable(db.Model):
    __tablename__ = 'restaurant_tables'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'))
    table_number = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer, default=2)
    location = db.Column(db.String(50))
    is_available = db.Column(db.Boolean, default=True)
