"""
Training-risk model experiment — WST-FR-14 AI release gate.
Compares a logistic-regression model against the rule-based baseline
(training_risk_baseline.py), on REAL attendance/assessment data.

DOCUMENTED LIMITATION: we have no independently-observed "did this student
actually fail/drop out" outcome in this small synthetic dataset. As a
transparent proxy target we use "completion_rate < 0.5" (not enough
signed-off passing results), computed strictly from activity data —
never protected attributes. Replace with a real outcome once enough
historical terms exist.
"""

import warnings
warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score

from db import get_connection
from predictions_log import start_run, finish_run, log_training_risk_prediction
from training_risk_baseline import (
    load_attendance, load_assessments,
    compute_attendance_features, compute_assessment_features, compute_risk_level,
)


def build_features_and_target(conn):
    attendance = load_attendance(conn)
    assessments = load_assessments(conn)

    att_features = compute_attendance_features(attendance)
    assess_features = compute_assessment_features(assessments)
    merged = att_features.merge(assess_features, on="student_id", how="outer").fillna(0)

    completion_df = pd.read_sql(
        "SELECT student_id, counts_toward_completion FROM assessments", conn
    )
    totals = completion_df.groupby("student_id").size().rename("total_assessments")
    completed = (
        completion_df[completion_df["counts_toward_completion"] == True]
        .groupby("student_id").size().rename("completed_assessments")
    )
    completion = pd.concat([totals, completed], axis=1).fillna(0).reset_index()
    completion["completion_rate"] = completion["completed_assessments"] / completion["total_assessments"].replace(0, 1)

    merged = merged.merge(completion[["student_id", "completion_rate"]], on="student_id", how="left")
    merged["completion_rate"] = merged["completion_rate"].fillna(0)
    merged["actual_at_risk"] = (merged["completion_rate"] < 0.5).astype(int)

    return merged


def main():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users LIMIT 1")
        triggered_by = cur.fetchone()[0]

        cur.execute("SELECT id FROM courses LIMIT 1")
        row = cur.fetchone()
        if row is None:
            print("مفيش أي courses — شغّل seed_data.py الأول.")
            return
        course_id = row[0]

        data = build_features_and_target(conn)
        if len(data) < 6:
            print("مفيش عدد طلاب كافي للتجربة (محتاجين 6 على الأقل) — شغّل seed_data.py الأول.")
            return

        features = ["absence_rate", "pending_assessments", "weak_results"]
        X = data[features]
        y = data["actual_at_risk"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y if y.nunique() > 1 else None
        )

        model = LogisticRegression()
        model.fit(X_train, y_train)
        y_pred_model = model.predict(X_test)

        test_rows = data.loc[X_test.index]
        baseline_levels = test_rows.apply(lambda r: compute_risk_level(r)[0], axis=1)
        y_pred_baseline = (baseline_levels != "LOW").astype(int)

        def safe_metric(fn, y_true, y_pred):
            return round(float(fn(y_true, y_pred, zero_division=0)), 3)

        baseline_precision = safe_metric(precision_score, y_test, y_pred_baseline)
        baseline_recall = safe_metric(recall_score, y_test, y_pred_baseline)
        model_precision = safe_metric(precision_score, y_test, y_pred_model)
        model_recall = safe_metric(recall_score, y_test, y_pred_model)

        print("=== نتائج المقارنة (على proxy target — راجع التحذير في أعلى الملف) ===")
        print(f"Baseline  — precision: {baseline_precision}  recall: {baseline_recall}")
        print(f"ML Model  — precision: {model_precision}  recall: {model_recall}")

        baseline_run = start_run(cur, "TRAINING_RISK", "RULE_BASELINE",
                                  "attendance_assessment_rules", "v1", triggered_by)
        model_run = start_run(cur, "TRAINING_RISK", "ML_MODEL",
                               "logistic_regression_activity_only", "v1", triggered_by,
                               ml_service_status="AVAILABLE")

        for _, row in data.iterrows():
            level, flags = compute_risk_level(row)
            log_training_risk_prediction(
                cur, "RULE_BASELINE", "attendance_assessment_rules", "v1",
                row["student_id"], course_id, level, flags,
                f"مستوى الخطر: {level}",
                [{"factor": f} for f in flags],
                {"absence_rate": row["absence_rate"], "pending_assessments": row["pending_assessments"],
                 "weak_results": row["weak_results"]},
            )

            row_df = pd.DataFrame(
                [[row["absence_rate"], row["pending_assessments"], row["weak_results"]]],
                columns=features,
            )
            model_pred = model.predict(row_df)[0]
            model_level = "HIGH" if model_pred == 1 else "LOW"
            log_training_risk_prediction(
                cur, "ML_MODEL", "logistic_regression_activity_only", "v1",
                row["student_id"], course_id, model_level, [],
                f"تصنيف الموديل: {model_level} (activity features only, no protected attributes)",
                [{"factor": "logistic_regression_score"}],
                {"absence_rate": row["absence_rate"], "pending_assessments": row["pending_assessments"],
                 "weak_results": row["weak_results"]},
            )

        finish_run(cur, baseline_run, len(data))
        finish_run(cur, model_run, len(data))
        conn.commit()
        print(f"\nتم تسجيل {len(data)*2} تنبؤ (baseline + model) في جدول predictions.")

    except Exception as e:
        conn.rollback()
        print("فشلت التجربة، تم التراجع:", e)
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
