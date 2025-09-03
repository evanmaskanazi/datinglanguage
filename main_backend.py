"""
Table for Two - Dating App Backend
Real connections, real dinners, real people.
"""
import os
import secrets
import json
import uuid
import html
import bleach
import redis
import smtplib
import jwt
import logging
import traceback
import re
from pathlib import Path
from datetime import datetime, date, timedelta
from functools import wraps
from threading import Thread
from io import BytesIO

# Flask imports
from flask import (Flask, request, jsonify, send_file, session,
                   render_template, redirect, url_for, make_response,
                   flash, Response, g, abort)
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect, generate_csrf
from werkzeug.middleware.proxy_fix import ProxyFix
from markupsafe import escape

# Database imports
from sqlalchemy import text, and_, or_, func
from sqlalchemy.ext.hybrid import hybrid_property

# Email imports
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Cryptography
from cryptography.fernet import Fernet

# === LOGGING CONFIGURATION ===
from utils.logging_config import setup_logger, log_audit
logger = setup_logger('table_for_two')

# === CONSTANTS ===
JWT_SECRET = os.environ.get('SECRET_KEY', 'your-secret-key')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

ALLOWED_ORIGINS = [
    'https://tablefortwo.com',
    'http://localhost:5000',
    'http://127.0.0.1:5000'
]

# Dangerous patterns for XSS protection
DANGEROUS_PATTERNS = [
    r'<script', r'javascript:', r'onerror=', r'onclick=',
    r'onload=', r'<iframe', r'<object', r'<embed',
    r'vbscript:', r'data:text/html'
]

# === ENCRYPTION SETUP ===
ENCRYPTION_KEY = os.environ.get('FIELD_ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    if os.environ.get('PRODUCTION'):
        raise ValueError("FIELD_ENCRYPTION_KEY must be set in production")
    else:
        ENCRYPTION_KEY = Fernet.generate_key()
        logger.warning("Using generated encryption key - DO NOT use in production!")
else:
    ENCRYPTION_KEY = ENCRYPTION_KEY if isinstance(ENCRYPTION_KEY, bytes) else ENCRYPTION_KEY.encode()

fernet = Fernet(ENCRYPTION_KEY)

# === REDIS SETUP ===
redis_client = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))

# === CREATE FLASK APP ===
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Set directories
BASE_DIR = Path(__file__).resolve().parent
app.static_folder = BASE_DIR / 'static'
app.template_folder = BASE_DIR / 'templates'

# === FLASK CONFIGURATION ===
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
    SESSION_COOKIE_NAME='__Host-session'
)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://localhost/table_for_two'
).replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 20,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'max_overflow': 40,
    'pool_timeout': 30
}

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('SMTP_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('SYSTEM_EMAIL')
app.config['MAIL_PASSWORD'] = os.environ.get('SYSTEM_EMAIL_PASSWORD')

# === INITIALIZE EXTENSIONS ===
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
CORS(app, supports_credentials=True)
csrf = CSRFProtect(app)

# Security headers
Talisman(app,
    force_https=False if app.debug else True,
    strict_transport_security={'max_age': 31536000, 'include_subdomains': True},
    content_security_policy=False,
    frame_options='SAMEORIGIN'
)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["5000 per day", "500 per hour"],
    storage_uri="memory://"
)

# === IMPORT UTILITIES AND MODELS ===
from utils.security import (
    sanitize_input, sanitize_html, validate_email,
    encrypt_field, decrypt_field, validate_cors_origin
)
from utils.cache_manager import CacheManager
from utils.email_manager import EmailManager

# Initialize managers
cache = CacheManager(redis_client)
email_manager = EmailManager(app)

# === DATABASE MODELS ===
from models.user import User
from models.restaurant import Restaurant, RestaurantTable
from models.match import Match, MatchStatus
from models.reservation import Reservation, ReservationStatus
from models.profile import UserProfile, UserPreferences
from models.feedback import DateFeedback
from models.payment import Payment, PaymentStatus

# === AUTHENTICATION ===
from auth.decorators import require_auth
from auth.jwt_handler import generate_token, verify_token

# === REQUEST HANDLERS ===
@app.before_request
def before_request():
    g.request_id = str(uuid.uuid4())
    g.request_start_time = datetime.utcnow()
    
    logger.info('request_started', extra={
        'request_id': g.request_id,
        'method': request.method,
        'path': request.path,
        'remote_addr': request.remote_addr
    })

@app.before_request
def check_cors():
    if request.method == 'OPTIONS':
        return
    
    if not validate_cors_origin(request, ALLOWED_ORIGINS):
        logger.warning(f"CORS validation failed for origin: {request.headers.get('Origin')}")
        abort(403, description="CORS validation failed")

