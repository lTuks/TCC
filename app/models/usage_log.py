
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.db.session import Base

class UsageLog(Base):
    __tablename__ = "usage_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    endpoint = Column(String(120))
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    cost = Column(String(50), default="0")
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
