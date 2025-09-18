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
from urllib.parse import urlencode
import requests

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
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from markupsafe import escape

# Database imports
from sqlalchemy import text, and_, or_, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.exc import IntegrityError
from sqlalchemy.types import Numeric
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

# Email imports
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Cryptography
from cryptography.fernet import Fernet

# OAuth configuration
from authlib.integrations.flask_client import OAuth

# === LOGGING CONFIGURATION ===
from utils.logging_config import setup_logger, log_audit

def require_auth(roles=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated via Flask-Login
            if not current_user.is_authenticated:
                # Fallback to session-based auth
                if 'user_id' not in session:
                    return jsonify({'error': 'Authentication required'}), 401

                # Get user from database
                from models.user import User
                user = User.query.get(session['user_id'])
                if not user:
                    session.clear()
                    return jsonify({'error': 'Invalid session'}), 401

                # Log in the user for Flask-Login
                login_user(user)
            else:
                user = current_user

            # Check if user is active
            if not user.is_active:
                return jsonify({'error': 'Account deactivated'}), 401

            # Check roles if specified
            if roles and user.role not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403

            # Attach user to request
            request.current_user = user

            return f(*args, **kwargs)

        return decorated_function

    return decorator

logger = setup_logger('table_for_two')

# === CONSTANTS ===
# === CONSTANTS ===
JWT_SECRET = os.environ.get('SECRET_KEY', 'your-secret-key')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# Translation service setup
GOOGLE_TRANSLATE_API_KEY = os.environ.get('GOOGLE_TRANSLATE_API_KEY')


def translate_text(text, target_language):
    """Translate text using Google Translate API"""
    if not GOOGLE_TRANSLATE_API_KEY or target_language == 'en':
        return text

    try:
        import requests
        url = 'https://translation.googleapis.com/language/translate/v2'
        params = {
            'key': GOOGLE_TRANSLATE_API_KEY,
            'q': text,
            'target': target_language,
            'source': 'en'
        }

        response = requests.post(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data['data']['translations'][0]['translatedText']
    except Exception as e:
        logger.warning(f"Translation failed for {text}: {e}")

    return text  # Fallback to original













ALLOWED_ORIGINS = [
    'https://tablefortwo.com',
    'https://datinglanguage.onrender.com',
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
    SESSION_COOKIE_SECURE=not app.debug,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
    SESSION_COOKIE_NAME='session'
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
mail = Mail(app)
CORS(app, supports_credentials=True)
csrf = CSRFProtect(app)

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v2/',
    client_kwargs={'scope': 'openid email profile'},
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs'
)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    from models.user import User
    return User.query.get(int(user_id))

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

# === DATABASE MODELS (Import in correct order) ===
from models.user import User
from models.restaurant import Restaurant, RestaurantTable
from models.match import Match, MatchStatus
from models.reservation import Reservation, ReservationStatus
from models.profile import UserProfile, UserPreferences
from models.feedback import DateFeedback
from models.payment import Payment, PaymentStatus
from models.restaurant_management import RestaurantBooking, RestaurantAnalytics, RestaurantSettings

# === SERVICE IMPORTS ===
from services.matching_service import MatchingService
from services.restaurant_service import RestaurantService
from services.restaurant_management_service import RestaurantManagementService
from services.email_service import EmailService
from services.auth_service import AuthService

# === UTILS IMPORTS ===
from utils.validators import validate_email, validate_password
from utils.security import sanitize_input, generate_csrf_token
from utils.helpers import format_datetime, calculate_age

# === WEBSOCKET SETUP ===
from services.websocket_service import WebSocketService

# Initialize WebSocket service
websocket_service = WebSocketService(app, redis_client, logger)
socketio = websocket_service.socketio

# === RESTAURANT API SERVICE ===
from services.restaurant_api_service import RestaurantAPIService
restaurant_api = RestaurantAPIService(logger)

# === INITIALIZE SERVICES ===
matching_service = MatchingService(db, cache, logger)
restaurant_service = RestaurantService(db, cache, logger)
restaurant_management_service = RestaurantManagementService(db, email_manager, logger)
email_service = EmailService(app, logger)
auth_service = AuthService(db, bcrypt, logger)

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
    if hasattr(g, 'request_start_time'):
        duration = (datetime.utcnow() - g.request_start_time).total_seconds()

        logger.info('request_completed', extra={
            'request_id': getattr(g, 'request_id', 'unknown'),
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration_ms': round(duration * 1000, 2)
        })

    response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
    return response

# === API ENDPOINTS ===

# Health check
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


# ADD HERE:
@app.route('/debug/paths')
def debug_paths():
    import os
    return jsonify({
        'app_root': app.root_path,
        'static_folder': str(app.static_folder),
        'static_url_path': app.static_url_path,
        'i18n_exists': os.path.exists(os.path.join(app.static_folder, 'i18n.js')),
        'files_in_static': os.listdir(app.static_folder) if os.path.exists(app.static_folder) else []
    })


@app.route('/debug/script-test')
def debug_script_test():
    """Test page to debug script loading"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Script Loading Test</title>
    </head>
    <body>
        <h1>Script Loading Test</h1>
        <div id="results"></div>

        <script>
            const results = document.getElementById('results');

            function log(msg) {
                const p = document.createElement('p');
                p.textContent = msg;
                results.appendChild(p);
                console.log(msg);
            }

            log('Starting test...');

            // Test 1: Load from /i18n.js
            const script1 = document.createElement('script');
            script1.src = '/i18n.js';
            script1.onload = () => log('✓ Loaded from /i18n.js');
            script1.onerror = () => log('✗ Failed to load from /i18n.js');
            document.head.appendChild(script1);

            // Test 2: Load from /static/i18n.js
            setTimeout(() => {
                const script2 = document.createElement('script');
                script2.src = '/static/i18n.js';
                script2.onload = () => log('✓ Loaded from /static/i18n.js');
                script2.onerror = () => log('✗ Failed to load from /static/i18n.js');
                document.head.appendChild(script2);
            }, 1000);

            // Test 3: Check if window.i18n exists after 2 seconds
            setTimeout(() => {
                log('window.i18n exists: ' + (typeof window.i18n !== 'undefined'));
                if (window.i18n) {
                    log('i18n.currentLang: ' + window.i18n.currentLang);
                }
            }, 2000);
        </script>
    </body>
    </html>
    """
    return html


@app.route('/debug/file-check')
def debug_file_check():
    """Check if i18n.js file exists and its content"""
    import os
    import hashlib

    file_path = os.path.join(app.static_folder, 'i18n.js')

    info = {
        'file_path': str(file_path),
        'exists': os.path.exists(file_path),
        'static_folder': str(app.static_folder),
        'static_url_path': app.static_url_path
    }

    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            content = f.read()
            info['size'] = len(content)
            info['md5'] = hashlib.md5(content).hexdigest()
            info['first_line'] = content[:100].decode('utf-8', errors='ignore')
            info['last_line'] = content[-100:].decode('utf-8', errors='ignore')

    return jsonify(info)



# CSRF token endpoint
@app.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    """Get CSRF token for API requests"""
    return jsonify({'csrf_token': generate_csrf()})


# Translation endpoint
@app.route('/api/translate', methods=['POST'])
@require_auth()
@limiter.limit("100 per hour")
def translate_text_endpoint():
    """Translate text for restaurant names"""
    try:
        data = request.json
        text = data.get('text')
        target = data.get('target', 'en')

        if not text:
            return jsonify({'error': 'Text required'}), 400

        # Map frontend language codes to Google Translate codes
        lang_map = {
            'he': 'iw',  # Hebrew
            'ar': 'ar',  # Arabic
            'ru': 'ru',  # Russian
            'en': 'en'  # English
        }

        google_lang = lang_map.get(target, target)
        translated = translate_text(text, google_lang)

        return jsonify({'translated': translated})

    except Exception as e:
        logger.error(f"Translation endpoint error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Translation failed'}), 500




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
        email = request.json.get('email', '').lower().strip()
        password = request.json.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400

        user = User.query.filter_by(email=email).first()

        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Use Flask-Login to log in user
        login_user(user, remember=True)

        # Set session for backward compatibility
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_role'] = user.role
        session.permanent = True

        # Log the login
        user.last_login = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role
            }
        })

    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_auth()
