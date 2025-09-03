"""Celery configuration for Table for Two"""
import os
from celery import Celery
from datetime import datetime, timedelta
from flask import Flask

# Initialize Celery
def create_celery_app():
    celery = Celery(
        'table_for_two',
        broker=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
        backend=os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    )
    
    # Configure Celery
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,
        task_soft_time_limit=240,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=100,
        beat_schedule={
            'send-reminder-emails': {
                'task': 'celery_app.send_date_reminders',
                'schedule': timedelta(hours=1),
            },
            'cleanup-expired-matches': {
                'task': 'celery_app.cleanup_expired_matches',
                'schedule': timedelta(hours=6),
            },
            'generate-daily-analytics': {
                'task': 'celery_app.generate_daily_analytics',
                'schedule': timedelta(days=1),
            },
        }
    )
    
    return celery

celery = create_celery_app()

# Import Flask app context
from dating_backend import app, db

@celery.task
def send_date_reminders():
    """Send reminder emails for upcoming dates"""
    with app.app_context():
        from services.email_service import EmailService
        from models.reservation import Reservation, ReservationStatus
        
        # Get reservations happening in next 24 hours
        tomorrow = datetime.utcnow() + timedelta(days=1)
        upcoming = Reservation.query.filter(
            Reservation.date_time.between(datetime.utcnow(), tomorrow),
            Reservation.status == ReservationStatus.CONFIRMED
        ).all()
        
        email_service = EmailService()
        for reservation in upcoming:
            email_service.send_date_reminder(reservation)
        
        return f"Sent {len(upcoming)} reminders"

@celery.task
def cleanup_expired_matches():
    """Clean up matches that expired without confirmation"""
    with app.app_context():
        from models.match import Match, MatchStatus
        
        # Expire matches older than 48 hours
        cutoff = datetime.utcnow() - timedelta(hours=48)
        expired = Match.query.filter(
            Match.created_at < cutoff,
            Match.status == MatchStatus.PENDING
        ).update({'status': MatchStatus.EXPIRED})
        
        db.session.commit()
        return f"Expired {expired} matches"

@celery.task
def process_payment_webhook(payment_id, webhook_data):
    """Process payment webhook asynchronously"""
    with app.app_context():
        from services.payment_service import PaymentService
        payment_service = PaymentService(db, None)
        return payment_service.process_webhook(payment_id, webhook_data)

@celery.task
def generate_daily_analytics():
    """Generate daily analytics report"""
    with app.app_context():
        from services.analytics_service import AnalyticsService
        analytics_service = AnalyticsService(db)
        return analytics_service.generate_daily_report()

@celery.task
def send_feedback_request(reservation_id):
    """Send feedback request after date"""
    with app.app_context():
        from services.email_service import EmailService
        from models.reservation import Reservation
        
        reservation = Reservation.query.get(reservation_id)
        if reservation:
            email_service = EmailService()
            email_service.send_feedback_request(reservation)
            return f"Feedback request sent for reservation {reservation_id}"
        return f"Reservation {reservation_id} not found"
