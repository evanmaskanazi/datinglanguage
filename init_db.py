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
        print("Creating database tables (preserving existing data)...")

        # First create basic tables without importing models that might fail
        try:
            db.create_all()
            print("Basic tables created successfully")
        except Exception as e:
            print(f"Error creating tables: {e}")

        # Run migrations for both restaurant and matches tables BEFORE importing models
        print("Running matches table migration...")
        migrate_matches_columns()
        print("Running restaurant ID column migration...")
        migrate_restaurant_id_column()
        print("Running restaurant table migration...")
        migrate_restaurant_columns()
        print("Running restaurant owner columns migration...")
        migrate_restaurant_owner_columns()

        # NOW we can safely import models after migration
        try:
            from models.user import User
            from models.restaurant import Restaurant, RestaurantTable
            print("Models imported successfully")
        except Exception as e:
            print(f"Error importing models: {e}")
            return

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

        # Create test users for matching
        try:
            if User.query.count() < 5:  # Only create if we don't have enough users
                print("Creating test users for matching...")

                test_users = [
                    {'email': 'sarah@example.com', 'name': 'Sarah M.'},
                    {'email': 'emma@example.com', 'name': 'Emma K.'},
                    {'email': 'lisa@example.com', 'name': 'Lisa R.'},
                    {'email': 'john@example.com', 'name': 'John D.'}
                ]

                for user_data in test_users:
                    existing_user = User.query.filter_by(email=user_data['email']).first()
                    if not existing_user:
                        test_user = User(
                            email=user_data['email'],
                            password_hash=bcrypt.generate_password_hash('TestPass123!').decode('utf-8'),
                            role='user',
                            is_active=True,
                            is_verified=True
                        )
                        db.session.add(test_user)

                db.session.commit()
                print("Test users created successfully!")

        except Exception as e:
            print(f"Error creating test users: {e}")
            db.session.rollback()

        # Only add restaurants if database is empty
        try:
            if Restaurant.query.count() == 0:
                print("No restaurants found, adding initial restaurants...")
                add_restaurants()
            else:
                existing_count = Restaurant.query.count()
                print(f"Database already has {existing_count} restaurants, skipping restaurant initialization")
        except Exception as e:
            print(f"Error checking/adding restaurants: {e}")

        print("Database initialization complete!")


