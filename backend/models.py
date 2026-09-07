from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from database import Base
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    password_hash = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    recipient_account = Column(String(100))
    status = Column(String(50), default="Pending")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    device_info = Column(String(255), default="unknown")
    location_ip = Column(String(50), default="unknown")
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    risk_score = Column(Float)
    decision_reason = Column(String(255))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))