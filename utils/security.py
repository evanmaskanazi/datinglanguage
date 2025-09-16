"""
Security utilities for input sanitization and validation
"""
import re
import html
import bleach
import secrets
from cryptography.fernet import Fernet
from urllib.parse import urlparse

# HTML tags allowed in user content
ALLOWED_HTML_TAGS = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']

def sanitize_input(text, allow_html=False):
    """Sanitize user input to prevent XSS"""
    if not text:
        return text
    
    if allow_html:
        text = bleach.clean(text, tags=ALLOWED_HTML_TAGS, strip=True)
    else:
        text = html.escape(text)
    
    return text.replace('\x00', '')

def sanitize_html(text):
    """Remove all HTML tags from text"""
    if not text:
        return text
    clean = re.compile('<.*?>')
    return re.sub(clean, '', str(text))

def validate_email(email):
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def encrypt_field(data, fernet):
    """Encrypt sensitive field data"""
    if not data:
        return None
    if isinstance(data, str):
        data = data.encode()
    return fernet.encrypt(data).decode()

def decrypt_field(encrypted_data, fernet):
    """Decrypt sensitive field data"""
    if not encrypted_data:
        return None
    return fernet.decrypt(encrypted_data.encode()).decode()

def validate_cors_origin(request, allowed_origins):
    """Validate CORS origin"""
    origin = request.headers.get('Origin')
    if not origin:
        return True
    
    origin_lower = origin.lower()
    for allowed in allowed_origins:
        if origin_lower == allowed.lower():
            return True
    
    return False

def generate_csrf_token():
    """Generate a CSRF token"""
    return secrets.token_urlsafe(32)

def validate_password_strength(password):
    """Validate password meets security requirements"""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    return True, "Password is valid"

def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    if not filename:
        return 'unknown'
    
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove dangerous characters
    filename = re.sub(r'[^\w\-_\.]', '', filename)
    
    # Limit length
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:95] + ('.' + ext if ext else '')
    
    return filename or 'unknown'

def validate_url(url):
    """Validate URL format and security"""
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        return parsed.scheme in ['http', 'https'] and parsed.netloc
    except:
        return False

def rate_limit_key(user_id, action):
    """Generate rate limiting key"""
    return f"rate_limit:{action}:{user_id}"

def secure_compare(a, b):
    """Secure string comparison to prevent timing attacks"""
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    
    if len(a) != len(b):
        return False
    
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    
    return result == 0
