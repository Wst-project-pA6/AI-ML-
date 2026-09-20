import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_read_root():
    """اختبار الصفحة الرئيسية للـ API"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "WST AI API is Running"}

def test_predict_student_risk_success():
    """اختبار التنبؤ بمخاطر الطلاب - حالة نجاح"""
    payload = {
        "student_id": "STU-2026-002",
        "attendance_status": "Absent",
        "task_assessment_result": "Needs Improvement",
        "time_on_task_minutes": 120
    }
    response = client.post("/predict/student-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["student_id"] == "STU-2026-002"
    assert "ai_training_risk_flag" in data

def test_predict_inventory_reorder_success():
    """اختبار التنبؤ بإعادة طلب المخزون - حالة نجاح"""
    payload = {
        "part_sku": "SKU-BRA-001",
        "inventory_on_hand_qty": 5,
        "inventory_min_reorder_level": 15,
        "part_issued_qty": 10,
        "part_unit_cost": 850.0
    }
    response = client.post("/predict/inventory-reorder", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["part_sku"] == "SKU-BRA-001"
    assert "ai_reorder_status" in data

def test_predict_student_risk_invalid_data():
    """اختبار التنبؤ بمخاطر الطلاب - بيانات ناقصة أو غير صحيحة"""
    payload = {
        "student_id": "STU-2026-002"
        # تم إهمال باقي الحقوق الإلزامية
    }
    response = client.post("/predict/student-risk", json=payload)
    assert response.status_code == 422  # Unprocessable Entity
