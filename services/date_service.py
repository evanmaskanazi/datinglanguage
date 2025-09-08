from flask import jsonify
from models.reservation import Reservation, ReservationStatus
from models.match import Match, MatchStatus
from models.restaurant import Restaurant
from models.user import User
from datetime import datetime
from sqlalchemy import and_, or_

class DateService:
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
    
    def get_upcoming_dates(self, user_id):
        """Get upcoming dates for user"""
        try:
            # Get upcoming reservations where user is involved
            upcoming = Reservation.query.join(Match).join(
                Restaurant, Reservation.restaurant_id == Restaurant.id
            ).filter(
                ((Match.user1_id == user_id) | (Match.user2_id == user_id)),
                Reservation.status.in_([ReservationStatus.CONFIRMED, ReservationStatus.PENDING]),
                Reservation.date_time >= datetime.utcnow()
            ).order_by(Reservation.date_time).all()
            
            dates = []
            for reservation in upcoming:
                # Get the other user
                other_user_id = reservation.match.user2_id if reservation.match.user1_id == user_id else reservation.match.user1_id
                other_user = User.query.get(other_user_id)
                
                if other_user and other_user.profile:
                    dates.append({
                        'id': reservation.id,
                        'datetime': reservation.date_time.isoformat(),
                        'restaurant_name': reservation.restaurant.name,
                        'restaurant_address': reservation.restaurant.address,
                        'match_name': other_user.profile.display_name,
                        'match_id': reservation.match.id,
                        'status': reservation.status.value
                    })
            
            return jsonify(dates)
            
        except Exception as e:
            self.logger.error(f"Get upcoming dates error: {str(e)}")
            return jsonify({'error': 'Failed to get dates'}), 500
    
    def get_date_history(self, user_id):
        """Get past dates for user"""
        try:
            # Get past reservations
            past = Reservation.query.join(Match).join(
                Restaurant, Reservation.restaurant_id == Restaurant.id
            ).filter(
                ((Match.user1_id == user_id) | (Match.user2_id == user_id)),
                or_(
                    Reservation.date_time < datetime.utcnow(),
                    Reservation.status == ReservationStatus.COMPLETED
                )
            ).order_by(Reservation.date_time.desc()).all()
            
            dates = []
            for reservation in past:
                # Get the other user
                other_user_id = reservation.match.user2_id if reservation.match.user1_id == user_id else reservation.match.user1_id
                other_user = User.query.get(other_user_id)
                
                if other_user and other_user.profile:
                    dates.append({
                        'id': reservation.id,
                        'datetime': reservation.date_time.isoformat(),
                        'restaurant_name': reservation.restaurant.name,
                        'restaurant_address': reservation.restaurant.address,
                        'match_name': other_user.profile.display_name,
                        'match_id': reservation.match.id,
                        'status': reservation.status.value,
                        'has_feedback': bool(reservation.feedbacks)
                    })
            
            return jsonify(dates)
            
        except Exception as e:
            self.logger.error(f"Get date history error: {str(e)}")
            return jsonify({'error': 'Failed to get history'}), 500
