"""Add missing columns to matches table"""
import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import app and database
from dating_backend import app, db

def migrate_matches_table():
    """Add missing columns to matches table"""
    with app.app_context():
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
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_matches_table()