def logout():
    """User logout"""
    try:
        logout_user()
        session.clear()
        return jsonify({'message': 'Logged out successfully'})
    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Logout failed'}), 500


@app.route('/api/auth/check', methods=['GET'])
@login_required
def check_auth():
    """Check if user is authenticated"""
    return jsonify({
        'authenticated': True,
        'user_id': current_user.id,
        'email': current_user.email
    }), 200

# Profile endpoints
@app.route('/api/profile', methods=['GET'])
@require_auth()
def get_profile():
    """Get user profile"""
    try:
        user = request.current_user
        profile_data = {
            'id': user.id,
            'email': user.email,
            'name': user.email.split('@')[0],
            'location': user.profile.location if user.profile and hasattr(user.profile, 'location') else None,
            'bio': user.profile.bio if user.profile and hasattr(user.profile, 'bio') else None,
            'preferences': {
                'min_age': user.preferences.min_age if user.preferences and hasattr(user.preferences, 'min_age') else 18,
                'max_age': user.preferences.max_age if user.preferences and hasattr(user.preferences, 'max_age') else 99,
                'gender_preference': user.preferences.gender_preference if user.preferences and hasattr(user.preferences, 'gender_preference') else 'any',
                'interests': user.preferences.interests.split(',') if user.preferences and hasattr(user.preferences, 'interests') and user.preferences.interests else []
            }
        }
        return jsonify(profile_data)
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

# Restaurant endpoints with API integration
# Replace your get_restaurants() function in dating_backend.py with this:

