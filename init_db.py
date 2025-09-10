"""Initialize database for Table for Two dating app with restaurant API integration"""
import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import app and database
from dating_backend import app, db, bcrypt


def init_database():
    """Initialize database with tables and default data"""
    with app.app_context():
        # Import ALL models to ensure they're registered with SQLAlchemy
        import models  # This will import everything from __init__.py

        print("Dropping existing tables...")
        db.drop_all()

        print("Creating database tables...")
        db.create_all()

        # Now we can safely use the models
        from models import User, Restaurant, RestaurantTable

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

        # Add initial restaurants
        print("Adding restaurants...")
        add_restaurants()

        print("Database initialization complete!")


def add_restaurants():
    """Add restaurants from both test data and API sources"""
    from models import Restaurant, RestaurantTable
    from services.restaurant_api_service import RestaurantAPIService

    # Initialize API service
    api_service = RestaurantAPIService(logger=None)

    # Add a few test restaurants first
    test_restaurants = [
        {
            'name': 'The Romantic Garden',
            'cuisine_type': 'Italian',
            'address': '123 Love Lane, Tel Aviv',
            'price_range': 3,
            'ambiance': 'romantic',
            'rating': 4.5,
            'is_active': True,
            'source': 'internal',
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
            'rating': 4.2,
            'is_active': True,
            'source': 'internal',
            'tables': [
                {'table_number': 'A1', 'capacity': 2, 'location': 'terrace'},
                {'table_number': 'A2', 'capacity': 2, 'location': 'indoor'}
            ]
        }
    ]

    try:
        # Add test restaurants
        for rest_data in test_restaurants:
            restaurant = Restaurant.query.filter_by(name=rest_data['name']).first()
            if not restaurant:
                tables_data = rest_data.pop('tables', [])
                restaurant = Restaurant(**rest_data)
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

        # Try to fetch restaurants from APIs if keys are available
        cities = ['Tel Aviv', 'Jerusalem', 'Haifa']  # Israeli cities
        cuisines = ['italian', 'asian', 'mediterranean', 'american']

        for city in cities:
            print(f"Fetching restaurants for {city}...")

            # Try Yelp API first
            yelp_restaurants = api_service.search_restaurants_yelp(city)
            for restaurant_data in yelp_restaurants[:10]:  # Limit to 10 per city
                if not Restaurant.query.filter_by(external_id=restaurant_data['external_id']).first():
                    restaurant = Restaurant(**restaurant_data)
                    db.session.add(restaurant)
                    db.session.flush()

                    # Add default tables for API restaurants
                    for i in range(1, 4):  # Add 3 tables per restaurant
                        table = RestaurantTable(
                            restaurant_id=restaurant.id,
                            table_number=str(i),
                            capacity=2,
                            location='main_dining',
                            is_available=True
                        )
                        db.session.add(table)

            # Try Google Places API as fallback
            if not yelp_restaurants:
                google_restaurants = api_service.search_restaurants_google(city)
                for restaurant_data in google_restaurants[:10]:
                    if not Restaurant.query.filter_by(external_id=restaurant_data['external_id']).first():
                        restaurant = Restaurant(**restaurant_data)
                        db.session.add(restaurant)
                        db.session.flush()

                        # Add default tables
                        for i in range(1, 3):
                            table = RestaurantTable(
                                restaurant_id=restaurant.id,
                                table_number=str(i),
                                capacity=2,
                                location='main_dining',
                                is_available=True
                            )
                            db.session.add(table)

        db.session.commit()
        print("Restaurants added successfully!")

        # Print summary
        total_restaurants = Restaurant.query.count()
        total_tables = RestaurantTable.query.count()
        print(f"Total restaurants in database: {total_restaurants}")
        print(f"Total tables available: {total_tables}")

    except Exception as e:
        print(f"Error adding restaurants: {e}")
        db.session.rollback()


def update_restaurants_from_api():
    """Function to periodically update restaurants from APIs"""
    from models import Restaurant, RestaurantTable
    from services.restaurant_api_service import RestaurantAPIService

    api_service = RestaurantAPIService(logger=None)

    print("Updating restaurants from APIs...")
    cities = ['Tel Aviv', 'Jerusalem', 'Haifa']

    for city in cities:
        # Fetch fresh data
        restaurants = api_service.search_restaurants_yelp(city)

        for restaurant_data in restaurants:
            existing = Restaurant.query.filter_by(external_id=restaurant_data['external_id']).first()

            if existing:
                # Update existing restaurant
                existing.rating = restaurant_data.get('rating', existing.rating)
                existing.is_active = True
            else:
                # Add new restaurant
                restaurant = Restaurant(**restaurant_data)
                db.session.add(restaurant)
                db.session.flush()

                # Add tables
                for i in range(1, 3):
                    table = RestaurantTable(
                        restaurant_id=restaurant.id,
                        table_number=str(i),
                        capacity=2,
                        location='main_dining',
                        is_available=True
                    )
                    db.session.add(table)

    db.session.commit()
    print("Restaurant update completed!")


if __name__ == '__main__':
    init_database()