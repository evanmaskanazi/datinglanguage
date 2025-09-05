"""Database initialization utilities for Table for Two"""
import os
from datetime import datetime

def create_default_categories(db):
    """Create default categories and reference data"""
    # In the current schema, we don't have categories table
    # This function is a placeholder for future expansion
    print("No default categories to create")
    pass

def create_admin_user(db, bcrypt):
    """Create admin user if not exists"""
    # Import here to avoid circular imports
    from models.user import User
    
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@tablefortwo.com')
    admin = User.query.filter_by(email=admin_email).first()
    
    if not admin:
        print("Creating admin user from db_init...")
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

def create_test_restaurants(db):
    """Create test restaurants for development"""
    # Import here to avoid circular imports
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
        },
        {
            'name': 'Cozy Corner Cafe',
            'cuisine_type': 'French',
            'address': '789 Charm Street, Tel Aviv',
            'price_range': 2,
            'ambiance': 'intimate',
            'tables': [
                {'table_number': 'B1', 'capacity': 2, 'location': 'booth'},
                {'table_number': 'B2', 'capacity': 2, 'location': 'patio'}
            ]
        },
        {
            'name': 'Ocean View Terrace',
            'cuisine_type': 'Seafood',
            'address': '321 Beach Boulevard, Tel Aviv',
            'price_range': 4,
            'ambiance': 'upscale',
            'tables': [
                {'table_number': 'T1', 'capacity': 2, 'location': 'balcony'},
                {'table_number': 'T2', 'capacity': 2, 'location': 'window'},
                {'table_number': 'T3', 'capacity': 2, 'location': 'private'}
            ]
        }
    ]
    
    created_count = 0
    for rest_data in test_restaurants:
        restaurant = Restaurant.query.filter_by(name=rest_data['name']).first()
        if not restaurant:
            tables_data = rest_data.pop('tables', [])
            restaurant = Restaurant(**rest_data, is_active=True)
            db.session.add(restaurant)
            db.session.flush()  # Get the restaurant ID
            
            # Add tables for this restaurant
            for table_data in tables_data:
                table = RestaurantTable(
                    restaurant_id=restaurant.id,
                    **table_data,
                    is_available=True
                )
                db.session.add(table)
            
            created_count += 1
            print(f"Created restaurant: {restaurant.name} with {len(tables_data)} tables")
    
    db.session.commit()
    print(f"Created {created_count} test restaurants")
