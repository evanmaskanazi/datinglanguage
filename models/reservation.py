from datetime import datetime
import secrets
from dating_backend import db

class ReservationStatus:
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    CANCELLED = 'cancelled'
    COMPLETED = 'completed'
    NO_SHOW = 'no_show'

class Reservation(db.Model):
    __tablename__ = 'reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'))
    table_id = db.Column(db.Integer, db.ForeignKey('restaurant_tables.id'))
    date_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default=ReservationStatus.PENDING)
    confirmation_code = db.Column(db.String(20), unique=True)
    special_requests = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    table = db.relationship('RestaurantTable', backref='reservations')
    feedbacks = db.relationship('DateFeedback', backref='reservation')
    payments = db.relationship('Payment', backref='reservation')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.confirmation_code:
            self.confirmation_code = self.generate_confirmation_code()
    
    @staticmethod
    def generate_confirmation_code():
        """Generate unique confirmation code"""
        return f"TFT-{secrets.token_urlsafe(6).upper()}"
    
    def confirm(self):
        """Confirm the reservation"""
        self.status = ReservationStatus.CONFIRMED
        db.session.commit()
    
    def cancel(self):
        """Cancel the reservation"""
        self.status = ReservationStatus.CANCELLED
        # Free up the table
        if self.table:
            self.table.is_available = True
        db.session.commit()
    
    def mark_completed(self):
        """Mark reservation as completed"""
        self.status = ReservationStatus.COMPLETED
        db.session.commit()
    
    @property
    def is_upcoming(self):
        """Check if reservation is in the future"""
        return self.date_time > datetime.utcnow()
    
    @property
    def is_confirmed(self):
        """Check if reservation is confirmed"""
        return self.status == ReservationStatus.CONFIRMED
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'match_id': self.match_id,
            'table_id': self.table_id,
            'date_time': self.date_time.isoformat(),
            'status': self.status,
            'confirmation_code': self.confirmation_code,
            'special_requests': self.special_requests,
            'created_at': self.created_at.isoformat(),
            'restaurant': self.table.restaurant.name if self.table else None
        }
    
    def __repr__(self):
        return f'<Reservation {self.confirmation_code} - {self.status}>'
