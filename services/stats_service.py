from flask import jsonify
from models.user import User
from models.match import Match, MatchStatus
from models.reservation import Reservation, ReservationStatus
from models.feedback import DateFeedback
from sqlalchemy import func

class StatsService:
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
    
    def get_user_stats(self, user_id):
        """Get user statistics for dashboard"""
        try:
            # Get total dates (completed reservations)
            total_dates = Reservation.query.join(Match).filter(
                (Match.user1_id == user_id) | (Match.user2_id == user_id),
                Reservation.status == ReservationStatus.COMPLETED
            ).count()
            
            # Get active matches
            active_matches = Match.query.filter(
                ((Match.user1_id == user_id) | (Match.user2_id == user_id)),
                Match.status.in_([MatchStatus.PENDING, MatchStatus.ACCEPTED])
            ).count()
            
            # Get pending matches waiting for user's response
            pending_matches = Match.query.filter(
                Match.user2_id == user_id,
                Match.status == MatchStatus.PENDING
            ).count()
            
            # Calculate success rate based on feedback
            positive_feedbacks = DateFeedback.query.filter(
                DateFeedback.user_id == user_id,
                DateFeedback.would_meet_again == True
            ).count()
            
            success_rate = 0
            if total_dates > 0:
                success_rate = int((positive_feedbacks / total_dates) * 100)
            
            return jsonify({
                'total_dates': total_dates,
                'active_matches': active_matches,
                'pending_matches': pending_matches,
                'success_rate': success_rate
            })
            
        except Exception as e:
            self.logger.error(f"Get user stats error: {str(e)}")
            return jsonify({'error': 'Failed to get stats'}), 500
