from sqlalchemy.orm import Session, joinedload
from database.models import ToolRequest, Tool, User, Object, RequestStatus
from database.connection import SessionLocal
from typing import Optional, List
from datetime import datetime

class ToolRequestService:
    @staticmethod
    def get_request_by_id(request_id: int) -> Optional[ToolRequest]:
        db = SessionLocal()
        try:
            return db.query(ToolRequest).options(
                joinedload(ToolRequest.tool),
                joinedload(ToolRequest.requester),
                joinedload(ToolRequest.approver),
                joinedload(ToolRequest.from_object),
                joinedload(ToolRequest.to_object),
                joinedload(ToolRequest.status)
            ).filter(ToolRequest.id == request_id).first()
        finally:
            db.close()

    @staticmethod
    def get_all_requests() -> List[ToolRequest]:
        db = SessionLocal()
        try:
            return db.query(ToolRequest).options(
                joinedload(ToolRequest.tool),
                joinedload(ToolRequest.requester),
                joinedload(ToolRequest.approver),
                joinedload(ToolRequest.from_object),
                joinedload(ToolRequest.to_object),
                joinedload(ToolRequest.status)
            ).all()
        finally:
            db.close()

    @staticmethod
    def create_request(tool_id: int, requester_id: int, from_object_id: int, to_object_id: int, status_name: str = "Ожидает одобрения", approver_id: Optional[int] = None) -> ToolRequest:
        db = SessionLocal()
        try:
            status = db.query(RequestStatus).filter(RequestStatus.name == status_name).first()
            if not status:
                raise ValueError(f"RequestStatus '{status_name}' not found")
            request = ToolRequest(
                tool_id=tool_id,
                requester_id=requester_id,
                from_object_id=from_object_id,
                to_object_id=to_object_id,
                status_id=status.id,
                approver_id=approver_id,
                created_at=datetime.utcnow()
            )
            db.add(request)
            db.commit()
            db.refresh(request)
            return request
        finally:
            db.close()

    @staticmethod
    def update_request(request_id: int, **kwargs) -> Optional[ToolRequest]:
        db = SessionLocal()
        try:
            request = db.query(ToolRequest).filter(ToolRequest.id == request_id).first()
            if not request:
                return None
            for key, value in kwargs.items():
                if hasattr(request, key):
                    setattr(request, key, value)
            db.commit()
            db.refresh(request)
            return request
        finally:
            db.close()

    @staticmethod
    def delete_request(request_id: int) -> bool:
        db = SessionLocal()
        try:
            request = db.query(ToolRequest).filter(ToolRequest.id == request_id).first()
            if not request:
                return False
            db.delete(request)
            db.commit()
            return True
        finally:
            db.close() 