@app.before_request
def validate_inputs():
    """Check all inputs for XSS attempts"""
    for key, value in request.values.items():
        if value and isinstance(value, str):
            for pattern in DANGEROUS_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(f"Potential XSS attempt blocked: {key}={value[:50]}...")
                    return jsonify({'error': 'Invalid input detected'}), 400

@app.after_request
def after_request(response):
    duration = (datetime.utcnow() - g.request_start_time).total_seconds()
    
    logger.info('request_completed', extra={
        'request_id': g.request_id,
        'method': request.method,
        'path': request.path,
        'status_code': response.status_code,
        'duration_ms': round(duration * 1000, 2)
    })
    
    response.headers['X-Request-ID'] = g.request_id
    return response

# === API ENDPOINTS ===

# Health check
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })

# Authentication endpoints
@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("10 per hour")
def register():
    """Register new user"""
    try:
        from services.auth_service import AuthService
        auth_service = AuthService(db, bcrypt, logger)
        return auth_service.register(request.json)
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("20 per minute")
def login():
    """User login"""
    try:
        from services.auth_service import AuthService
        auth_service = AuthService(db, bcrypt, logger)
        return auth_service.login(request.json)
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Login failed'}), 500

# Profile endpoints
@app.route('/api/profile', methods=['GET'])
@require_auth()
def get_profile():
    """Get user profile"""
    try:
        from services.profile_service import ProfileService
        profile_service = ProfileService(db, logger)
        return profile_service.get_profile(request.current_user.id)
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get profile'}), 500

