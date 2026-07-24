from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    is_admin = Column(Boolean, default=False)
    daily_limit = Column(Integer, default=10)  # ۱۰ تا برای کاربر عادی
    requests_today = Column(Integer, default=0)
    last_request_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())