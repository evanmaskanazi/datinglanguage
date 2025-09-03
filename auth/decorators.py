from functools import wraps
from flask import request, jsonify, g
from auth.jwt_handler import verify_token
from models.user import User

def require_auth(roles=None):
    """Authentication decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for token in header
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Invalid authorization header'}), 401
            
            token = auth_header.replace('Bearer ', '')
            payload = verify_token(token)
            
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Get user
            user = User.query.get(payload['user_id'])
            if not user or not user.is_active:
                return jsonify({'error': 'User not found or inactive'}), 401
            
            # Check roles if specified
            if roles and user.role not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            # Add user to request context
            request.current_user = user
            g.user_id = user.id
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
