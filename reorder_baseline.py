"""
Reorder Baseline (Rule-Based) — WST-FR-14
يحسب اقتراح إعادة الطلب لكل (مخزن، قطعة) بناءً على:
- متوسط الاستهلاك الأسبوعي (من stock_movements، type='ISSUE'، آخر N أسبوع)
- مستوى min/max المسجل في stock_balances لكل مخزن
لا يعتمد على أي موديل ML — هذا هو الـ baseline الذي يجب أن يهزمه أي موديل مستقبلي.
"""

import pandas as pd
from db import get_connection

LOOKBACK_WEEKS = 8  # نفس القيمة الافتراضية في prediction_settings.reorder_lookback_weeks


def load_stock_movements(conn, weeks: int) -> pd.DataFrame:
    query = """
        SELECT store_id, part_id, on_hand_delta, occurred_at
        FROM stock_movements
        WHERE occurred_at >= now() - (%s || ' weeks')::interval
          AND type = 'ISSUE'
    """
    return pd.read_sql(query, conn, params=(weeks,))


def load_stock_balances(conn) -> pd.DataFrame:
    query = """
        SELECT
            sb.store_id, sb.part_id,
            sb.on_hand, sb.reserved, sb.min_level, sb.max_level,
            p.sku, p.name_en
        FROM stock_balances sb
        JOIN parts p ON p.id = sb.part_id
    """
    return pd.read_sql(query, conn)


def compute_weekly_average_consumption(movements: pd.DataFrame, weeks: int) -> pd.DataFrame:
    """متوسط الاستهلاك الأسبوعي لكل (مخزن، قطعة). on_hand_delta سالب في حركات ISSUE، فناخد القيمة المطلقة."""
    consumption = (
        movements.groupby(["store_id", "part_id"])["on_hand_delta"]
        .sum()
        .abs()
        .reset_index(name="total_consumed")
    )
    consumption["avg_weekly_consumption"] = consumption["total_consumed"] / weeks
    return consumption


def build_reorder_suggestions(balances: pd.DataFrame, consumption: pd.DataFrame) -> pd.DataFrame:
    merged = balances.merge(consumption, on=["store_id", "part_id"], how="left")
    merged["avg_weekly_consumption"] = merged["avg_weekly_consumption"].fillna(0)

    available = merged["on_hand"] - merged["reserved"]

    # يقترح إعادة الطلب فقط لو المتاح أقل من أو يساوي الحد الأدنى
    needs_reorder = available <= merged["min_level"]
    merged["suggested_quantity"] = 0
    merged.loc[needs_reorder, "suggested_quantity"] = (
        merged.loc[needs_reorder, "max_level"] - available[needs_reorder]
    ).clip(lower=0)

    return merged[[
        "store_id", "part_id", "sku", "name_en",
        "on_hand", "reserved", "min_level", "max_level",
        "avg_weekly_consumption", "suggested_quantity"
    ]].query("suggested_quantity > 0")


def main():
    conn = get_connection()
    try:
        balances = load_stock_balances(conn)
        movements = load_stock_movements(conn, LOOKBACK_WEEKS)
        consumption = compute_weekly_average_consumption(movements, LOOKBACK_WEEKS)
        suggestions = build_reorder_suggestions(balances, consumption)

        if suggestions.empty:
            print("مفيش أي قطعة محتاجة إعادة طلب دلوقتي.")
        else:
            print(suggestions.to_string(index=False))
    finally:
        conn.close()


if __name__ == "__main__":
    main()