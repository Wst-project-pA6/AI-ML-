from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

DATABASE_URL = "sqlite:///./wst_ai.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class StudentRiskLog(Base):
    __tablename__ = "student_risk_predictions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, index=True)
    attendance_status = Column(String)
    task_assessment_result = Column(String)
    time_on_task_minutes = Column(Integer)
    predicted_risk_flag = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class InventoryReorderLog(Base):
    __tablename__ = "inventory_reorder_predictions"

    id = Column(Integer, primary_key=True, index=True)
    part_sku = Column(String, index=True)
    inventory_on_hand_qty = Column(Integer)
    inventory_min_reorder_level = Column(Integer)
    part_issued_qty = Column(Integer)
    part_unit_cost = Column(Float)
    predicted_reorder_status = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
