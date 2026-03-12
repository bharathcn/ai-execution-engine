from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database.db import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    goal_id = Column(Integer, ForeignKey("goals.id"))

    day_number = Column(Integer)

    title = Column(String)

    instructions = Column(String)

    expected_outcome = Column(String)

    status = Column(String, default="PENDING")

    created_at = Column(DateTime, default=datetime.utcnow)

    completed_at = Column(DateTime, nullable=True)