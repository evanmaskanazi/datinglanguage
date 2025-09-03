import re
import html
import bleach
from cryptography.fernet import Fernet

def sanitize_input(text, allow_html=False):
    """Sanitize user input to prevent XSS"""
    if not text:
        return text
    
    if allow_html:
        allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
        text = bleach.clean(text, tags=allowed_tags, strip=True)
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
