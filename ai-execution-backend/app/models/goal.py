from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.db import Base


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    goal_text = Column(String, nullable=False)
    category = Column(String, nullable=True)
    answers_json = Column(Text, nullable=True)
    plan_summary = Column(String)
    status = Column(String, nullable=False, default="DRAFT")
    created_at = Column(DateTime, default=datetime.utcnow)
    start_date = Column(Date, nullable=True)
    unlocked_until_day = Column(Integer, nullable=True, default=1)

    user = relationship("User", backref="goals")
