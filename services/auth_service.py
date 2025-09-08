from flask import jsonify
from datetime import datetime 
from models.user import User, db
from models.profile import UserProfile
from utils.security import validate_email, sanitize_input
from auth.jwt_handler import generate_token
import secrets

class AuthService:
    def __init__(self, db, bcrypt, logger):
        self.db = db
        self.bcrypt = bcrypt
        self.logger = logger
    
    def register(self, data):
        """Register new user"""
        try:
            # Validate input
            email = sanitize_input(data.get('email', '').lower().strip())
            password = data.get('password', '')
            display_name = sanitize_input(data.get('display_name', ''))
            
            if not email or not validate_email(email):
                return jsonify({'error': 'Invalid email address'}), 400
            
            if not password or len(password) < 8:
                return jsonify({'error': 'Password must be at least 8 characters'}), 400
            
            if not display_name:
                return jsonify({'error': 'Display name is required'}), 400
            
            # Check if user exists
            if User.query.filter_by(email=email).first():
                return jsonify({'error': 'Email already registered'}), 409
            
            # Create user
            user = User(
                email=email,
                password_hash=self.bcrypt.generate_password_hash(password).decode('utf-8'),
                verification_token=secrets.token_urlsafe(32)
            )
            self.db.session.add(user)
            self.db.session.flush()
            
            # Create profile
            profile = UserProfile(
                user_id=user.id,
                display_name=display_name
            )
            self.db.session.add(profile)
            self.db.session.commit()
            
            # Generate token
            token = generate_token(user.id)
            
            # TODO: Send verification email
            
            return jsonify({
                'success': True,
                'token': token,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'display_name': display_name
                }
            }), 201
            
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Registration error: {str(e)}")
            return jsonify({'error': 'Registration failed'}), 500
    
    def login(self, data):
        """User login"""
        try:
            email = sanitize_input(data.get('email', '').lower().strip())
            password = data.get('password', '')
            
            if not email or not password:
                return jsonify({'error': 'Email and password required'}), 400
            
            # Find user
            user = User.query.filter_by(email=email).first()
            
            if not user or not self.bcrypt.check_password_hash(user.password_hash, password):
                return jsonify({'error': 'Invalid credentials'}), 401
            
            if not user.is_active:
                return jsonify({'error': 'Account deactivated'}), 403
            
            # Update last login
            user.last_login = datetime.utcnow()
            self.db.session.commit()
            
            # Generate token
            token = generate_token(user.id)
            
            return jsonify({
                'success': True,
                'token': token,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'role': user.role,
                    'is_verified': user.is_verified
                }
            })
            
        except Exception as e:
            self.logger.error(f"Login error: {str(e)}")
            return jsonify({'error': 'Login failed'}), 500
