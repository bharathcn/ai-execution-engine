from sqlalchemy import Column, Integer, String, DateTime, Date
from datetime import datetime
from app.database.db import Base


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    goal_text = Column(String, nullable=False)
    plan_summary = Column(String)
    status = Column(String, default="DRAFT")
    created_at = Column(DateTime, default=datetime.utcnow)
    start_date = Column(Date, nullable=True)
    unlocked_until_day = Column(Integer, nullable=True, default=1)