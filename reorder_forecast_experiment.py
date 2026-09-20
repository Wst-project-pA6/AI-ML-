"""
Reorder demand-forecast experiment — WST-FR-14 AI release gate.
Compares a simple linear-trend model against the moving-average RULE_BASELINE
(reorder_baseline.py) on REAL data from stock_movements, using a time-based
train/test split. Logs BOTH results to predictions/prediction_runs.
"""

import warnings
warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")

import numpy as np
import pandas as pd
from db import get_connection
from predictions_log import start_run, finish_run, log_reorder_prediction

TOTAL_WEEKS = 8
TEST_WEEKS = 2
TRAIN_WEEKS = TOTAL_WEEKS - TEST_WEEKS


def load_weekly_consumption(conn):
    query = """
        SELECT store_id, part_id, on_hand_delta, occurred_at
        FROM stock_movements
        WHERE type = 'ISSUE'
          AND occurred_at >= now() - (%s || ' weeks')::interval
    """
    df = pd.read_sql(query, conn, params=(TOTAL_WEEKS,))
    if df.empty:
        return df
    df["week_index"] = ((pd.Timestamp.now(tz="UTC") - df["occurred_at"]).dt.days // 7)
    df["week_index"] = TOTAL_WEEKS - 1 - df["week_index"]
    weekly = (
        df.groupby(["store_id", "part_id", "week_index"])["on_hand_delta"]
        .sum().abs().reset_index(name="consumed")
    )
    return weekly


def evaluate_part(series: pd.Series):
    train = series.iloc[:TRAIN_WEEKS].values
    test = series.iloc[TRAIN_WEEKS:].values
    if len(train) < 3 or len(test) == 0:
        return None

    baseline_pred = np.full(len(test), train.mean())
    baseline_mae = float(np.mean(np.abs(test - baseline_pred)))

    x_train = np.arange(len(train))
    coeffs = np.polyfit(x_train, train, deg=1)
    x_test = np.arange(len(train), len(train) + len(test))
    model_pred = np.polyval(coeffs, x_test)
    model_pred = np.clip(model_pred, a_min=0, a_max=None)
    model_mae = float(np.mean(np.abs(test - model_pred)))

    denom = np.sum(np.abs(test)) or 1.0
    baseline_wape = float(np.sum(np.abs(test - baseline_pred)) / denom)
    model_wape = float(np.sum(np.abs(test - model_pred)) / denom)

    return {
        "baseline_mae": round(baseline_mae, 3), "model_mae": round(model_mae, 3),
        "baseline_wape": round(baseline_wape, 3), "model_wape": round(model_wape, 3),
        "model_wins": model_mae < baseline_mae,
        "next_week_baseline": round(float(train.mean()), 2),
        "next_week_model": round(float(np.polyval(coeffs, len(train))), 2),
    }


def main():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users LIMIT 1")
        triggered_by = cur.fetchone()[0]

        weekly = load_weekly_consumption(conn)
        if weekly.empty:
            print("مفيش بيانات استهلاك كافية — شغّل seed_data.py الأول.")
            return

        baseline_run = start_run(cur, "REORDER_SUGGESTION", "RULE_BASELINE",
                                  "moving_average_baseline", "v1", triggered_by)
        model_run = start_run(cur, "REORDER_SUGGESTION", "ML_MODEL",
                               "linear_trend_forecast", "v1", triggered_by,
                               ml_service_status="AVAILABLE")

        results = []
        baseline_count = model_count = 0
        for (store_id, part_id), group in weekly.groupby(["store_id", "part_id"]):
            group = group.sort_values("week_index")
            metrics = evaluate_part(group["consumed"])
            if metrics is None:
                continue

            log_reorder_prediction(
                cur, "RULE_BASELINE", "moving_average_baseline", "v1",
                store_id, part_id, max(1, round(metrics["next_week_baseline"])), None,
                f"متوسط الاستهلاك الأسبوعي = {metrics['next_week_baseline']}",
                [{"factor": "avg_weekly_consumption", "value": metrics["next_week_baseline"]}],
                {"train_weeks": TRAIN_WEEKS, "mae": metrics["baseline_mae"]},
            )
            baseline_count += 1

            log_reorder_prediction(
                cur, "ML_MODEL", "linear_trend_forecast", "v1",
                store_id, part_id, max(1, round(metrics["next_week_model"])), None,
                f"اتجاه خطي عبر {TRAIN_WEEKS} أسابيع، توقع الأسبوع القادم = {metrics['next_week_model']}",
                [{"factor": "linear_trend", "value": metrics["next_week_model"]}],
                {"train_weeks": TRAIN_WEEKS, "mae": metrics["model_mae"]},
            )
            model_count += 1

            results.append({"store_id": store_id, "part_id": part_id, **metrics})

        finish_run(cur, baseline_run, baseline_count)
        finish_run(cur, model_run, model_count)
        conn.commit()

        report = pd.DataFrame(results)
        print(report.to_string(index=False))
        if not report.empty:
            print(f"\nمتوسط MAE — Baseline: {report['baseline_mae'].mean():.3f} | Model: {report['model_mae'].mean():.3f}")
            print(f"الموديل غلب الـ baseline في {report['model_wins'].sum()} من {len(report)} قطعة/مخزن.")
    except Exception as e:
        conn.rollback()
        print("فشلت التجربة، تم التراجع:", e)
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