@app.route('/api/profile', methods=['PUT'])
@require_auth()
def update_profile():
    """Update user profile"""
    try:
        from services.profile_service import ProfileService
        profile_service = ProfileService(db, logger)
        return profile_service.update_profile(request.current_user.id, request.json)
    except Exception as e:
        logger.error(f"Update profile error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to update profile'}), 500

# Restaurant endpoints
@app.route('/api/restaurants', methods=['GET'])
def get_restaurants():
    """Get available restaurants"""
    try:
        from services.restaurant_service import RestaurantService
        restaurant_service = RestaurantService(db, cache, logger)
        return restaurant_service.get_available_restaurants(request.args)
    except Exception as e:
        logger.error(f"Get restaurants error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get restaurants'}), 500

@app.route('/api/restaurants/<int:restaurant_id>/tables', methods=['GET'])
def get_restaurant_tables(restaurant_id):
    """Get available tables for a restaurant"""
    try:
        from services.restaurant_service import RestaurantService
        restaurant_service = RestaurantService(db, cache, logger)
        return restaurant_service.get_available_tables(restaurant_id, request.args)
    except Exception as e:
        logger.error(f"Get tables error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get tables'}), 500

# Matching endpoints
@app.route('/api/matches/browse', methods=['GET'])
@require_auth()
def browse_matches():
    """Browse potential matches for available tables"""
    try:
        from services.matching_service import MatchingService
        matching_service = MatchingService(db, cache, logger)
        return matching_service.browse_matches(request.current_user.id, request.args)
    except Exception as e:
        logger.error(f"Browse matches error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to browse matches'}), 500

@app.route('/api/matches/request', methods=['POST'])
@require_auth()
@limiter.limit("10 per hour")
def request_match():
    """Request a match with another user"""
    try:
        from services.matching_service import MatchingService
        matching_service = MatchingService(db, cache, logger)
        return matching_service.request_match(request.current_user.id, request.json)
    except Exception as e:
        logger.error(f"Request match error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to request match'}), 500

@app.route('/api/matches/<int:match_id>/respond', methods=['POST'])
@require_auth()
def respond_to_match(match_id):
    """Accept or decline a match request"""
    try:
        from services.matching_service import MatchingService
        matching_service = MatchingService(db, cache, logger)
        return matching_service.respond_to_match(request.current_user.id, match_id, request.json)
    except Exception as e:
        logger.error(f"Respond to match error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to respond to match'}), 500

# Reservation endpoints
@app.route('/api/reservations', methods=['POST'])
@require_auth()
@limiter.limit("5 per hour")
def create_reservation():
    """Create a reservation after match confirmation"""
    try:
        from services.reservation_service import ReservationService
        reservation_service = ReservationService(db, email_manager, logger)
        return reservation_service.create_reservation(request.current_user.id, request.json)
    except Exception as e:
        logger.error(f"Create reservation error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to create reservation'}), 500

@app.route('/api/reservations/<int:reservation_id>', methods=['GET'])
@require_auth()
def get_reservation(reservation_id):
    """Get reservation details"""
    try:
        from services.reservation_service import ReservationService
        reservation_service = ReservationService(db, email_manager, logger)
        return reservation_service.get_reservation(request.current_user.id, reservation_id)
    except Exception as e:
        logger.error(f"Get reservation error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get reservation'}), 500

# Payment endpoints
@app.route('/api/payments/initiate', methods=['POST'])
@require_auth()
def initiate_payment():
    """Initiate payment for reservation"""
    try:
        from services.payment_service import PaymentService
        payment_service = PaymentService(db, logger)
        return payment_service.initiate_payment(request.current_user.id, request.json)
    except Exception as e:
        logger.error(f"Initiate payment error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to initiate payment'}), 500

@app.route('/api/payments/webhook', methods=['POST'])
@csrf.exempt
def payment_webhook():
    """Handle payment provider webhooks"""
    try:
        from services.payment_service import PaymentService
        payment_service = PaymentService(db, logger)
        return payment_service.handle_webhook(request.json, request.headers)
    except Exception as e:
        logger.error(f"Payment webhook error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Webhook processing failed'}), 500

# Feedback endpoints
@app.route('/api/feedback', methods=['POST'])
@require_auth()
def submit_feedback():
    """Submit post-date feedback"""
    try:
        from services.feedback_service import FeedbackService
        feedback_service = FeedbackService(db, logger)
        return feedback_service.submit_feedback(request.current_user.id, request.json)
    except Exception as e:
        logger.error(f"Submit feedback error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to submit feedback'}), 500

# Admin endpoints (protected)
@app.route('/api/admin/restaurants', methods=['POST'])
@require_auth(roles=['admin'])
def add_restaurant():
    """Add new restaurant partner"""
    try:
        from services.admin_service import AdminService
        admin_service = AdminService(db, logger)
        return admin_service.add_restaurant(request.json)
    except Exception as e:
        logger.error(f"Add restaurant error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to add restaurant'}), 500

@app.route('/api/admin/analytics', methods=['GET'])
@require_auth(roles=['admin'])
def get_analytics():
    """Get platform analytics"""
    try:
        from services.admin_service import AdminService
        admin_service = AdminService(db, cache, logger)
        return admin_service.get_analytics(request.args)
    except Exception as e:
        logger.error(f"Get analytics error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get analytics'}), 500

# GDPR endpoints
@app.route('/api/user/data-export', methods=['GET'])
@require_auth()
def export_user_data():
    """Export user data for GDPR compliance"""
    try:
        from services.gdpr_service import GDPRService
        gdpr_service = GDPRService(db, logger)
        return gdpr_service.export_user_data(request.current_user.id)
    except Exception as e:
        logger.error(f"Data export error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to export data'}), 500

@app.route('/api/user/delete-account', methods=['DELETE'])
@require_auth()
def delete_account():
    """Delete user account"""
    try:
        from services.gdpr_service import GDPRService
        gdpr_service = GDPRService(db, logger)
        return gdpr_service.delete_account(request.current_user.id)
    except Exception as e:
        logger.error(f"Delete account error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to delete account'}), 500

# === ERROR HANDLERS ===
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Resource not found',
        'request_id': getattr(g, 'request_id', 'unknown')
    }), 404

@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': str(error.description),
        'request_id': getattr(g, 'request_id', 'unknown')
    }), 429

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logger.error('internal_server_error', extra={
        'error': str(error),
        'request_id': getattr(g, 'request_id', 'unknown')
    }, exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'request_id': getattr(g, 'request_id', 'unknown')
    }), 500

# === STATIC FILES ===
@app.route('/')
def index():
    """Serve the main app"""
    return send_file('static/index.html')

@app.route('/favicon.ico')
def favicon():
    return send_file('static/favicon.ico', mimetype='image/x-icon')

# === INITIALIZATION ===
def initialize_database():
    """Initialize database with default data"""
    with app.app_context():
        db.create_all()
        
        # Import initialization functions
        from utils.db_init import (
            create_default_categories,
            create_admin_user,
            create_test_restaurants
        )
        
        # Run initialization
        create_default_categories(db)
        create_admin_user(db, bcrypt)
        
        if not os.environ.get('PRODUCTION'):
            create_test_restaurants(db)
        
        logger.info("Database initialized successfully")

# === MAIN ENTRY POINT ===
if __name__ == '__main__':
    # Initialize database if needed
    initialize_database()
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=not os.environ.get('PRODUCTION'))
