from datetime import datetime
from dating_backend import db
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import and_

class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    cuisine_type = db.Column(db.String(100))
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    price_range = db.Column(db.Integer)  # 1-4 scale
    rating = db.Column(db.Numeric(3, 2))
    ambiance = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # API integration fields
    external_id = db.Column(db.String(255))
    source = db.Column(db.String(50), default='internal')
    image_url = db.Column(db.String(500))
    
    # Restaurant owner account info
    owner_email = db.Column(db.String(255))
    owner_password_hash = db.Column(db.String(255))
    is_partner = db.Column(db.Boolean, default=False)
    
    # Fixed relationships
    tables = db.relationship('RestaurantTable', backref='restaurant', lazy='dynamic', cascade='all, delete-orphan')
    reservations = db.relationship('Reservation', back_populates='restaurant', lazy='dynamic')
    
    @hybrid_property
    def available_tables_count(self):
        """Count of available tables"""
        return self.tables.filter_by(is_available=True).count()
    
    def set_password(self, password):
        """Set password for restaurant owner account using bcrypt"""
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        self.owner_password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check password for restaurant owner account using bcrypt"""
        from flask_bcrypt import Bcrypt
        if not self.owner_password_hash:
            return False
        bcrypt = Bcrypt()
        return bcrypt.check_password_hash(self.owner_password_hash, password)
    
    def get_match_requests(self, date_range=None):
        """Get match requests for this restaurant"""
        from models.match import Match
        query = Match.query.filter_by(restaurant_id=str(self.id))
        
        if date_range:
            start_date, end_date = date_range
            query = query.filter(and_(
                Match.proposed_datetime >= start_date,
                Match.proposed_datetime <= end_date
            ))
        
        return query.order_by(Match.proposed_datetime).all()
    
    def get_confirmed_matches_count(self):
        """Get count of confirmed matches at this restaurant"""
        from models.match import Match, MatchStatus
        return Match.query.filter_by(
            restaurant_id=str(self.id),
            status=MatchStatus.CONFIRMED
        ).count()
    
    def get_success_rate(self):
        """Calculate success rate (confirmed matches / total matches)"""
        from models.match import Match, MatchStatus
        total_matches = Match.query.filter_by(restaurant_id=str(self.id)).count()
        if total_matches == 0:
            return 0.0
        
        confirmed_matches = Match.query.filter_by(
            restaurant_id=str(self.id),
            status=MatchStatus.CONFIRMED
        ).count()
        
        return round((confirmed_matches / total_matches) * 100, 1)
    
    def __repr__(self):
        return f'<Restaurant {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'cuisine_type': self.cuisine_type,
            'address': self.address,
            'phone': self.phone,
            'price_range': self.price_range,
            'rating': float(self.rating) if self.rating else None,
            'ambiance': self.ambiance,
            'is_active': self.is_active,
            'external_id': self.external_id,
            'source': self.source,
            'image_url': self.image_url,
            'is_partner': self.is_partner,
            'available_tables': self.available_tables_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RestaurantTable(db.Model):
    __tablename__ = 'restaurant_tables'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    table_number = db.Column(db.String(10), nullable=False)
    capacity = db.Column(db.Integer, default=2)
    location = db.Column(db.String(100))  # window, corner, center, etc.
    is_available = db.Column(db.Boolean, default=True)
    special_features = db.Column(db.Text)  # romantic, quiet, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<RestaurantTable {self.restaurant.name} - Table {self.table_number}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'table_number': self.table_number,
            'capacity': self.capacity,
            'location': self.location,
            'is_available': self.is_available,
            'special_features': self.special_features,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
