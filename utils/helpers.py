"""
General helper utilities for the dating app
"""
from datetime import datetime, timedelta, timezone
import re
import uuid
import hashlib
import json

def format_datetime(dt, format_type='default'):
    """Format datetime for display"""
    if not dt:
        return None
    
    if format_type == 'default':
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    elif format_type == 'date_only':
        return dt.strftime('%Y-%m-%d')
    elif format_type == 'time_only':
        return dt.strftime('%H:%M')
    elif format_type == 'friendly':
        return dt.strftime('%B %d, %Y at %I:%M %p')
    else:
        return dt.isoformat()

def calculate_age(birth_date):
    """Calculate age from birth date"""
    if not birth_date:
        return None
    
    today = datetime.now().date()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def generate_unique_id():
    """Generate a unique identifier"""
    return str(uuid.uuid4())

def hash_string(text):
    """Create hash of string"""
    return hashlib.sha256(text.encode()).hexdigest()

def clean_phone_number(phone):
    """Clean phone number to digits only"""
    if not phone:
        return None
    return re.sub(r'\D', '', phone)

def format_currency(amount, currency='USD'):
    """Format amount as currency"""
    if currency == 'USD':
        return f"${amount:.2f}"
    else:
        return f"{amount:.2f} {currency}"

def truncate_text(text, max_length=100):
    """Truncate text to specified length"""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates (simplified)"""
    # Simple euclidean distance approximation
    # For production, use proper haversine formula
    return ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5
