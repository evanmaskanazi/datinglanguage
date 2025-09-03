from flask import jsonify
from models.feedback import DateFeedback, db

class FeedbackService:
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
    
    def submit_feedback(self, user_id, data):
        """Submit post-date feedback"""
        try:
            feedback = DateFeedback(
                user_id=user_id,
                reservation_id=data.get('reservation_id'),
                match_user_id=data.get('match_user_id'),
                rating=data.get('rating'),
                showed_up=data.get('showed_up'),
                would_meet_again=data.get('would_meet_again'),
                chemistry_level=data.get('chemistry_level'),
                conversation_quality=data.get('conversation_quality'),
                overall_experience=data.get('overall_experience'),
                comments=data.get('comments')
            )
            
            self.db.session.add(feedback)
            self.db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Feedback submitted successfully'
            })
            
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Submit feedback error: {str(e)}")
            return jsonify({'error': 'Failed to submit feedback'}), 500
