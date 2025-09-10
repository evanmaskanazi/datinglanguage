"""Add external_id, source, and image_url columns to restaurants table"""
import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import app and database
from dating_backend import app, db

def migrate_restaurant_table():
    """Add missing columns to restaurants table"""
    with app.app_context():
        # Raw SQL to add columns if they don't exist
        migration_sql = [
            """
            ALTER TABLE restaurants 
            ADD COLUMN IF NOT EXISTS external_id VARCHAR(255) UNIQUE;
            """,
            """
            ALTER TABLE restaurants 
            ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'internal';
            """,
            """
            ALTER TABLE restaurants 
            ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);
            """
        ]
        
        try:
            for sql in migration_sql:
                print(f"Executing: {sql.strip()}")
                db.session.execute(sql)
            
            db.session.commit()
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_restaurant_table()