def migrate_matches_columns():
    """Add missing columns to matches table"""
    from sqlalchemy import text

    try:
        # Check if columns exist first, then add them
        check_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'matches' AND column_name IN ('restaurant_id', 'table_id', 'compatibility_score', 'proposed_datetime');
        """

        result = db.session.execute(text(check_sql)).fetchall()
        existing_columns = [row[0] for row in result]

        migrations_needed = []

        if 'restaurant_id' not in existing_columns:
            migrations_needed.append("ALTER TABLE matches ADD COLUMN restaurant_id INTEGER;")

        if 'table_id' not in existing_columns:
            migrations_needed.append("ALTER TABLE matches ADD COLUMN table_id INTEGER;")

        if 'compatibility_score' not in existing_columns:
            migrations_needed.append("ALTER TABLE matches ADD COLUMN compatibility_score DECIMAL(5,2) DEFAULT 0.00;")

        if 'proposed_datetime' not in existing_columns:
            migrations_needed.append("ALTER TABLE matches ADD COLUMN proposed_datetime TIMESTAMP;")

        for sql in migrations_needed:
            print(f"Executing migration: {sql}")
            db.session.execute(text(sql))

        if migrations_needed:
            db.session.commit()
            print("✅ Matches table migration completed!")
        else:
            print("✅ Matches columns already exist, no migration needed!")

    except Exception as e:
        print(f"❌ Matches migration failed: {e}")
        db.session.rollback()
        raise


def migrate_restaurant_id_column():
    """Change restaurant_id column to handle both integer and string IDs"""
    from sqlalchemy import text

    try:
        # Check current column type
        check_sql = """
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_name = 'matches' AND column_name = 'restaurant_id';
        """

        result = db.session.execute(text(check_sql)).fetchone()

        if result and result[0] == 'integer':
            print("Converting restaurant_id column from INTEGER to VARCHAR...")

            # Convert the column type
            convert_sql = "ALTER TABLE matches ALTER COLUMN restaurant_id TYPE VARCHAR(255);"
            db.session.execute(text(convert_sql))
            db.session.commit()
            print("✅ Restaurant ID column conversion completed!")
        else:
            print("✅ Restaurant ID column is already VARCHAR!")

    except Exception as e:
        print(f"❌ Restaurant ID migration failed: {e}")
        db.session.rollback()
        raise


def migrate_restaurant_columns():
    """Add missing columns to restaurants table"""
    from sqlalchemy import text

    try:
        # Check if columns exist first, then add them
        check_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'restaurants' AND column_name IN ('external_id', 'source', 'image_url');
        """

        result = db.session.execute(text(check_sql)).fetchall()
        existing_columns = [row[0] for row in result]

        migrations_needed = []

        if 'external_id' not in existing_columns:
            migrations_needed.append("ALTER TABLE restaurants ADD COLUMN external_id VARCHAR(255);")

        if 'source' not in existing_columns:
            migrations_needed.append("ALTER TABLE restaurants ADD COLUMN source VARCHAR(50) DEFAULT 'internal';")

        if 'image_url' not in existing_columns:
            migrations_needed.append("ALTER TABLE restaurants ADD COLUMN image_url VARCHAR(500);")

        for sql in migrations_needed:
            print(f"Executing migration: {sql}")
            db.session.execute(text(sql))

        if migrations_needed:
            db.session.commit()
            print("✅ Restaurant table migration completed!")
        else:
            print("✅ Restaurant columns already exist, no migration needed!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.session.rollback()
        raise


def migrate_restaurant_owner_columns():
    """Add missing owner columns to restaurants table"""
    from sqlalchemy import text

    try:
        # Check if columns exist first, then add them
        check_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'restaurants' AND column_name IN ('owner_email', 'owner_password_hash', 'is_partner');
        """

        result = db.session.execute(text(check_sql)).fetchall()
        existing_columns = [row[0] for row in result]

        migrations_needed = []

        if 'owner_email' not in existing_columns:
            migrations_needed.append("ALTER TABLE restaurants ADD COLUMN owner_email VARCHAR(255);")

        if 'owner_password_hash' not in existing_columns:
            migrations_needed.append("ALTER TABLE restaurants ADD COLUMN owner_password_hash VARCHAR(255);")

        if 'is_partner' not in existing_columns:
            migrations_needed.append("ALTER TABLE restaurants ADD COLUMN is_partner BOOLEAN DEFAULT FALSE;")

        for sql in migrations_needed:
            print(f"Executing migration: {sql}")
            db.session.execute(text(sql))

        if migrations_needed:
            db.session.commit()
            print("✅ Restaurant owner columns migration completed!")
        else:
            print("✅ Restaurant owner columns already exist, no migration needed!")

    except Exception as e:
        print(f"❌ Restaurant owner migration failed: {e}")
        db.session.rollback()
        raise


def add_restaurants():
    """Add restaurants from both test data and API sources"""
    from models.restaurant import Restaurant, RestaurantTable
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
        },
        {
            'name': 'Urban Spice',
            'cuisine_type': 'Asian',
            'address': '789 Central St, Tel Aviv',
            'price_range': 2,
            'ambiance': 'modern',
            'rating': 4.3,
            'is_active': True,
            'source': 'internal',
            'tables': [
                {'table_number': 'B1', 'capacity': 2, 'location': 'booth'},
                {'table_number': 'B2', 'capacity': 2, 'location': 'window'}
            ]
        },
        {
            'name': 'Mediterranean Pearl',
            'cuisine_type': 'Mediterranean',
            'address': '321 Seaside Ave, Tel Aviv',
            'price_range': 4,
            'ambiance': 'upscale',
            'rating': 4.7,
            'is_active': True,
            'source': 'internal',
            'tables': [
                {'table_number': 'VIP1', 'capacity': 2, 'location': 'private'},
                {'table_number': 'VIP2', 'capacity': 2, 'location': 'terrace'}
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

        for city in cities:
            print(f"Fetching restaurants for {city}...")

            # Try Yelp API first
            try:
                yelp_restaurants = api_service.search_restaurants_yelp(city)
                for restaurant_data in yelp_restaurants[:5]:  # Limit to 5 per city
                    external_id = restaurant_data.get('external_id')
                    if external_id and not Restaurant.query.filter_by(external_id=external_id).first():
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
            except Exception as api_error:
                print(f"API error for {city}: {api_error}")

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
    with app.app_context():
        from models.restaurant import Restaurant, RestaurantTable
        from services.restaurant_api_service import RestaurantAPIService

        api_service = RestaurantAPIService(logger=None)

        print("Updating restaurants from APIs...")
        cities = ['Tel Aviv', 'Jerusalem', 'Haifa']

        for city in cities:
            try:
                # Fetch fresh data
                restaurants = api_service.search_restaurants_yelp(city)

                for restaurant_data in restaurants:
                    external_id = restaurant_data.get('external_id')
                    if external_id:
                        existing = Restaurant.query.filter_by(external_id=external_id).first()

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
            except Exception as e:
                print(f"Error updating restaurants for {city}: {e}")

        db.session.commit()
        print("Restaurant update completed!")


if __name__ == '__main__':
    init_database()