@app.route('/api/restaurants', methods=['GET'])
def get_restaurants():
    """Get available restaurants from database and APIs"""
    try:
        # Get query parameters
        location = request.args.get('location', 'Tel Aviv')
        cuisine = request.args.get('cuisine')
        price_range = request.args.get('price_range')
        recommended = request.args.get('recommended', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))
        lang = request.args.get('lang', 'en')  # Get language preference here

        restaurants = []

        # First, get restaurants from database
        query = Restaurant.query.filter_by(is_active=True)

        if cuisine:
            query = query.filter(Restaurant.cuisine_type.ilike(f'%{cuisine}%'))
        if price_range:
            query = query.filter_by(price_range=int(price_range))

        # Get database restaurants
        db_restaurants = query.limit(limit // 2).all()

        # Format database restaurants
        for r in db_restaurants:
            available_tables = RestaurantTable.query.filter_by(
                restaurant_id=r.id, is_available=True
            ).count()

            # For database restaurants, translate name and cuisine if needed
            restaurant_name = r.name
            cuisine_type = r.cuisine_type

            if lang != 'en':
                restaurant_name = translate_text(r.name, lang)
                cuisine_type = translate_text(r.cuisine_type, lang)

            restaurants.append({
                'id': r.id,
                'name': restaurant_name,
                'cuisine': cuisine_type,
                'address': r.address,
                'price_range': '$' * (r.price_range or 1),
                'rating': r.rating or 4.0,
                'available_slots': available_tables * 4,
                'image_url': getattr(r, 'image_url', None) or '/static/images/restaurant-placeholder.jpg',
                'source': getattr(r, 'source', 'internal')
            })

        # If we need more restaurants or for recommendations, fetch from APIs
        if len(restaurants) < limit or recommended:
            try:
                logger.info(f"Fetching API restaurants for location: {location}")

                # FIX 8: Try Google Places API FIRST (better coverage for international)
                api_restaurants = []

                try:
                    api_restaurants = restaurant_api.search_restaurants_google(
                        location=location,
                        cuisine=cuisine
                    )
                    logger.info(f"Google API returned {len(api_restaurants)} restaurants")
                except Exception as google_error:
                    logger.error(f"Google API failed: {google_error}")

                # FIX 9: Only try Yelp if Google fails or returns few results
                if len(api_restaurants) < 5:  # If Google returned less than 5
                    try:
                        yelp_restaurants = restaurant_api.search_restaurants_yelp(
                            location=location,
                            cuisine=cuisine,
                            price=price_range
                        )
                        logger.info(f"Yelp API returned {len(yelp_restaurants)} restaurants")
                        # Combine with Google results
                        api_restaurants.extend(yelp_restaurants)
                    except Exception as yelp_error:
                        logger.error(f"Yelp API failed: {yelp_error}")

                # FIX 10: Enhanced mock restaurants with more variety
                if not api_restaurants:
                    logger.warning("All APIs failed, using enhanced mock restaurants")
                    api_restaurants = [
                        {
                            'external_id': 'ChIJ1-U0Qp1MHRURJFvgKIuvslw',
                            'name': 'Cafe Central',
                            'cuisine_type': 'International',
                            'address': 'Rothschild Blvd, Tel Aviv',
                            'price_range': 2,
                            'rating': 4.2,
                            'source': 'mock'
                        },
                        {
                            'external_id': 'ChIJ3fIA445LHRURFH_Ww1-rgMU',
                            'name': 'Bella Vista Restaurant',
                            'cuisine_type': 'Italian',
                            'address': 'Hayarkon St, Tel Aviv',
                            'price_range': 3,
                            'rating': 4.5,
                            'source': 'mock'
                        },
                        {
                            'external_id': 'ChIJkS1XOoRMHRURRyqhiUCrnxE',
                            'name': 'Tokyo Sushi House',
                            'cuisine_type': 'Japanese',
                            'address': 'Dizengoff St, Tel Aviv',
                            'price_range': 3,
                            'rating': 4.4,
                            'source': 'mock'
                        },
                        {
                            'external_id': 'ChIJW_PEYptMHRURb-4h9AYDN_w',
                            'name': 'Mediterranean Delights',
                            'cuisine_type': 'Mediterranean',
                            'address': 'Ibn Gabirol St, Tel Aviv',
                            'price_range': 2,
                            'rating': 4.3,
                            'source': 'mock'
                        },
                        {
                            'external_id': 'ChIJoSYW_oFLHRUROTeWytMUISo',
                            'name': 'American Bistro',
                            'cuisine_type': 'American',
                            'address': 'Allenby St, Tel Aviv',
                            'price_range': 2,
                            'rating': 4.1,
                            'source': 'mock'
                        },
                        {
                            'external_id': 'ChIJ2dL3yiVNHRURma-Gja8DSow',
                            'name': 'Italian Garden',
                            'cuisine_type': 'Italian',
                            'address': 'King George St, Tel Aviv',
                            'price_range': 3,
                            'rating': 4.6,
                            'source': 'mock'
                        },
                        {
                            'external_id': 'ChIJ1YYt7YNMHRURP03UUCeI3Do',
                            'name': 'French Corner',
                            'cuisine_type': 'French',
                            'address': 'Ben Yehuda St, Tel Aviv',
                            'price_range': 4,
                            'rating': 4.7,
                            'source': 'mock'
                        },
                        {
                            'external_id': 'ChIJ4bopMXZMHRURzCb29y_gXok',
                            'name': 'Asian Fusion',
                            'cuisine_type': 'Asian',
                            'address': 'Shenkin St, Tel Aviv',
                            'price_range': 3,
                            'rating': 4.4,
                            'source': 'mock'
                        }
                    ]

                # FIX 11: Cache restaurant data for individual lookups
                for api_restaurant in api_restaurants[:limit - len(restaurants)]:
                    restaurant_id = f"api_{api_restaurant.get('external_id', 'unknown')}"

                    # Cache this restaurant data for later individual lookups
                    cache_key = f"restaurant_{restaurant_id}"
                    cache_data = {
                        'name': api_restaurant.get('name', 'Unknown'),
                        'cuisine': api_restaurant.get('cuisine_type', 'International'),
                        'address': api_restaurant.get('address', ''),
                        'rating': api_restaurant.get('rating', 4.0),
                        'price_range': api_restaurant.get('price_range', 2),
                        'source': api_restaurant.get('source', 'api'),
                        'cached_at': datetime.utcnow().isoformat()
                    }

                    try:
                        cache.set(cache_key, cache_data)  # Cache for 24 hours
                        logger.info(f"Cached restaurant data for {restaurant_id}")
                    except Exception as cache_error:
                        logger.warning(f"Failed to cache restaurant {restaurant_id}: {cache_error}")

                    # For API restaurants, translate name and cuisine if needed
                    restaurant_name = api_restaurant.get('name', 'Unknown')
                    cuisine_type = api_restaurant.get('cuisine_type', 'International')

                    if lang != 'en':
                        restaurant_name = translate_text(restaurant_name, lang)
                        cuisine_type = translate_text(cuisine_type, lang)

                    restaurants.append({
                        'id': restaurant_id,
                        'name': restaurant_name,
                        'cuisine': cuisine_type,
                        'address': api_restaurant.get('address', ''),
                        'price_range': '$' * (api_restaurant.get('price_range', 2)),
                        'rating': api_restaurant.get('rating', 4.0),
                        'available_slots': 8,  # Default for API restaurants
                        'image_url': api_restaurant.get('image_url', '/static/images/restaurant-placeholder.jpg'),
                        'source': api_restaurant.get('source', 'api')
                    })

            except Exception as api_error:
                logger.warning(f"API restaurant fetch failed: {api_error}")

        logger.info(f"Returning {len(restaurants)} total restaurants")
        return jsonify(restaurants)

    except Exception as e:
        logger.error(f"Get restaurants error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get restaurants'}), 500


@app.route('/api/restaurants/<restaurant_id>/tables', methods=['GET'])  # Remove <int:>
def get_restaurant_tables(restaurant_id):
    """Get available tables for a restaurant"""
    try:
        # Handle API restaurants (string IDs starting with 'api_')
        if str(restaurant_id).startswith('api_'):
            # Return mock tables for API restaurants
            return jsonify([
                {'id': 1, 'table_number': '1', 'capacity': 2, 'location': 'window', 'is_available': True},
                {'id': 2, 'table_number': '2', 'capacity': 2, 'location': 'center', 'is_available': True},
                {'id': 3, 'table_number': '3', 'capacity': 2, 'location': 'corner', 'is_available': False}
            ])

        # Handle database restaurants (integer IDs)
        from services.restaurant_service import RestaurantService
        restaurant_service = RestaurantService(db, cache, logger)
        return restaurant_service.get_available_tables(int(restaurant_id), request.args)
    except ValueError:
        return jsonify({'error': 'Invalid restaurant ID'}), 400
    except Exception as e:
        logger.error(f"Get tables error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get tables'}), 500

@app.route('/api/restaurants/<restaurant_id>/slots', methods=['GET'])
def get_restaurant_slots(restaurant_id):
    """Get available time slots for a restaurant"""
    try:
        # Handle both API and database restaurants
        time_slots = [
            {'time': '12:00', 'available': True},
            {'time': '12:30', 'available': True},
            {'time': '13:00', 'available': False},
            {'time': '13:30', 'available': True},
            {'time': '18:00', 'available': True},
            {'time': '18:30', 'available': True},
            {'time': '19:00', 'available': True},
            {'time': '19:30', 'available': False},
            {'time': '20:00', 'available': True},
            {'time': '20:30', 'available': True}
        ]
        return jsonify(time_slots)
    except Exception as e:
        logger.error(f"Get slots error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get time slots'}), 500


@app.route('/api/restaurants/<restaurant_id>', methods=['GET'])
def get_restaurant(restaurant_id):
    """Get restaurant details"""
    try:
        lang = request.args.get('lang', 'en')  # Get language parameter

        # Handle API restaurants (prefixed with 'api_')
        if str(restaurant_id).startswith('api_'):
            # Check cache first (populated by get_restaurants())
            cache_key = f"restaurant_{restaurant_id}"
            cached_data = cache.get(cache_key)

            if cached_data and isinstance(cached_data, dict):
                logger.info(f"Found cached restaurant data for {restaurant_id}")

                # Translate cached data if needed
                restaurant_name = cached_data.get('name', 'Restaurant')
                cuisine_type = cached_data.get('cuisine', 'International')

                if lang != 'en':
                    restaurant_name = translate_text(restaurant_name, lang)
                    cuisine_type = translate_text(cuisine_type, lang)

                return jsonify({
                    'id': restaurant_id,
                    'name': restaurant_name,
                    'cuisine': cuisine_type,
                    'address': cached_data.get('address', 'Address not available'),
                    'price_range': '$' * cached_data.get('price_range', 2),
                    'rating': cached_data.get('rating', 4.0),
                    'available_tables': 3,
                    'source': cached_data.get('source', 'api')
                })

            # Extract the actual place ID (remove 'api_' prefix)
            place_id = restaurant_id[4:]  # Remove 'api_' prefix

            # Try Google Places API with better error handling
            try:
                import requests
                google_api_key = os.getenv('GOOGLE_PLACES_API_KEY')
                if google_api_key:
                    google_url = f"https://maps.googleapis.com/maps/api/place/details/json"
                    params = {
                        'place_id': place_id,
                        'fields': 'name,formatted_address,rating,price_level,types',
                        'key': google_api_key
                    }

                    response = requests.get(google_url, params=params, timeout=5)
                    logger.info(f"Google Places API response status: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"Google Places API status: {data.get('status')}")

                        if data.get('status') == 'OK' and 'result' in data:
                            place = data['result']

                            # Map price_level to readable format
                            price_map = {0: '$', 1: '$', 2: '$$', 3: '$$$', 4: '$$$$'}
                            price_range = price_map.get(place.get('price_level', 2), '$$')

                            # Determine cuisine from types
                            cuisine = 'International'
                            types = place.get('types', [])
                            if 'italian_restaurant' in types:
                                cuisine = 'Italian'
                            elif 'chinese_restaurant' in types:
                                cuisine = 'Chinese'
                            elif 'mexican_restaurant' in types:
                                cuisine = 'Mexican'
                            elif 'japanese_restaurant' in types:
                                cuisine = 'Japanese'
                            elif 'indian_restaurant' in types:
                                cuisine = 'Indian'
                            elif 'thai_restaurant' in types:
                                cuisine = 'Thai'
                            elif 'french_restaurant' in types:
                                cuisine = 'French'

                            # Translate if needed
                            restaurant_name = place.get('name', 'Restaurant')
                            cuisine_type = cuisine

                            if lang != 'en':
                                restaurant_name = translate_text(restaurant_name, lang)
                                cuisine_type = translate_text(cuisine_type, lang)

                            restaurant_data = {
                                'id': restaurant_id,
                                'name': restaurant_name,
                                'cuisine': cuisine_type,
                                'address': place.get('formatted_address', 'Address not available'),
                                'price_range': price_range,
                                'rating': place.get('rating', 4.0),
                                'available_tables': 3
                            }

                            # Cache this data for future use
                            try:
                                cache_data = {
                                    'name': place.get('name', 'Restaurant'),  # Cache original name
                                    'cuisine': cuisine,  # Cache original cuisine
                                    'address': place.get('formatted_address', 'Address not available'),
                                    'rating': place.get('rating', 4.0),
                                    'price_range': place.get('price_level', 2),
                                    'source': 'google',
                                    'cached_at': datetime.utcnow().isoformat()
                                }
                                cache.set(cache_key, cache_data)
                                logger.info(f"Cached Google Places data for {restaurant_id}")
                            except Exception as cache_error:
                                logger.warning(f"Failed to cache Google data: {cache_error}")

                            return jsonify(restaurant_data)
                        else:
                            logger.warning(f"Google Places API error status: {data.get('status')} for {place_id}")
                    else:
                        logger.error(f"Google Places API HTTP error: {response.status_code}")
                        logger.error(f"Response: {response.text}")
            except Exception as e:
                logger.warning(f"Google Places API failed for {place_id}: {e}")

            # Enhanced fallback lookup table with more restaurants
            restaurant_lookup = {
                'ChIJ1-U0Qp1MHRURJFvgKIuvslw': {
                    'name': 'Cafe Central',
                    'cuisine': 'International',
                    'address': 'Rothschild Blvd, Tel Aviv',
                    'rating': 4.2
                },
                'ChIJ3fIA445LHRURFH_Ww1-rgMU': {
                    'name': 'Bella Vista Restaurant',
                    'cuisine': 'Italian',
                    'address': 'Hayarkon St, Tel Aviv',
                    'rating': 4.5
                },
                'ChIJkS1XOoRMHRURRyqhiUCrnxE': {
                    'name': 'Tokyo Sushi House',
                    'cuisine': 'Japanese',
                    'address': 'Dizengoff St, Tel Aviv',
                    'rating': 4.4
                },
                'ChIJW_PEYptMHRURb-4h9AYDN_w': {
                    'name': 'Mediterranean Delights',
                    'cuisine': 'Mediterranean',
                    'address': 'Ibn Gabirol St, Tel Aviv',
                    'rating': 4.3
                },
                'ChIJoSYW_oFLHRUROTeWytMUISo': {
                    'name': 'American Bistro',
                    'cuisine': 'American',
                    'address': 'Allenby St, Tel Aviv',
                    'rating': 4.1
                },
                'ChIJ2dL3yiVNHRURma-Gja8DSow': {
                    'name': 'Italian Garden',
                    'cuisine': 'Italian',
                    'address': 'King George St, Tel Aviv',
                    'rating': 4.6
                },
                'ChIJ1YYt7YNMHRURP03UUCeI3Do': {
                    'name': 'French Corner',
                    'cuisine': 'French',
                    'address': 'Ben Yehuda St, Tel Aviv',
                    'rating': 4.7
                },
                'ChIJ4bopMXZMHRURzCb29y_gXok': {
                    'name': 'Asian Fusion',
                    'cuisine': 'Asian',
                    'address': 'Shenkin St, Tel Aviv',
                    'rating': 4.4
                },
                'ChIJzTn1pCJNHRURQsMg5TCDr6c': {
                    'name': 'Mexican Cantina',
                    'cuisine': 'Mexican',
                    'address': 'Florentin, Tel Aviv',
                    'rating': 4.2
                },
                'ChIJt-3lqYBLHRURN_cghNWVlz0': {
                    'name': 'Steakhouse Prime',
                    'cuisine': 'American',
                    'address': 'Ramat Aviv, Tel Aviv',
                    'rating': 4.5
                },
                'ChIJh3glpn5MHRUR6jwTBg3yMK4': {
                    'name': 'Seafood Palace',
                    'cuisine': 'Seafood',
                    'address': 'Jaffa Port, Tel Aviv',
                    'rating': 4.3
                }
            }

            restaurant_info = restaurant_lookup.get(place_id)
            if restaurant_info:
                # Translate if needed
                restaurant_name = restaurant_info['name']
                cuisine_type = restaurant_info['cuisine']

                if lang != 'en':
                    restaurant_name = translate_text(restaurant_name, lang)
                    cuisine_type = translate_text(cuisine_type, lang)

                restaurant_data = {
                    'id': restaurant_id,
                    'name': restaurant_name,
                    'cuisine': cuisine_type,
                    'address': restaurant_info['address'],
                    'price_range': '$$',
                    'rating': restaurant_info['rating'],
                    'available_tables': 3
                }

                # Cache the lookup table data too
                try:
                    cache_data = {
                        'name': restaurant_info['name'],  # Cache original name
                        'cuisine': restaurant_info['cuisine'],  # Cache original cuisine
                        'address': restaurant_info['address'],
                        'rating': restaurant_info['rating'],
                        'price_range': 2,
                        'source': 'lookup',
                        'cached_at': datetime.utcnow().isoformat()
                    }
                    cache.set(cache_key, cache_data)
                except Exception as cache_error:
                    logger.warning(f"Failed to cache lookup data: {cache_error}")

                return jsonify(restaurant_data)
            else:
                # Last resort fallback - still translate
                restaurant_name = 'Local Restaurant'
                cuisine_type = 'International'

                if lang != 'en':
                    restaurant_name = translate_text(restaurant_name, lang)
                    cuisine_type = translate_text(cuisine_type, lang)

                return jsonify({
                    'id': restaurant_id,
                    'name': restaurant_name,
                    'cuisine': cuisine_type,
                    'address': 'Tel Aviv, Israel',
                    'price_range': '$$',
                    'rating': 4.0,
                    'available_tables': 3
                })

        # Handle database restaurants
        try:
            restaurant = Restaurant.query.get(int(restaurant_id))
            if not restaurant:
                return jsonify({'error': 'Restaurant not found'}), 404

            # Translate database restaurant if needed
            restaurant_name = restaurant.name
            cuisine_type = restaurant.cuisine_type

            if lang != 'en':
                restaurant_name = translate_text(restaurant_name, lang)
                cuisine_type = translate_text(cuisine_type, lang)

            return jsonify({
                'id': restaurant.id,
                'name': restaurant_name,
                'cuisine': cuisine_type,
                'address': restaurant.address,
                'price_range': '$' * (restaurant.price_range or 1),
                'rating': restaurant.rating or 4.0,
                'available_tables': RestaurantTable.query.filter_by(
                    restaurant_id=restaurant.id, is_available=True
                ).count()
            })
        except ValueError:
            return jsonify({'error': 'Invalid restaurant ID'}), 400

    except Exception as e:
        logger.error(f"Get restaurant error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get restaurant'}), 500


# API endpoint to refresh restaurants from APIs
@app.route('/api/admin/restaurants/refresh', methods=['POST'])
@require_auth(roles=['admin'])
def refresh_restaurants():
    """Refresh restaurant database from APIs"""
    try:
        # This would be called periodically or by admin
        from init_db import update_restaurants_from_api
        update_restaurants_from_api()
        return jsonify({'message': 'Restaurants refreshed successfully'})
    except Exception as e:
        logger.error(f"Refresh restaurants error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to refresh restaurants'}), 500

# Matching endpoints
@app.route('/api/matches', methods=['GET'])
@require_auth()
def get_matches():
    """Get user's matches"""
    try:
        from services.matching_service import MatchingService

        return matching_service.get_user_matches(request.current_user.id)
    except Exception as e:
        logger.error(f"Get matches error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get matches'}), 500

@app.route('/api/matches/suggestions', methods=['POST'])
@require_auth()
def get_match_suggestions():
    """Get suggested matches for a time slot"""
    try:
        from services.matching_service import MatchingService

        return matching_service.get_suggestions(request.current_user.id, request.json)
    except Exception as e:
        logger.error(f"Get suggestions error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get suggestions'}), 500

@app.route('/api/matches/browse', methods=['GET'])
@require_auth()
def browse_matches():
    """Browse potential matches for available tables"""
    try:
        from services.matching_service import MatchingService

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

        result = matching_service.request_match(request.current_user.id, request.json)

        # Send WebSocket notification for new match
        if hasattr(result, 'json') and result.status_code == 201:
            websocket_service.notify_new_match(
                request.json.get('match_user_id'),
                {'type': 'match_request', 'from_user': request.current_user.id}
            )

        return result
    except Exception as e:
        logger.error(f"Request match error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to request match'}), 500

@app.route('/api/matches/<int:match_id>/accept', methods=['POST'])
@require_auth()
def accept_match(match_id):
    """Accept a match request"""
    try:
        from services.matching_service import MatchingService

        return matching_service.respond_to_match(request.current_user.id, match_id, {'accept': True})
    except Exception as e:
        logger.error(f"Accept match error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to accept match'}), 500

@app.route('/api/matches/<int:match_id>/decline', methods=['POST'])
@require_auth()
def decline_match(match_id):
    """Decline a match request"""
    try:
        from services.matching_service import MatchingService

        return matching_service.respond_to_match(request.current_user.id, match_id, {'accept': False})
    except Exception as e:
        logger.error(f"Decline match error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to decline match'}), 500

# Date endpoints
@app.route('/api/dates/upcoming', methods=['GET'])
@require_auth()
def get_upcoming_dates():
    """Get upcoming dates"""
    try:
        return jsonify([])
    except Exception as e:
        logger.error(f"Get upcoming dates error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get upcoming dates'}), 500

@app.route('/api/dates/history', methods=['GET'])
@require_auth()
def get_date_history():
    """Get date history"""
    try:
        from services.date_service import DateService
        date_service = DateService(db, logger)
        return date_service.get_date_history(request.current_user.id)
    except Exception as e:
        logger.error(f"Get date history error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get date history'}), 500

@app.route('/api/dates/<int:date_id>', methods=['GET'])
@require_auth()
def get_date_details(date_id):
    """Get date details"""
    try:
        from services.date_service import DateService
        date_service = DateService(db, logger)
        return date_service.get_date_details(request.current_user.id, date_id)
    except Exception as e:
        logger.error(f"Get date details error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get date details'}), 500

@app.route('/api/dates/<int:date_id>/rate', methods=['POST'])
@require_auth()
def rate_date(date_id):
    """Rate a date"""
    try:
        from services.feedback_service import FeedbackService
        feedback_service = FeedbackService(db, logger)
        return feedback_service.rate_date(request.current_user.id, date_id, request.json)
    except Exception as e:
        logger.error(f"Rate date error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to rate date'}), 500

# User stats
@app.route('/api/user/stats', methods=['GET'])
@require_auth()
def get_user_stats():
    """Get user statistics"""
    try:
        stats = {
            'total_dates': 0,
            'active_matches': 0,
            'success_rate': 0,
            'pending_matches': 0
        }
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Get stats error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get statistics'}), 500

# Settings
@app.route('/api/settings', methods=['PUT'])
@require_auth()
def update_settings():
    """Update user settings"""
    try:
        from services.settings_service import SettingsService
        settings_service = SettingsService(db, logger)
        return settings_service.update_settings(request.current_user.id, request.json)
    except Exception as e:
        logger.error(f"Update settings error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to update settings'}), 500

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

# Password reset endpoints
@app.route('/api/auth/forgot-password', methods=['POST'])
@limiter.limit("5 per hour")
def forgot_password():
    """Send password reset email"""
    try:
        email = request.json.get('email', '').lower().strip()

        if not email or not validate_email(email):
            return jsonify({'error': 'Invalid email address'}), 400

        user = User.query.filter_by(email=email).first()

        # Always return success to prevent email enumeration
        if user:
            # Generate reset token
            serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
            reset_token = serializer.dumps(user.email, salt='password-reset-salt')

            # Store token in user record (you'll need to add reset_token field to User model)
            user.reset_token = reset_token
            user.reset_token_created = datetime.utcnow()
            db.session.commit()

            # Send email (simplified version)
            reset_url = f"{request.host_url}reset-password.html?token={reset_token}"

            # TODO: Implement actual email sending
            logger.info(f"Password reset link for {email}: {reset_url}")

            # In production, you'd use email_manager to send the email
            # email_manager.send_password_reset_email(user.email, reset_url)

        return jsonify({
            'success': True,
            'message': 'If an account exists with that email, you will receive password reset instructions.'
        })

    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to process request'}), 500

@app.route('/api/auth/reset-password', methods=['POST'])
@limiter.limit("5 per hour")
def reset_password():
    """Reset password with token"""
    try:
        token = request.json.get('token')
        new_password = request.json.get('password')

        if not token or not new_password:
            return jsonify({'error': 'Token and password required'}), 400

        if len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400

        # Verify token
        serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        try:
            email = serializer.loads(token, salt='password-reset-salt', max_age=3600)  # 1 hour expiry
        except SignatureExpired:
            return jsonify({'error': 'Reset link has expired'}), 400
        except:
            return jsonify({'error': 'Invalid reset link'}), 400

        # Find user and update password
        user = User.query.filter_by(email=email, reset_token=token).first()
        if not user:
            return jsonify({'error': 'Invalid reset link'}), 400

        # Update password
        user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.reset_token = None
        user.reset_token_created = None
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Password updated successfully'
        })

    except Exception as e:
        logger.error(f"Reset password error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to reset password'}), 500


# OAuth endpoints
@app.route('/auth/google')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/auth/google/callback')
def google_callback():
    token = google.authorize_access_token()
    user_info = token['userinfo']

    # Check if user exists or create new user
    user = User.query.filter_by(email=user_info['email']).first()
    if not user:
        user = User(
            email=user_info['email'],
            password_hash=bcrypt.generate_password_hash('oauth_user').decode('utf-8'),
            is_verified=True,
            role='user'
        )
        db.session.add(user)
        db.session.commit()

    login_user(user, remember=True)
    session['user_id'] = user.id
    session['user_email'] = user.email
    session['user_role'] = user.role
    session.permanent = True

    return redirect('/dashboard.html')


@app.route('/auth/facebook')
def facebook_login():
    redirect_uri = url_for('facebook_callback', _external=True)
    return facebook.authorize_redirect(redirect_uri)


@app.route('/auth/facebook/callback')
def facebook_callback():
    token = facebook.authorize_access_token()
    resp = facebook.get('me?fields=id,name,email', token=token)
    user_info = resp.json()

    # Check if user exists or create new user
    user = User.query.filter_by(email=user_info['email']).first()
    if not user:
        user = User(
            email=user_info['email'],
            password_hash=bcrypt.generate_password_hash('oauth_user').decode('utf-8'),
            is_verified=True,
            role='user'
        )
        db.session.add(user)
        db.session.commit()

    login_user(user, remember=True)
    session['user_id'] = user.id
    session['user_email'] = user.email
    session['user_role'] = user.role
    session.permanent = True

    return redirect('/dashboard.html')


# Restaurant authentication endpoints
@app.route('/api/restaurant-auth/register', methods=['POST'])
@limiter.limit("5 per hour")
def restaurant_register():
    """Register a restaurant account"""
    try:
        data = request.json

        # Validate required fields
        required_fields = ['name', 'email', 'password', 'address', 'cuisine_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        # Check if restaurant email already exists
        existing = Restaurant.query.filter_by(owner_email=data['email']).first()
        if existing:
            return jsonify({'error': 'Restaurant with this email already exists'}), 400

        # Create restaurant
        restaurant = Restaurant(
            name=data['name'],
            owner_email=data['email'],
            owner_password_hash=bcrypt.generate_password_hash(data['password']).decode('utf-8'),
            address=data['address'],
            cuisine_type=data['cuisine_type'],
            is_partner=True,
            is_active=True,
            rating=0.0,
            price_range=2
        )

        db.session.add(restaurant)
        db.session.commit()

        return jsonify({'message': 'Restaurant registered successfully', 'id': restaurant.id}), 201

    except Exception as e:
        logger.error(f"Restaurant registration error: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500


@app.route('/api/restaurant-auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def restaurant_login():
    """Restaurant login"""
    try:
        data = request.json
        email = data.get('email', '').lower().strip()
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400

        # Find restaurant by owner email
        restaurant = Restaurant.query.filter_by(owner_email=email).first()

        if not restaurant:
            return jsonify({'error': 'Invalid credentials'}), 401

        # Use the Restaurant model's check_password method
        if not restaurant.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Set session for restaurant owner
        session['restaurant_id'] = restaurant.id
        session['restaurant_email'] = restaurant.owner_email
        session.permanent = True

        return jsonify({
            'success': True,
            'restaurant': {
                'id': restaurant.id,
                'name': restaurant.name,
                'email': restaurant.owner_email
            }
        })

    except Exception as e:
        logger.error(f"Restaurant login error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Login failed'}), 500



# === STATIC FILES ===
@app.route('/')
def index():
    """Serve the main landing page"""
    return send_file('static/index.html')

@app.route('/login.html')
def login_page():
    """Serve the login page"""
    return send_file('static/login.html')

@app.route('/dashboard.html')
def dashboard():
    """Serve the dashboard"""
    return send_file('static/dashboard.html')

@app.route('/restaurants.html')
def restaurants_page():
    """Serve the restaurant portal page"""
    return send_file('static/restaurants.html')

@app.route('/restaurant-dashboard.html')
def restaurant_dashboard():
    """Serve the restaurant dashboard"""
    return send_file('static/restaurant-dashboard.html')

@app.route('/signup.html')
def signup_page():
    """Serve the signup page"""
    return send_file('static/signup.html')

# === DYNAMIC IMAGE GENERATION ===
@app.route('/static/images/default-avatar.jpg')
def default_avatar():
    """Generate a default avatar image"""
    from PIL import Image, ImageDraw
    import io

    img = Image.new('RGB', (200, 200), color='#e74c3c')
    draw = ImageDraw.Draw(img)

    try:
        draw.text((100, 100), "?", fill='white', anchor="mm")
    except:
        draw.text((90, 80), "?", fill='white')

    img_io = io.BytesIO()
    img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)

    return send_file(img_io, mimetype='image/jpeg')

@app.route('/static/images/restaurant-placeholder.jpg')
def restaurant_placeholder():
    """Generate a placeholder restaurant image"""
    from PIL import Image, ImageDraw
    import io

    img = Image.new('RGB', (400, 300), color='#f0f0f0')
    draw = ImageDraw.Draw(img)

    draw.rectangle([150, 100, 250, 200], fill='#e74c3c')
    draw.text((200, 220), "Restaurant", fill='#666', anchor="mm")

    img_io = io.BytesIO()
    img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)

    return send_file(img_io, mimetype='image/jpeg')

@app.route('/static/images/couple-dinner.jpg')
def couple_dinner():
    """Generate a couple dinner placeholder image"""
    from PIL import Image, ImageDraw
    import io

    img = Image.new('RGB', (600, 400), color='#fff5f5')
    draw = ImageDraw.Draw(img)

    # Draw simple shapes to represent couple dining
    # Table
    draw.ellipse([200, 200, 400, 280], fill='#8B4513')
    # Two circles for people
    draw.ellipse([180, 150, 220, 190], fill='#e74c3c')
    draw.ellipse([380, 150, 420, 190], fill='#e74c3c')

    img_io = io.BytesIO()
    img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)

    return send_file(img_io, mimetype='image/jpeg')

@app.route('/favicon.ico')
def favicon():
    """Generate a simple favicon"""
    from PIL import Image, ImageDraw
    import io

    img = Image.new('RGBA', (32, 32), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw a heart shape
    draw.ellipse([4, 4, 16, 16], fill='#e74c3c')
    draw.ellipse([16, 4, 28, 16], fill='#e74c3c')
    draw.polygon([(16, 24), (4, 12), (28, 12)], fill='#e74c3c')

    img_io = io.BytesIO()
    img.save(img_io, 'ICO')
    img_io.seek(0)

    return send_file(img_io, mimetype='image/x-icon')


@app.route('/i18n.js')
def serve_i18n_root():
    """Serve i18n.js from root"""
    import os
    file_path = os.path.join(app.static_folder, 'i18n.js')

    logger.info(f"i18n.js requested")
    logger.info(f"Looking for file at: {file_path}")
    logger.info(f"File exists: {os.path.exists(file_path)}")

    if os.path.exists(file_path):
        logger.info(f"File size: {os.path.getsize(file_path)} bytes")
        return send_file(file_path, mimetype='application/javascript')
    else:
        logger.error(f"File not found at {file_path}")
        return "File not found", 404


@app.route('/static/i18n.js')
def serve_i18n_static():
    """Serve i18n.js from static path"""
    import os
    file_path = os.path.join(app.static_folder, 'i18n.js')

    logger.info(f"static/i18n.js requested")
    logger.info(f"Looking for file at: {file_path}")

    if os.path.exists(file_path):
        # Read file content to verify it's not empty
        with open(file_path, 'r') as f:
            content = f.read()
            logger.info(f"File content length: {len(content)}")
            logger.info(f"First 100 chars: {content[:100]}")

        response = make_response(send_file(file_path, mimetype='application/javascript'))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    else:
        return "File not found", 404



# Following endpoints
@app.route('/api/users/follow', methods=['POST'])
@require_auth()
def follow_user():
    """Follow another user"""
    try:
        from services.following_service import FollowingService
        following_service = FollowingService(db, cache, logger)
        return following_service.follow_user(request.current_user.id, request.json.get('user_id'))
    except Exception as e:
        logger.error(f"Follow user error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to follow user'}), 500


@app.route('/api/users/unfollow', methods=['POST'])
@require_auth()
def unfollow_user():
    """Unfollow a user"""
    try:
        from services.following_service import FollowingService
        following_service = FollowingService(db, cache, logger)
        return following_service.unfollow_user(request.current_user.id, request.json.get('user_id'))
    except Exception as e:
        logger.error(f"Unfollow user error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to unfollow user'}), 500


@app.route('/api/restaurants/follow', methods=['POST'])
@require_auth()
@limiter.limit("10 per minute")
def follow_restaurant():
    """Follow a restaurant"""
    try:
        from services.following_service import FollowingService
        following_service = FollowingService(db, cache, logger)
        return following_service.follow_restaurant(request.current_user.id, request.json.get('restaurant_id'))
    except Exception as e:
        logger.error(f"Follow restaurant error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to follow restaurant'}), 500


@app.route('/api/restaurants/unfollow', methods=['POST'])
@require_auth()
def unfollow_restaurant():
    """Unfollow a restaurant"""
    try:
        user = request.current_user
        restaurant_id = request.json.get('restaurant_id')

        # Handle both internal and API restaurants
        if str(restaurant_id).startswith('api_'):
            restaurant = Restaurant.query.filter_by(external_id=restaurant_id[4:]).first()
        else:
            restaurant = Restaurant.query.get(int(restaurant_id))

        if not restaurant:
            return jsonify({'error': 'Restaurant not found'}), 404

        user.unfollow_restaurant(restaurant)
        db.session.commit()

        return jsonify({'message': f'Unfollowed {restaurant.name}'}), 200
    except Exception as e:
        logger.error(f"Unfollow restaurant error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to unfollow restaurant'}), 500


@app.route('/api/users/following', methods=['GET'])
@require_auth()
def get_user_following():
    """Get users that current user is following"""
    try:
        from services.following_service import FollowingService
        following_service = FollowingService(db, cache, logger)
        return following_service.get_user_following(request.current_user.id)
    except Exception as e:
        logger.error(f"Get following error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get following list'}), 500


@app.route('/api/users/restaurants/following', methods=['GET'])
@require_auth()
def get_followed_restaurants():
    """Get restaurants that current user follows"""
    try:
        from services.following_service import FollowingService
        following_service = FollowingService(db, cache, logger)
        return following_service.get_followed_restaurants(request.current_user.id)
    except Exception as e:
        logger.error(f"Get followed restaurants error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get followed restaurants'}), 500


@app.route('/api/restaurants/all', methods=['GET'])
@require_auth()
def get_all_restaurants_for_following():
    """Get all restaurants for following purposes"""
    try:
        restaurants = Restaurant.query.filter_by(is_active=True).all()
        result = []

        for restaurant in restaurants:
            is_following = request.current_user.is_following_restaurant(restaurant)
            result.append({
                'id': restaurant.id,
                'name': restaurant.name,
                'cuisine_type': restaurant.cuisine_type,
                'address': restaurant.address,
                'rating': float(restaurant.rating) if restaurant.rating else 0.0,
                'price_range': '$' * (restaurant.price_range or 1),
                'is_following': is_following,
                'follower_count': restaurant.followers.count()
            })

        return jsonify(result)
    except Exception as e:
        logger.error(f"Get all restaurants error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get restaurants'}), 500


# Time preferences endpoints
@app.route('/api/time-preferences', methods=['POST'])
@require_auth()
@limiter.limit("20 per hour")
def add_time_preference():
    """Add a time preference"""
    try:
        from services.time_preference_service import TimePreferenceService
        time_service = TimePreferenceService(db, cache, logger)
        return time_service.add_time_preference(request.current_user.id, request.json)
    except Exception as e:
        logger.error(f"Add time preference error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to add time preference'}), 500


@app.route('/api/time-preferences', methods=['GET'])
@require_auth()
def get_time_preferences():
    """Get user's time preferences"""
    try:
        from services.time_preference_service import TimePreferenceService
        time_service = TimePreferenceService(db, cache, logger)
        include_matches = request.args.get('include_matches', 'false').lower() == 'true'
        return time_service.get_user_preferences(request.current_user.id, include_matches)
    except Exception as e:
        logger.error(f"Get time preferences error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get time preferences'}), 500


@app.route('/api/time-preferences/<int:preference_id>', methods=['DELETE'])
@require_auth()
def remove_time_preference(preference_id):
    """Remove a time preference"""
    try:
        from services.time_preference_service import TimePreferenceService
        time_service = TimePreferenceService(db, cache, logger)
        return time_service.remove_time_preference(request.current_user.id, preference_id)
    except Exception as e:
        logger.error(f"Remove time preference error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to remove time preference'}), 500


@app.route('/api/time-preferences/matches', methods=['GET'])
@require_auth()
def get_time_preference_matches():
    """Get users with matching time preferences from followed users"""
    try:
        from services.time_preference_service import TimePreferenceService
        time_service = TimePreferenceService(db, cache, logger)
        return time_service.get_matching_users(request.current_user.id)
    except Exception as e:
        logger.error(f"Get time preference matches error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get matches'}), 500





@app.route('/api/restaurant-management/matches', methods=['GET'])
@limiter.limit("100 per hour")
def get_restaurant_matches():
    """Get match requests for restaurant (requires restaurant authentication)"""
    try:
        # This would need restaurant-specific authentication
        restaurant_id = request.args.get('restaurant_id')
        date_filter = request.args.get('date_filter')

        if not restaurant_id:
            return jsonify({'error': 'Restaurant ID required'}), 400

        return restaurant_management_service.get_match_requests(int(restaurant_id), date_filter)
    except Exception as e:
        logger.error(f"Get restaurant matches error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get matches'}), 500


@app.route('/api/restaurant-management/stats', methods=['GET'])
@limiter.limit("100 per hour")
def get_restaurant_stats():
    """Get restaurant statistics"""
    try:
        restaurant_id = request.args.get('restaurant_id')

        if not restaurant_id:
            return jsonify({'error': 'Restaurant ID required'}), 400

        return restaurant_management_service.get_restaurant_stats(int(restaurant_id))
    except Exception as e:
        logger.error(f"Get restaurant stats error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get statistics'}), 500


# Add these endpoints AFTER get_restaurant_stats endpoint (around line 1770)

@app.route('/api/restaurant-management/analytics/comprehensive', methods=['GET'])
@limiter.limit("100 per hour")
def get_comprehensive_analytics():
    """Get comprehensive analytics with charts data"""
    try:
        restaurant_id = request.args.get('restaurant_id')
        period = request.args.get('period', 'week')

        if not restaurant_id:
            return jsonify({'error': 'Restaurant ID required'}), 400

        return restaurant_management_service.get_comprehensive_analytics(int(restaurant_id), period)
    except Exception as e:
        logger.error(f"Get comprehensive analytics error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get comprehensive analytics'}), 500


@app.route('/api/restaurant-management/demographics', methods=['GET'])
@limiter.limit("50 per hour")
def get_customer_demographics():
    """Get customer demographics"""
    try:
        restaurant_id = request.args.get('restaurant_id')

        if not restaurant_id:
            return jsonify({'error': 'Restaurant ID required'}), 400

        return restaurant_management_service.get_customer_demographics(int(restaurant_id))
    except Exception as e:
        logger.error(f"Get demographics error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get demographics'}), 500


@app.route('/api/restaurant-management/revenue', methods=['GET'])
@limiter.limit("50 per hour")
def get_revenue_analytics():
    """Get revenue analytics"""
    try:
        restaurant_id = request.args.get('restaurant_id')
        period = request.args.get('period', 'month')

        if not restaurant_id:
            return jsonify({'error': 'Restaurant ID required'}), 400

        return restaurant_management_service.get_revenue_analytics(int(restaurant_id), period)
    except Exception as e:
        logger.error(f"Get revenue analytics error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get revenue analytics'}), 500


# Booking creation endpoint for when users make restaurant bookings
@app.route('/api/bookings/create', methods=['POST'])
@require_auth()
@limiter.limit("10 per hour")
def create_restaurant_booking():
    """Create a restaurant booking from user interface"""
    try:
        data = request.json

        # Validate required fields
        required_fields = ['restaurant_id', 'match_user_id', 'booking_datetime']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        # Create booking entry
        from models.restaurant_management import RestaurantBooking
        booking = RestaurantBooking(
            restaurant_id=int(data['restaurant_id']),
            user1_id=request.current_user.id,
            user2_id=int(data['match_user_id']),
            booking_datetime=datetime.fromisoformat(data['booking_datetime']),
            status='pending',
            party_size=data.get('party_size', 2),
            special_requests=data.get('special_requests', '')
        )

        db.session.add(booking)
        db.session.commit()

        return jsonify({
            'success': True,
            'booking_id': booking.id,
            'message': 'Booking request sent to restaurant'
        }), 201

    except Exception as e:
        logger.error(f"Create booking error: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Failed to create booking'}), 500


@app.route('/api/bookings/<int:booking_id>/rate', methods=['POST'])
@require_auth()
@limiter.limit("20 per hour")
def rate_restaurant_booking():
    """Rate a completed restaurant booking"""
    try:
        booking = RestaurantBooking.query.get(booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        # Check if user was part of this booking
        if request.current_user.id not in [booking.user1_id, booking.user2_id]:
            return jsonify({'error': 'Unauthorized'}), 403

        if booking.status != 'completed':
            return jsonify({'error': 'Can only rate completed bookings'}), 400

        data = request.json
        rating = data.get('rating')
        review = data.get('review', '')

        if not rating or rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400

        # Create or update restaurant rating
        from models.feedback import DateFeedback
        feedback = DateFeedback(
            booking_id=booking_id,
            user_id=request.current_user.id,
            restaurant_id=booking.restaurant_id,
            rating=rating,
            review=review
        )

        db.session.add(feedback)

        # Update restaurant average rating
        restaurant = Restaurant.query.get(booking.restaurant_id)
        if restaurant:
            # Calculate new average rating
            all_ratings = DateFeedback.query.filter_by(restaurant_id=restaurant.id).all()
            avg_rating = sum(r.rating for r in all_ratings) / len(all_ratings) if all_ratings else rating
            restaurant.rating = round(avg_rating, 1)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Rating submitted successfully'
        })

    except Exception as e:
        logger.error(f"Rate booking error: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Failed to submit rating'}), 500




# Add the CSRF exemption HERE (after the route definitions)
csrf.exempt(restaurant_register)
csrf.exempt(restaurant_login)


# Add these endpoints to dating_backend.py after your existing restaurant management endpoints

@app.route('/api/restaurant-management/bookings', methods=['GET'])
@limiter.limit("100 per hour")
def get_restaurant_bookings():
    """Get all bookings for a restaurant"""
    try:
        restaurant_id = request.args.get('restaurant_id')
        date_filter = request.args.get('date_filter')
        status_filter = request.args.get('status')

        if not restaurant_id:
            return jsonify({'error': 'Restaurant ID required'}), 400

        # Use the existing get_match_requests method (it handles bookings)
        return restaurant_management_service.get_match_requests(int(restaurant_id), date_filter)
    except Exception as e:
        logger.error(f"Get restaurant bookings error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get bookings'}), 500


@app.route('/api/restaurant-management/bookings/<int:booking_id>/status', methods=['PUT'])
@limiter.limit("50 per hour")
def update_booking_status():
    """Update booking status"""
    try:
        booking_id = request.view_args['booking_id']
        restaurant_id = request.json.get('restaurant_id')
        new_status = request.json.get('status')

        if not restaurant_id or not new_status:
            return jsonify({'error': 'Restaurant ID and status required'}), 400

        valid_statuses = ['pending', 'confirmed', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return jsonify({'error': f'Status must be one of: {valid_statuses}'}), 400

        return restaurant_management_service.update_booking_status(int(restaurant_id), booking_id, new_status)
    except Exception as e:
        logger.error(f"Update booking status error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to update booking'}), 500


@app.route('/api/restaurant-management/analytics', methods=['GET'])
@limiter.limit("100 per hour")
def get_restaurant_analytics():
    """Get detailed analytics for restaurant"""
    try:
        restaurant_id = request.args.get('restaurant_id')
        period = request.args.get('period', 'week')  # week, month, year

        if not restaurant_id:
            return jsonify({'error': 'Restaurant ID required'}), 400

        return restaurant_management_service.get_analytics_data(int(restaurant_id), period)
    except Exception as e:
        logger.error(f"Get restaurant analytics error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get analytics'}), 500


@app.route('/api/restaurant-management/settings', methods=['GET'])
@limiter.limit("100 per hour")
def get_restaurant_management_settings():
    """Get restaurant settings"""
    try:
        restaurant_id = request.args.get('restaurant_id')

        if not restaurant_id:
            return jsonify({'error': 'Restaurant ID required'}), 400

        return restaurant_management_service.get_restaurant_settings(int(restaurant_id))
    except Exception as e:
        logger.error(f"Get restaurant settings error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get settings'}), 500


@app.route('/api/restaurant-management/settings', methods=['PUT'])
@limiter.limit("20 per hour")
def update_restaurant_management_settings():
    """Update restaurant settings"""
    try:
        restaurant_id = request.json.get('restaurant_id')

        if not restaurant_id:
            return jsonify({'error': 'Restaurant ID required'}), 400

        return restaurant_management_service.update_restaurant_settings(int(restaurant_id), request.json)
    except Exception as e:
        logger.error(f"Update restaurant settings error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to update settings'}), 500


@app.route('/api/restaurant-management/sample-data', methods=['POST'])
@limiter.limit("10 per hour")
def create_sample_restaurant_data():
    """Create sample bookings for testing (development only)"""
    try:
        if os.environ.get('PRODUCTION'):
            return jsonify({'error': 'Not available in production'}), 403

        restaurant_id = request.json.get('restaurant_id')

        if not restaurant_id:
            return jsonify({'error': 'Restaurant ID required'}), 400

        from services.restaurant_management_service import RestaurantManagementService
        from models.user import User
        restaurant_service = RestaurantManagementService(db, logger)

        # Get some test users
        users = User.query.limit(4).all()
        if len(users) < 2:
            return jsonify({'error': 'Need at least 2 users in database'}), 400

        # Create sample bookings
        sample_bookings = [
            {
                'user1_id': users[0].id,
                'user2_id': users[1].id,
                'datetime': (datetime.utcnow() + timedelta(days=1)).isoformat(),
            },
            {
                'user1_id': users[0].id,
                'user2_id': users[1].id if len(users) > 1 else users[0].id,
                'datetime': (datetime.utcnow() + timedelta(days=2)).isoformat(),
            }
        ]

        created_bookings = []
        for booking_data in sample_bookings:
            result = restaurant_service.create_sample_booking(
                int(restaurant_id),
                booking_data['user1_id'],
                booking_data['user2_id'],
                booking_data['datetime']
            )
            if result[1] == 200:
                created_bookings.append(result[0].get_json())

        return jsonify({
            'message': f'Created {len(created_bookings)} sample bookings',
            'bookings': created_bookings
        })
    except Exception as e:
        logger.error(f"Create sample data error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to create sample data'}), 500








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

# === INITIALIZATION ===
def initialize_database():
    """Initialize database with default data"""
    with app.app_context():
        # Import all models to ensure they're registered with SQLAlchemy
        from models.user import User
        from models.restaurant import Restaurant, RestaurantTable
        from models.match import Match, MatchStatus
        from models.reservation import Reservation, ReservationStatus
        from models.profile import UserProfile, UserPreferences
        from models.feedback import DateFeedback
        from models.payment import Payment, PaymentStatus

        # Create all tables
        db.create_all()
        logger.info("Database tables created")

        # Only run initialization functions when running directly (not via gunicorn)
        if __name__ == '__main__':
            from utils.db_init import (
                create_default_categories,
                create_admin_user,
                create_test_restaurants
            )

            create_default_categories(db)
            create_admin_user(db, bcrypt)

            if not os.environ.get('PRODUCTION'):
                create_test_restaurants(db)

            logger.info("Database initialized successfully")

# === MAIN ENTRY POINT ===
if __name__ == '__main__':
    # Initialize database if needed
    initialize_database()

    # Run with WebSocket support
    port = int(os.environ.get('PORT', 5000))
    websocket_service.run(host='0.0.0.0', port=port, debug=not os.environ.get('PRODUCTION'))