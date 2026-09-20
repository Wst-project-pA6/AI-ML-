"""
Shared helper to log baseline/model runs into the predictions + prediction_runs
tables, per the schema's AI release-gate requirements (WST-FR-14).
"""

import json
from db import get_connection


def start_run(cur, pred_type, source_kind, source_name, source_version, triggered_by, ml_service_status="NOT_ENABLED"):
    cur.execute("""
        INSERT INTO prediction_runs (type, source_kind, source_name, source_version, triggered_by, ml_service_status)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (pred_type, source_kind, source_name, source_version, triggered_by, ml_service_status))
    return cur.fetchone()[0]


def finish_run(cur, run_id, generated_count):
    cur.execute("""
        UPDATE prediction_runs SET finished_at = now(), generated_count = %s WHERE id = %s
    """, (generated_count, run_id))


def log_reorder_prediction(cur, source_kind, source_name, source_version,
                            store_id, part_id, suggested_quantity, weeks_of_cover,
                            explanation_summary, explanation_factors, reorder_input):
    cur.execute("""
        INSERT INTO predictions (type, source_kind, source_name, source_version,
            explanation_summary, explanation_factors,
            store_id, part_id, reorder_input, reorder_suggested_quantity, reorder_estimated_weeks_of_cover)
        VALUES ('REORDER_SUGGESTION', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (source_kind, source_name, source_version,
          explanation_summary, json.dumps(explanation_factors),
          store_id, part_id, json.dumps(reorder_input), suggested_quantity, weeks_of_cover))


def log_training_risk_prediction(cur, source_kind, source_name, source_version,
                                  student_id, course_id, risk_level, risk_flags,
                                  explanation_summary, explanation_factors, risk_input):
    cur.execute("""
        INSERT INTO predictions (type, source_kind, source_name, source_version,
            explanation_summary, explanation_factors,
            student_id, course_id, risk_level, risk_flags, risk_input)
        VALUES ('TRAINING_RISK', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (source_kind, source_name, source_version,
          explanation_summary, json.dumps(explanation_factors),
          student_id, course_id, risk_level, json.dumps(risk_flags), json.dumps(risk_input)))
