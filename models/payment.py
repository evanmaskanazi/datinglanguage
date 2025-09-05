from datetime import datetime
from dating_backend import db

class DateFeedback(db.Model):
    __tablename__ = 'date_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservations.id'), nullable=False)
    match_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer)  # 1-5
    showed_up = db.Column(db.Boolean)
    would_meet_again = db.Column(db.Boolean)
    chemistry_level = db.Column(db.Integer)  # 1-5
    conversation_quality = db.Column(db.Integer)  # 1-5
    overall_experience = db.Column(db.Integer)  # 1-5
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Create unique constraint
    __table_args__ = (
        db.UniqueConstraint('user_id', 'reservation_id'),
    )
    
    # Relationship to match_user
    match_user = db.relationship('User', foreign_keys=[match_user_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'reservation_id': self.reservation_id,
            'rating': self.rating,
            'showed_up': self.showed_up,
            'would_meet_again': self.would_meet_again,
            'chemistry_level': self.chemistry_level,
            'conversation_quality': self.conversation_quality,
            'overall_experience': self.overall_experience,
            'comments': self.comments
        }
