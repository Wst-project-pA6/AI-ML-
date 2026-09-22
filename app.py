from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import joblib
import pandas as pd
from sqlalchemy.orm import Session
from database import SessionLocal, init_db, StudentRiskLog, InventoryReorderLog

app = FastAPI(
    title="WST AI Integrated API",
    version="2.0.0"
)

# إنشاء الجداول عند بدء التشغيل
init_db()

# تحميل النماذج والمشفرات
student_model = joblib.load('student_risk_model.joblib')
le_attendance = joblib.load('le_attendance.joblib')
le_assessment = joblib.load('le_assessment.joblib')

inventory_model = joblib.load('inventory_reorder_model.joblib')

# Dependency للحصول على جلسة قاعدة البيانات
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class StudentRiskRequest(BaseModel):
    student_id: str
    attendance_status: str
    task_assessment_result: str
    time_on_task_minutes: int

class InventoryReorderRequest(BaseModel):
    part_sku: str
    inventory_on_hand_qty: int
    inventory_min_reorder_level: int
    part_issued_qty: int
    part_unit_cost: float

@app.get("/")
def read_root():
    return {"message": "WST AI API is Running"}

@app.post("/predict/student-risk")
def predict_student_risk(req: StudentRiskRequest, db: Session = Depends(get_db)):
    try:
        att_code = le_attendance.transform([req.attendance_status])[0]
        ass_code = le_assessment.transform([req.task_assessment_result])[0]

        X_input = pd.DataFrame([{
            "attendance_code": att_code,
            "assessment_code": ass_code,
            "time_on_task_minutes": req.time_on_task_minutes
        }])

        pred_flag = str(student_model.predict(X_input)[0])

        # حفظ النتيجة في قاعدة البيانات
        log_entry = StudentRiskLog(
            student_id=req.student_id,
            attendance_status=req.attendance_status,
            task_assessment_result=req.task_assessment_result,
            time_on_task_minutes=req.time_on_task_minutes,
            predicted_risk_flag=pred_flag
        )
        db.add(log_entry)
        db.commit()

        return {
            "student_id": req.student_id,
            "ai_training_risk_flag": pred_flag,
            "inputs_used": req.model_dump()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict/inventory-reorder")
def predict_inventory_reorder(req: InventoryReorderRequest, db: Session = Depends(get_db)):
    try:
        # الشرط المنطقي: إذا كان المتبقي أقل من أو يساوي حد إعادة الطلب
        if req.inventory_on_hand_qty <= req.inventory_min_reorder_level:
            reorder_status = "REORDER_RECOMMENDED"
        else:
            reorder_status = "HEALTHY"

        # حفظ النتيجة في قاعدة البيانات
        log_entry = InventoryReorderLog(
            part_sku=req.part_sku,
            inventory_on_hand_qty=req.inventory_on_hand_qty,
            inventory_min_reorder_level=req.inventory_min_reorder_level,
            part_issued_qty=req.part_issued_qty,
            part_unit_cost=req.part_unit_cost,
            predicted_reorder_status=reorder_status
        )
        db.add(log_entry)
        db.commit()

        return {
            "part_sku": req.part_sku,
            "ai_reorder_status": reorder_status,
            "inputs_used": req.model_dump()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))