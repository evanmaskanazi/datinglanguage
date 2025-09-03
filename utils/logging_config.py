import logging
import os

def setup_logger(name):
    """Setup logger with proper formatting"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

def log_audit(action, user_id=None, details=None):
    """Log audit trail"""
    # TODO: Implement audit logging to database
    pass
