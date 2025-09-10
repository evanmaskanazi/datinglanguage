from datetime import datetime
from dating_backend import db
from sqlalchemy import Index

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
    price_range = db.Column(db.Integer)  # 1-4 scale
    ambiance = db.Column(db.String(50))  # romantic, casual, upscale, etc
    rating = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # NEW FIELDS FOR API INTEGRATION
    external_id = db.Column(db.String(255), unique=True, nullable=True)
    source = db.Column(db.String(50), default='internal')  # 'internal', 'yelp', 'google'
    image_url = db.Column(db.String(500))
    
    # Relationships
    tables = db.relationship('RestaurantTable', backref='restaurant', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'cuisine_type': self.cuisine_type,
            'address': self.address,
            'price_range': self.price_range,
            'ambiance': self.ambiance,
            'rating': self.rating,
            'external_id': self.external_id,
            'source': self.source,
            'image_url': self.image_url
        }

class RestaurantTable(db.Model):
    __tablename__ = 'restaurant_tables'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    table_number = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer, default=2)
    location = db.Column(db.String(50))  # window, garden, corner, etc
    is_available = db.Column(db.Boolean, default=True)
    
    # Create unique constraint
    __table_args__ = (
        db.UniqueConstraint('restaurant_id', 'table_number'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'table_number': self.table_number,
            'capacity': self.capacity,
            'location': self.location,
            'is_available': self.is_available
        }
