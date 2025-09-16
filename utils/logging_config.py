"""
Logging configuration for the dating app
"""
import logging
import os
from datetime import datetime

def setup_logger(name, level=None):
    """Setup logger with consistent formatting"""
    if level is None:
        level = logging.DEBUG if os.environ.get('FLASK_ENV') == 'development' else logging.INFO
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger

def log_error(logger, error, context=None):
    """Log error with context"""
    error_msg = f"Error: {str(error)}"
    if context:
        error_msg += f" | Context: {context}"
    logger.error(error_msg)

def log_user_action(logger, user_id, action, details=None):
    """Log user actions for audit trail"""
    log_msg = f"User {user_id} performed: {action}"
    if details:
        log_msg += f" | Details: {details}"
    logger.info(log_msg)

# ADD THIS MISSING FUNCTION:
def log_audit(logger, user_id, action, details=None):
    """Log audit events with special formatting"""
    audit_msg = f"AUDIT: User {user_id} | Action: {action}"
    if details:
        audit_msg += f" | Details: {details}"
    logger.info(audit_msg)
