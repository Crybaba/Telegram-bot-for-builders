from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base


class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, unique=True, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="role")


class ToolName(Base):
    __tablename__ = "tool_name"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, unique=True, nullable=False)
    
    # Relationships
    tools = relationship("Tool", back_populates="tool_name")


class RequestStatus(Base):
    __tablename__ = "request_status"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, unique=True, nullable=False)
    
    # Relationships
    tool_requests = relationship("ToolRequest", back_populates="status")


class Status(Base):
    __tablename__ = "status"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, unique=True, nullable=False)
    
    # Relationships
    tools = relationship("Tool", back_populates="status")


class User(Base):
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False)  # @username
    chat_id = Column(BigInteger, nullable=True)  # Telegram chat_id для отправки уведомлений
    name = Column(Text, nullable=True)  # nullable
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    object_id = Column(Integer, ForeignKey("object.id"), nullable=True)  # nullable
    
    # Relationships
    role = relationship("Role", back_populates="users")
    object = relationship("Object", back_populates="users", foreign_keys=[object_id])
    inventory_checks = relationship("InventoryCheck", back_populates="user")
    tool_requests_requester = relationship("ToolRequest", foreign_keys="ToolRequest.requester_id", back_populates="requester")
    tool_requests_approver = relationship("ToolRequest", foreign_keys="ToolRequest.approver_id", back_populates="approver")


class Object(Base):
    __tablename__ = "object"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, unique=True, nullable=False)
    location = Column(Text)
    foreman_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    
    # Relationships
    users = relationship("User", back_populates="object", foreign_keys=[User.object_id])
    foreman = relationship("User", foreign_keys=[foreman_id])
    tools = relationship("Tool", back_populates="current_object")
    inventory_checks = relationship("InventoryCheck", back_populates="object")
    tool_requests_from = relationship("ToolRequest", foreign_keys="ToolRequest.from_object_id", back_populates="from_object")
    tool_requests_to = relationship("ToolRequest", foreign_keys="ToolRequest.to_object_id", back_populates="to_object")


class Tool(Base):
    __tablename__ = "tools"
    
    id = Column(Integer, primary_key=True, index=True)
    inventory_number = Column(Text, unique=True, nullable=False)
    name_id = Column(Integer, ForeignKey("tool_name.id"), nullable=False)
    qr_code_value = Column(Text, unique=True, nullable=False)
    current_object_id = Column(Integer, ForeignKey("object.id"))
    status_id = Column(Integer, ForeignKey("status.id"), nullable=False)
    
    # Relationships
    tool_name = relationship("ToolName", back_populates="tools")
    current_object = relationship("Object", back_populates="tools")
    status = relationship("Status", back_populates="tools")
    tool_on_checks = relationship("ToolOnCheck", back_populates="tool")
    tool_requests = relationship("ToolRequest", back_populates="tool")


class InventoryCheck(Base):
    __tablename__ = "inventory_checks"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, default=func.current_timestamp())
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    object_id = Column(Integer, ForeignKey("object.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="inventory_checks")
    object = relationship("Object", back_populates="inventory_checks")
    tool_on_checks = relationship("ToolOnCheck", back_populates="check")


class ToolOnCheck(Base):
    __tablename__ = "tool_on_check"
    
    check_id = Column(Integer, ForeignKey("inventory_checks.id"), primary_key=True)
    tool_id = Column(Integer, ForeignKey("tools.id"), primary_key=True)
    
    # Relationships
    check = relationship("InventoryCheck", back_populates="tool_on_checks")
    tool = relationship("Tool", back_populates="tool_on_checks")


class ToolRequest(Base):
    __tablename__ = "tool_request"
    
    id = Column(Integer, primary_key=True, index=True)
    tool_id = Column(Integer, ForeignKey("tools.id"), nullable=False)
    from_object_id = Column(Integer, ForeignKey("object.id"))
    to_object_id = Column(Integer, ForeignKey("object.id"))
    requester_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    approver_id = Column(Integer, ForeignKey("user.id"))
    status_id = Column(Integer, ForeignKey("request_status.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    
    # Relationships
    tool = relationship("Tool", back_populates="tool_requests")
    from_object = relationship("Object", foreign_keys=[from_object_id], back_populates="tool_requests_from")
    to_object = relationship("Object", foreign_keys=[to_object_id], back_populates="tool_requests_to")
    requester = relationship("User", foreign_keys=[requester_id], back_populates="tool_requests_requester")
    approver = relationship("User", foreign_keys=[approver_id], back_populates="tool_requests_approver")
    status = relationship("RequestStatus", back_populates="tool_requests") 