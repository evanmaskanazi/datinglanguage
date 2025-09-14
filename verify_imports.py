#!/usr/bin/env python3
"""
Verify that all required imports work before starting the application
"""
import sys

def verify_imports():
    required_modules = [
        'flask',
        'flask_login', 
        'flask_sqlalchemy',
        'flask_bcrypt',
        'flask_cors',
        'werkzeug',
        'psycopg2',
        'redis',
        'celery',
        'stripe',
        'requests'
    ]
    
    failed_imports = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError as e:
            print(f"✗ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\nFailed to import: {', '.join(failed_imports)}")
        sys.exit(1)
    
    print("\nAll imports successful!")

if __name__ == "__main__":
    verify_imports()
