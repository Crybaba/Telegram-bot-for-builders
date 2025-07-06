from database.connection import SessionLocal, engine
from database.models import Base, Role, RequestStatus, Status
from sqlalchemy.orm import Session

def init_database():
    """Initialize database with basic data"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Add basic roles
        roles_data = [
            {"name": "в обработке"},
            {"name": "прораб объекта"},
            {"name": "рабочий на объекте"}
        ]
        
        for role_data in roles_data:
            role = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not role:
                role = Role(**role_data)
                db.add(role)
        
        # Add request statuses (для заявок на инструменты и регистрацию)
        request_statuses_data = [
            {"name": "Ожидает одобрения"},
            {"name": "Одобрено"},
            {"name": "Отклонено"},
            {"name": "Выполнено"}
        ]
        
        for status_data in request_statuses_data:
            status = db.query(RequestStatus).filter(RequestStatus.name == status_data["name"]).first()
            if not status:
                status = RequestStatus(**status_data)
                db.add(status)
        
        # Add tool statuses
        tool_statuses_data = [
            {"name": "Доступен"},
            {"name": "В использовании"},
            {"name": "На ремонте"},
            {"name": "Списан"}
        ]
        
        for status_data in tool_statuses_data:
            status = db.query(Status).filter(Status.name == status_data["name"]).first()
            if not status:
                status = Status(**status_data)
                db.add(status)
        
        db.commit()
        print("Database initialized successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database() 