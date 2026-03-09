from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, TIMESTAMP, text
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    is_admin = Column(Boolean, nullable=False, server_default=text("FALSE"))
    is_active = Column(Boolean, nullable=False, server_default=text("TRUE"))
    can_use_stt = Column(Boolean, nullable=False, server_default=text("FALSE"))
    is_unlimited = Column(Boolean, nullable=False, server_default=text("FALSE"))
    daily_limit = Column(Integer, nullable=False, server_default=text("10"))
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, server_default=text("'success'"))
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))