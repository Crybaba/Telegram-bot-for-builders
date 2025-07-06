from database.connection import engine, SessionLocal
from database.models import Base
from sqlalchemy import text

def test_database_connection():
    """Test database connection"""
    try:
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            
        # Test creating tables
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
        
        # Test session
        db = SessionLocal()
        try:
            result = db.execute(text("SELECT version()"))
            row = result.fetchone()
            if row:
                version = row[0]
                print(f"✅ Database session working! PostgreSQL version: {version}")
            else:
                print("✅ Database session working!")
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_database_connection() 