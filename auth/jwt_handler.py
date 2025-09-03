import jwt
import os
from datetime import datetime, timedelta
from flask import current_app

JWT_SECRET = os.environ.get('SECRET_KEY', 'your-secret-key')
JWT_ALGORITHM = 'HS256'

def generate_token(user_id, expires_in=24):
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=expires_in),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def refresh_token(token):
    """Refresh JWT token if valid"""
    payload = verify_token(token)
    if payload:
        return generate_token(payload['user_id'])
    return None
