from sqlalchemy.orm import joinedload
from database.models import User, Role, Object
from database.connection import SessionLocal
from typing import Optional, List

class UserService:
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        db = SessionLocal()
        try:
            return db.query(User).options(joinedload(User.role), joinedload(User.object)).filter(User.id == user_id).first()
        finally:
            db.close()

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        db = SessionLocal()
        try:
            return db.query(User).options(joinedload(User.role), joinedload(User.object)).filter(User.username == username).first()
        finally:
            db.close()

    @staticmethod
    def get_all_users() -> List[User]:
        db = SessionLocal()
        try:
            return db.query(User).options(joinedload(User.role), joinedload(User.object)).all()
        finally:
            db.close()

    @staticmethod
    def create_user(username: str, name: Optional[str] = None, role_name: str = "в обработке", object_id: Optional[int] = None) -> User:
        db = SessionLocal()
        try:
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                raise ValueError(f"Role '{role_name}' not found")
            user = User(username=username, name=name, role_id=role.id, object_id=object_id)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()

    @staticmethod
    def update_user(user_id: int, **kwargs) -> Optional[User]:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()

    @staticmethod
    def delete_user(user_id: int) -> bool:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            db.delete(user)
            db.commit()
            return True
        finally:
            db.close()

    @staticmethod
    def approve_user(user_id: int, object_id: int) -> bool:
        """Approve user registration and assign to object"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                # Get worker role (role_id = 3)
                worker_role = db.query(Role).filter(Role.id == 3).first()
                if not worker_role:
                    return False
                
                user.role_id = worker_role.id
                user.object_id = object_id
                db.commit()
                return True
            return False
        finally:
            db.close()

    @staticmethod
    def reject_user(user_id: int) -> bool:
        """Reject user registration"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                # Set role to "в обработке" (role_id = 1) and null object
                pending_role = db.query(Role).filter(Role.id == 1).first()
                if not pending_role:
                    return False
                
                user.role_id = pending_role.id
                user.object_id = None
                db.commit()
                return True
            return False
        finally:
            db.close() 