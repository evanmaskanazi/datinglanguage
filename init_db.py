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
        print("Running restaurant tables migration...")
        migrate_restaurant_tables_columns()
        print("Running restaurant management tables migration...")
        migrate_restaurant_management_tables()
        print("Running date feedback table migration...")
        migrate_date_feedback_table()
        print("Running time preferences table migration...")
        migrate_time_preferences_table()
        # Create test restaurant account for login testing
        print("Running match status normalization...")
        migrate_match_status_normalization()
        try:
            create_test_restaurant_account()
        except Exception as e:
            print(f"Error creating test restaurant account: {e}")

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


def migrate_restaurant_tables_columns():
    """Add missing columns to restaurant_tables table"""
    from sqlalchemy import text

    try:
        # Check if columns exist first, then add them
        check_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'restaurant_tables' AND column_name IN ('special_features', 'created_at');
        """

        result = db.session.execute(text(check_sql)).fetchall()
        existing_columns = [row[0] for row in result]

        migrations_needed = []

        if 'special_features' not in existing_columns:
            migrations_needed.append("ALTER TABLE restaurant_tables ADD COLUMN special_features TEXT;")

        if 'created_at' not in existing_columns:
            migrations_needed.append(
                "ALTER TABLE restaurant_tables ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        for sql in migrations_needed:
            print(f"Executing migration: {sql}")
            db.session.execute(text(sql))

        if migrations_needed:
            db.session.commit()
            print("✅ Restaurant tables columns migration completed!")
        else:
            print("✅ Restaurant tables columns already exist, no migration needed!")

    except Exception as e:
        print(f"❌ Restaurant tables migration failed: {e}")
        db.session.rollback()
        raise


# Add this function to init_db.py

def migrate_restaurant_management_tables():
    """Create restaurant management tables"""
    from sqlalchemy import text

    try:
        # Create restaurant_analytics table
        analytics_sql = """
        CREATE TABLE IF NOT EXISTS restaurant_analytics (
            id SERIAL PRIMARY KEY,
            restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
            date DATE NOT NULL,
            total_matches INTEGER DEFAULT 0,
            confirmed_matches INTEGER DEFAULT 0,
            completed_dates INTEGER DEFAULT 0,
            revenue DECIMAL(10,2) DEFAULT 0.00,
            average_rating DECIMAL(3,2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        # Create restaurant_bookings table
        bookings_sql = """
        CREATE TABLE IF NOT EXISTS restaurant_bookings (
            id SERIAL PRIMARY KEY,
            restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
            match_id INTEGER REFERENCES matches(id),
            table_id INTEGER REFERENCES restaurant_tables(id),
            user1_id INTEGER NOT NULL REFERENCES users(id),
            user2_id INTEGER NOT NULL REFERENCES users(id),
            booking_datetime TIMESTAMP NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            party_size INTEGER DEFAULT 2,
            special_requests TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        # Create restaurant_settings table
        settings_sql = """
        CREATE TABLE IF NOT EXISTS restaurant_settings (
            id SERIAL PRIMARY KEY,
            restaurant_id INTEGER NOT NULL UNIQUE REFERENCES restaurants(id),
            notification_email VARCHAR(255),
            auto_accept_bookings BOOLEAN DEFAULT FALSE,
            max_advance_days INTEGER DEFAULT 30,
            min_advance_hours INTEGER DEFAULT 2,
            special_instructions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        # Execute table creations
        db.session.execute(text(analytics_sql))
        db.session.execute(text(bookings_sql))
        db.session.execute(text(settings_sql))

        # Create indexes for better performance
        index_sql = [
            "CREATE INDEX IF NOT EXISTS idx_restaurant_analytics_restaurant_date ON restaurant_analytics(restaurant_id, date);",
            "CREATE INDEX IF NOT EXISTS idx_restaurant_bookings_restaurant_status ON restaurant_bookings(restaurant_id, status);",
            "CREATE INDEX IF NOT EXISTS idx_restaurant_bookings_datetime ON restaurant_bookings(booking_datetime);"
        ]

        for sql in index_sql:
            db.session.execute(text(sql))

        db.session.commit()
        print("✅ Restaurant management tables created successfully!")

    except Exception as e:
        print(f"❌ Restaurant management tables migration failed: {e}")
        db.session.rollback()
        raise


# Add this call to your init_database() function in init_db.py:
# Add this line with your other migration calls:
# migrate_restaurant_management_tables()


def migrate_date_feedback_table():
    """Create enhanced date feedback table"""
    from sqlalchemy import text

    try:
        # Drop the table if it exists to recreate it properly
        drop_sql = "DROP TABLE IF EXISTS date_feedback CASCADE;"
        db.session.execute(text(drop_sql))

        # Create enhanced date_feedback table with correct columns
        feedback_sql = """
        CREATE TABLE IF NOT EXISTS date_feedback (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            booking_id INTEGER REFERENCES restaurant_bookings(id),
            reservation_id INTEGER REFERENCES reservations(id),
            match_user_id INTEGER NOT NULL REFERENCES users(id),
            restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),

            -- Original rating fields
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            showed_up BOOLEAN,
            would_meet_again BOOLEAN,
            chemistry_level INTEGER CHECK (chemistry_level >= 1 AND chemistry_level <= 5),
            conversation_quality INTEGER CHECK (conversation_quality >= 1 AND conversation_quality <= 5),
            overall_experience INTEGER CHECK (overall_experience >= 1 AND overall_experience <= 5),
            comments TEXT,

            -- Enhanced restaurant rating fields
            restaurant_rating INTEGER CHECK (restaurant_rating >= 1 AND restaurant_rating <= 5),
            food_quality INTEGER CHECK (food_quality >= 1 AND food_quality <= 5),
            service_quality INTEGER CHECK (service_quality >= 1 AND service_quality <= 5),
            ambiance_rating INTEGER CHECK (ambiance_rating >= 1 AND ambiance_rating <= 5),
            value_for_money INTEGER CHECK (value_for_money >= 1 AND value_for_money <= 5),
            restaurant_review TEXT,

            -- Date success fields
            date_success BOOLEAN,
            recommend_restaurant BOOLEAN,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        db.session.execute(text(feedback_sql))

        # Create indexes for better performance AFTER table creation
        index_sql = [
            "CREATE INDEX IF NOT EXISTS idx_date_feedback_restaurant ON date_feedback(restaurant_id);",
            "CREATE INDEX IF NOT EXISTS idx_date_feedback_user ON date_feedback(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_date_feedback_booking ON date_feedback(booking_id);",
            "CREATE INDEX IF NOT EXISTS idx_date_feedback_created_at ON date_feedback(created_at);"
        ]

        for sql in index_sql:
            db.session.execute(text(sql))

        db.session.commit()
        print("✅ Enhanced date feedback table created successfully!")

    except Exception as e:
        print(f"❌ Date feedback table migration failed: {e}")
        db.session.rollback()
        raise


# ADD THE NEW FUNCTION HERE (line ~430)
def migrate_time_preferences_table():
    """Create time preferences table"""
    from sqlalchemy import text

    try:
        # Create the time preferences table
        create_sql = """
        CREATE TABLE IF NOT EXISTS user_time_preferences (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            preferred_date DATE NOT NULL,
            preferred_time VARCHAR(10) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            -- Add unique constraint to prevent duplicates
            UNIQUE(user_id, preferred_date, preferred_time)
        );
        """

        db.session.execute(text(create_sql))

        # Create indexes for better performance
        index_sql = [
            "CREATE INDEX IF NOT EXISTS idx_time_preferences_user ON user_time_preferences(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_time_preferences_date ON user_time_preferences(preferred_date);",
            "CREATE INDEX IF NOT EXISTS idx_time_preferences_time ON user_time_preferences(preferred_time);"
        ]

        for sql in index_sql:
            db.session.execute(text(sql))

        db.session.commit()
        print("✅ Time preferences table created successfully!")

    except Exception as e:
        print(f"❌ Time preferences table migration failed: {e}")
        db.session.rollback()
        raise


def migrate_match_status_normalization():
    """Ensure all match statuses are uppercase"""
    from sqlalchemy import text

    try:
        # Normalize all statuses to uppercase
        normalize_sql = """
        UPDATE matches 
        SET status = CASE 
            WHEN LOWER(status::text) IN ('accepted', 'confirmed') THEN 'ACCEPTED'
            WHEN LOWER(status::text) = 'pending' THEN 'PENDING'
            WHEN LOWER(status::text) = 'declined' THEN 'DECLINED'
            WHEN LOWER(status::text) = 'cancelled' THEN 'CANCELLED'
            WHEN LOWER(status::text) = 'completed' THEN 'COMPLETED'
            ELSE UPPER(status::text)
        END
        WHERE status IS NOT NULL;
        """

        db.session.execute(text(normalize_sql))
        db.session.commit()
        print("✅ Match statuses normalized to uppercase!")

    except Exception as e:
        print(f"⚠️ Match status normalization failed: {e}")
        db.session.rollback()



def create_test_restaurant_account():
    """Create a test restaurant account for login testing"""
    try:
        from models.restaurant import Restaurant

        # Check if test restaurant exists
        test_restaurant = Restaurant.query.filter_by(owner_email='restaurant@test.com').first()

        if not test_restaurant:
            print("Creating test restaurant account...")

            test_restaurant = Restaurant(
                name='Test Restaurant',
                cuisine_type='International',
                address='123 Test Street, Tel Aviv',
                phone='+972-50-123-4567',
                price_range=2,
                rating=4.2,
                ambiance='casual',
                is_active=True,
                is_partner=True,
                owner_email='restaurant@test.com',
                source='internal'
            )

            # Use the Restaurant model's set_password method
            test_restaurant.set_password('RestaurantPass123!')

            db.session.add(test_restaurant)
            db.session.commit()

            print("✅ Test restaurant account created:")
            print(f"   Email: restaurant@test.com")
            print(f"   Password: RestaurantPass123!")
        else:
            print("✅ Test restaurant account already exists")

    except Exception as e:
        print(f"❌ Failed to create test restaurant account: {e}")
        db.session.rollback()

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