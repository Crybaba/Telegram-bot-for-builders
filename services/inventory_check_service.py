from sqlalchemy.orm import Session, joinedload
from database.models import InventoryCheck, ToolOnCheck, User, Object
from database.connection import SessionLocal
from typing import Optional, List
from datetime import datetime

class InventoryCheckService:
    @staticmethod
    def get_check_by_id(check_id: int) -> Optional[InventoryCheck]:
        db = SessionLocal()
        try:
            return db.query(InventoryCheck).options(joinedload(InventoryCheck.user), joinedload(InventoryCheck.object), joinedload(InventoryCheck.tool_on_checks)).filter(InventoryCheck.id == check_id).first()
        finally:
            db.close()

    @staticmethod
    def get_all_checks() -> List[InventoryCheck]:
        db = SessionLocal()
        try:
            return db.query(InventoryCheck).options(joinedload(InventoryCheck.user), joinedload(InventoryCheck.object)).all()
        finally:
            db.close()

    @staticmethod
    def create_check(user_id: int, object_id: int, date: Optional[datetime] = None, tool_ids: Optional[List[int]] = None) -> InventoryCheck:
        db = SessionLocal()
        try:
            check = InventoryCheck(user_id=user_id, object_id=object_id, date=date or datetime.utcnow())
            db.add(check)
            db.commit()
            db.refresh(check)
            # Add tools to check if provided
            if tool_ids:
                for tool_id in tool_ids:
                    toc = ToolOnCheck(check_id=check.id, tool_id=tool_id)
                    db.add(toc)
                db.commit()
            return check
        finally:
            db.close()

    @staticmethod
    def update_check(check_id: int, **kwargs) -> Optional[InventoryCheck]:
        db = SessionLocal()
        try:
            check = db.query(InventoryCheck).filter(InventoryCheck.id == check_id).first()
            if not check:
                return None
            for key, value in kwargs.items():
                if hasattr(check, key):
                    setattr(check, key, value)
            db.commit()
            db.refresh(check)
            return check
        finally:
            db.close()

    @staticmethod
    def delete_check(check_id: int) -> bool:
        db = SessionLocal()
        try:
            check = db.query(InventoryCheck).filter(InventoryCheck.id == check_id).first()
            if not check:
                return False
            db.delete(check)
            db.commit()
            return True
        finally:
            db.close() 