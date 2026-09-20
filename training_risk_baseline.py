"""
Training-Risk Baseline (Rule-Based) — WST-FR-14
يحسب مستوى خطر عدم إتمام التدريب لكل طالب بناءً على:
- نسبة الغياب (attendance_records.status = 'ABSENT')
- عدد التقييمات المعلقة (assessments.sign_off_status = 'PENDING')
- عدد النتائج الضعيفة (assessments.result IN ('FAIL','NEEDS_IMPROVEMENT'))
لا يستخدم أي خاصية محمية (جنس، خلفية، إلخ) — فقط بيانات النشاط التدريبي.
"""

import pandas as pd
from db import get_connection

# عتبات بسيطة وواضحة (قابلة للتعديل لاحقًا بعد رؤية بيانات حقيقية)
ABSENCE_RATE_HIGH = 0.30      # 30% غياب أو أكتر = خطر عالي
ABSENCE_RATE_MEDIUM = 0.15    # 15% إلى 30% = خطر متوسط
PENDING_ASSESSMENTS_HIGH = 3  # 3 تقييمات معلقة أو أكتر = خطر عالي
WEAK_RESULTS_HIGH = 2         # نتيجتين ضعيفتين أو أكتر = خطر عالي


def load_attendance(conn) -> pd.DataFrame:
    query = """
        SELECT student_id, status
        FROM attendance_records
    """
    return pd.read_sql(query, conn)


def load_assessments(conn) -> pd.DataFrame:
    query = """
        SELECT student_id, result, sign_off_status
        FROM assessments
    """
    return pd.read_sql(query, conn)


def compute_attendance_features(attendance: pd.DataFrame) -> pd.DataFrame:
    total = attendance.groupby("student_id").size().rename("total_sessions")
    absent = (
        attendance[attendance["status"] == "ABSENT"]
        .groupby("student_id")
        .size()
        .rename("absent_count")
    )
    features = pd.concat([total, absent], axis=1).fillna(0)
    features["absence_rate"] = features["absent_count"] / features["total_sessions"]
    return features.reset_index()


def compute_assessment_features(assessments: pd.DataFrame) -> pd.DataFrame:
    pending = (
        assessments[assessments["sign_off_status"] == "PENDING"]
        .groupby("student_id")
        .size()
        .rename("pending_assessments")
    )
    weak = (
        assessments[assessments["result"].isin(["FAIL", "NEEDS_IMPROVEMENT"])]
        .groupby("student_id")
        .size()
        .rename("weak_results")
    )
    features = pd.concat([pending, weak], axis=1).fillna(0)
    return features.reset_index()


def compute_risk_level(row) -> tuple[str, list[str]]:
    """يرجع (مستوى الخطر، قائمة الأسباب) — كل قرار لازم يكون قابل للشرح."""
    flags = []

    if row["absence_rate"] >= ABSENCE_RATE_HIGH:
        flags.append(f"نسبة غياب مرتفعة ({row['absence_rate']:.0%})")
    elif row["absence_rate"] >= ABSENCE_RATE_MEDIUM:
        flags.append(f"نسبة غياب متوسطة ({row['absence_rate']:.0%})")

    if row["pending_assessments"] >= PENDING_ASSESSMENTS_HIGH:
        flags.append(f"{int(row['pending_assessments'])} تقييمات لسه معلقة")

    if row["weak_results"] >= WEAK_RESULTS_HIGH:
        flags.append(f"{int(row['weak_results'])} نتائج ضعيفة (FAIL/NEEDS_IMPROVEMENT)")

    # منطق بسيط: أي إشارتين أو أكتر = HIGH، إشارة واحدة = MEDIUM، لا شيء = LOW
    if len(flags) >= 2:
        level = "HIGH"
    elif len(flags) == 1:
        level = "MEDIUM"
    else:
        level = "LOW"

    return level, flags


def build_risk_report(attendance_features: pd.DataFrame, assessment_features: pd.DataFrame) ->
