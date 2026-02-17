"""
Database Initialization Script
Creates all tables and sets up indices
"""

import os
from app import app
from models import db, User
import json

def init_database():
    """Initialize the database with all tables"""
    with app.app_context():
        # Create all tables
        print("[DB INIT] Creating database tables...")
        db.create_all()
        print("[DB INIT] ✅ All tables created successfully!")
        
        # Create default user if doesn't exist
        default_user = User.query.filter_by(username='default').first()
        if not default_user:
            print("[DB INIT] Creating default user...")
            default_user = User(
                username='default',
                email=None,
                preferences=json.dumps({
                    'theme': 'light',
                    'notifications_enabled': True,
                    'reminder_sound': True
                })
            )
            db.session.add(default_user)
            db.session.commit()
            print(f"[DB INIT] ✅ Default user created with ID: {default_user.id}")
        else:
            print(f"[DB INIT] ℹ️  Default user already exists (ID: {default_user.id})")
        
        # Print table summary
        print("\n[DB INIT] Database Summary:")
        print(f"  - Database file: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"  - Tables created:")
        print(f"    • users")
        print(f"    • saved_drugs")
        print(f"    • medication_reminders")
        print(f"    • prescriptions")
        print(f"    • prescription_items")
        print("\n[DB INIT] 🎉 Database initialization complete!")

if __name__ == '__main__':
    # Ensure database directory exists
    db_path = 'instance'
    if not os.path.exists(db_path):
        os.makedirs(db_path)
        print(f"[DB INIT] Created directory: {db_path}/")
    
    init_database()
