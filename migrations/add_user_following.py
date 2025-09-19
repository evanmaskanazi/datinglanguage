"""Add user following table"""
import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import app and database
from dating_backend import app, db

def migrate_user_following():
    """Create user following table"""
    with app.app_context():
        from sqlalchemy import text
        
        try:
            # Create user follows table
            create_sql = """
            CREATE TABLE IF NOT EXISTS user_follows (
                id SERIAL PRIMARY KEY,
                follower_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                followed_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(follower_id, followed_id)
            );
            """
            
            db.session.execute(text(create_sql))
            
            # Create indexes
            index_sql = [
                "CREATE INDEX IF NOT EXISTS idx_user_follows_follower ON user_follows(follower_id);",
                "CREATE INDEX IF NOT EXISTS idx_user_follows_followed ON user_follows(followed_id);"
            ]
            
            for sql in index_sql:
                db.session.execute(text(sql))
            
            db.session.commit()
            print("✅ User following table created successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_user_following()
