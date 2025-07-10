from database.connection import SessionLocal, engine
from database.models import Base, Role, RequestStatus, Status, Object, Tool, ToolName
from sqlalchemy.orm import Session
import random
from sqlalchemy import text

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
            {"name": "Выполнено"}
        ]
        
        for status_data in request_statuses_data:
            status = db.query(RequestStatus).filter(RequestStatus.name == status_data["name"]).first()
            if not status:
                status = RequestStatus(**status_data)
                db.add(status)
        
        # Add tool statuses
        tool_statuses_data = [
            {"name": "В наличии"},
            {"name": "Утерян"},
            {"name": "Списан"}
        ]
        
        for status_data in tool_statuses_data:
            status = db.query(Status).filter(Status.name == status_data["name"]).first()
            if not status:
                status = Status(**status_data)
                db.add(status)
        
        db.commit()
        print("✅ Database initialized successfully!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

def create_test_data():
    """Create test data with tools on 3 objects"""
    db = SessionLocal()
    try:
        # Check if data already exists
        existing_objects = db.query(Object).count()
        if existing_objects > 0:
            print("⚠️ Test data already exists. Skipping creation.")
            return True
            
        # Create tool names
        tool_names = [
            "Молоток",
            "Отвертка",
            "Дрель",
            "Шуруповерт",
            "Пила",
            "Рубанок",
            "Стамеска",
            "Ключ гаечный",
            "Плоскогубцы",
            "Кусачки",
            "Ножовка",
            "Топор",
            "Лопата",
            "Кисть",
            "Валик"
        ]
        
        tool_name_objects = []
        for name in tool_names:
            tool_name = ToolName(name=name)
            db.add(tool_name)
            tool_name_objects.append(tool_name)
        
        # Create objects
        objects = [
            Object(name="Объект А", location="ул. Ленина, 1"),
            Object(name="Объект Б", location="пр. Мира, 15"),
            Object(name="Объект В", location="ул. Пушкина, 8")
        ]
        
        for obj in objects:
            db.add(obj)
        
        db.commit()
        
        # Get status "В наличии" (most common)
        available_status = db.query(Status).filter(Status.name == "В наличии").first()
        if not available_status:
            print("❌ Status 'В наличии' not found!")
            return False
        
        # Create tools for each object
        for obj in objects:
            print(f"Создаю инструменты для объекта: {obj.name}")
            
            # Select 10 random tool names for this object
            selected_tools = random.sample(tool_names, 10)
            
            for i, tool_name in enumerate(selected_tools):
                # Find tool name object
                tool_name_obj = db.query(ToolName).filter(ToolName.name == tool_name).first()
                if not tool_name_obj:
                    print(f"❌ Tool name '{tool_name}' not found!")
                    continue
                
                # Create tool
                tool = Tool(
                    inventory_number=f"INV-{obj.id:02d}-{i+1:03d}",
                    name_id=tool_name_obj.id,
                    qr_code_value=f"QR-{obj.id:02d}-{i+1:03d}",
                    current_object_id=obj.id,
                    status_id=available_status.id
                )
                db.add(tool)
        
        db.commit()
        print("✅ Test data created successfully!")
        print(f"   - Создано {len(tool_names)} названий инструментов")
        print(f"   - Создано 3 статуса")
        print(f"   - Создано {len(objects)} объектов")
        print(f"   - Создано {len(objects) * 10} инструментов (по 10 на объект)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        db.rollback()
        return False
    finally:
        db.close()

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
    print("🚀 Инициализация базы данных...")
    
    # Тестируем подключение
    if test_database_connection():
        # Инициализируем базовые данные
        init_database()
        
        # Создаем тестовые данные
        print("\n📊 Создание тестовых данных...")
        create_test_data()
        
        print("\n✅ Все готово! База данных инициализирована и заполнена тестовыми данными.")
    else:
        print("❌ Не удалось подключиться к базе данных. Проверьте настройки в config.py") 