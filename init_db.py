"""Initialize database for Table for Two dating app"""
import os
import sys
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import app and models
from dating_backend import app, db, bcrypt

def init_database():
    """Initialize database with tables and default data"""
    with app.app_context():
        # Import ALL models inside app context to ensure proper registration
        from models.user import User
        from models.profile import UserProfile, UserPreferences
        from models.restaurant import Restaurant, RestaurantTable
        from models.match import Match
        from models.reservation import Reservation
        from models.feedback import DateFeedback
        from models.payment import Payment
        
        print("Creating database tables...")
        db.create_all()
        
        # IMPORTANT: Only query AFTER all models are imported and tables created
        print("Checking for admin user...")
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@tablefortwo.com')
        
        try:
            admin = User.query.filter_by(email=admin_email).first()
            
            if not admin:
                print("Creating admin user...")
                admin = User(
                    email=admin_email,
                    password_hash=bcrypt.generate_password_hash(
                        os.environ.get('ADMIN_PASSWORD', 'Admin123!')
                    ).decode('utf-8'),
                    role='admin',
                    is_active=True,
                    is_verified=True
                )
                db.session.add(admin)
                db.session.commit()
                print(f"Admin user created: {admin_email}")
            else:
                print(f"Admin user already exists: {admin_email}")
                
        except Exception as e:
            print(f"Error during admin user creation: {e}")
            db.session.rollback()
        
        # Add test restaurants in development
        if not os.environ.get('PRODUCTION'):
            print("Adding test restaurants...")
            add_test_restaurants()
        
        print("Database initialization complete!")

def add_test_restaurants():
    """Add test restaurants for development"""
    # Import models here too
    from models.restaurant import Restaurant, RestaurantTable
    
    test_restaurants = [
        {
            'name': 'The Romantic Garden',
            'cuisine_type': 'Italian',
            'address': '123 Love Lane, Tel Aviv',
            'price_range': 3,
            'ambiance': 'romantic',
            'tables': [
                {'table_number': '1', 'capacity': 2, 'location': 'window'},
                {'table_number': '2', 'capacity': 2, 'location': 'garden'},
                {'table_number': '3', 'capacity': 2, 'location': 'corner'}
            ]
        },
        {
            'name': 'Sunset Bistro',
            'cuisine_type': 'Mediterranean',
            'address': '456 Beach Road, Tel Aviv',
            'price_range': 2,
            'ambiance': 'casual',
            'tables': [
                {'table_number': 'A1', 'capacity': 2, 'location': 'terrace'},
                {'table_number': 'A2', 'capacity': 2, 'location': 'indoor'}
            ]
        }
    ]
    
    try:
        for rest_data in test_restaurants:
            restaurant = Restaurant.query.filter_by(name=rest_data['name']).first()
            if not restaurant:
                tables_data = rest_data.pop('tables')
                restaurant = Restaurant(**rest_data, is_active=True)
                db.session.add(restaurant)
                db.session.flush()
                
                # Add tables
                for table_data in tables_data:
                    table = RestaurantTable(
                        restaurant_id=restaurant.id,
                        **table_data,
                        is_available=True
                    )
                    db.session.add(table)
        
        db.session.commit()
        print("Test restaurants added successfully!")
    except Exception as e:
        print(f"Error adding test restaurants: {e}")
        db.session.rollback()

if __name__ == '__main__':
    init_database()
