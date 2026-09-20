"""
WST-FR-14: Training Risk ML Model & Evaluation
"""

import json
import warnings
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from db import get_connection

warnings.filterwarnings("ignore", category=UserWarning)

from training_risk_baseline import (
    load_attendance,
    load_assessments,
    compute_attendance_features,
    compute_assessment_features,
    build_risk_report
)

def prepare_dataset(conn):
    attendance = load_attendance(conn)
    assessments = load_assessments(conn)

    att_f = compute_attendance_features(attendance)
    ass_f = compute_assessment_features(assessments)

    df = pd.merge(att_f, ass_f, on="student_id", how="outer").fillna(0)
    
    if "course_id" in attendance.columns:
        student_course_map = attendance.groupby("student_id")["course_id"].first().to_dict()
        df["course_id"] = df["student_id"].map(student_course_map)
    else:
        df["course_id"] = None

    baseline_df = build_risk_report(att_f, ass_f)
    df["target_risk"] = baseline_df["risk_level"]
    return df

def train_and_evaluate():
    conn = get_connection()
    try:
        df = prepare_dataset(conn)

        X = df[["absence_rate", "pending_assessments", "weak_results"]]
        y = df["target_risk"]

        X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
            X, y, df["student_id"], test_size=0.2, random_state=42
        )

        model = LogisticRegression()
        model.fit(X_train, y_train)

        # حفظ النموذج المدرب على القرصلاستخدامه في API
        joblib.dump(model, "training_risk_model.joblib")

        y_pred = model.predict(X_test)
        
        print("\n==================================================")
        print("         AI RELEASE GATE: EVALUATION REPORT        ")
        print("==================================================")
        print("\n--- Model Classification Report (Precision / Recall) ---")
        print(classification_report(y_test, y_pred, zero_division=0))

        cursor = conn.cursor()

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='predictions';")
        existing_cols = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT id FROM courses LIMIT 1;" if table_exists(cursor, "courses") else "SELECT NULL;")
        default_course_id = cursor.fetchone()
        default_course_id = str(default_course_id[0]) if default_course_id and default_course_id[0] else None

        test_df = df.loc[ids_test.index].copy()
        test_df["ml_pred"] = y_pred

        for _, row in test_df.iterrows():
            explanation = f"ML Predicted: {row['ml_pred']} (Absence: {row['absence_rate']:.0%}, Weak: {int(row['weak_results'])})"
            inputs = {
                "absence_rate": float(row["absence_rate"]),
                "pending_assessments": int(row["pending_assessments"]),
                "weak_results": int(row["weak_results"])
            }

            course_id_val = str(row["course_id"]) if pd.notna(row["course_id"]) and row["course_id"] else default_course_id

            insert_data = {
                "type": "TRAINING_RISK",
                "status": "ACTIVE",
                "source_kind": "ML_MODEL",
                "source_name": "training_risk_model",
                "source_version": "1.0.0",
                "student_id": str(row["student_id"]),
                "course_id": course_id_val,
                "risk_level": str(row["ml_pred"]),
                "explanation_summary": f"Risk Level: {row['ml_pred']}"
            }

            if "explanation" in existing_cols:
                insert_data["explanation"] = explanation
            if "inputs_used" in existing_cols:
                insert_data["inputs_used"] = json.dumps(inputs)
            elif "features" in existing_cols:
                insert_data["features"] = json.dumps(inputs)

            cols = ", ".join(insert_data.keys())
            vals = list(insert_data.values())
            placeholders = ", ".join(["%s"] * len(vals))

            cursor.execute(f"INSERT INTO predictions ({cols}) VALUES ({placeholders});", vals)

        conn.commit()
        print("✅ Saved ML predictions to DB successfully.")
        print("💾 Saved model file to 'training_risk_model.joblib'")

    finally:
        conn.close()

def table_exists(cursor, table_name):
    cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s);", (table_name,))
    return cursor.fetchone()[0]

if __name__ == "__main__":
    train_and_evaluate()
