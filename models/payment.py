"""
Payment models for handling transactions
"""
from datetime import datetime
from dating_backend import db
from enum import Enum

class PaymentStatus(Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REFUNDED = 'refunded'

class Payment(db.Model):
    __tablename__ = 'payments'  # Fixed: proper double underscore syntax
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservations.id'))
    booking_id = db.Column(db.Integer, db.ForeignKey('restaurant_bookings.id'))
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING)
    stripe_payment_id = db.Column(db.String(255))
    stripe_charge_id = db.Column(db.String(255))
    payment_method = db.Column(db.String(50))
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Fixed relationship with unique backref to avoid conflicts
    payment_user = db.relationship("User", backref="user_payments")
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'reservation_id': self.reservation_id,
            'booking_id': self.booking_id,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status.value if self.status else None,
            'payment_method': self.payment_method,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    def __repr__(self):
        return f'<Payment {self.id}: ${self.amount} ({self.status.value})>'
