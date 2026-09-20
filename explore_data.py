import pandas as pd

# تحميل البيانات
df_vehicles = pd.read_csv('vehicles_and_workshop_jobs.csv')
df_students = pd.read_csv('students_and_practical_training.csv')

print("=" * 60)
print("1. ملخص بيانات الطلاب والتدريب:")
print("=" * 60)
print(f"- إجمالي سجلات الطلاب: {len(df_students)}")
print(f"- توزيع مخاطر التدريب (AI Risk Flag):\n{df_students['ai_training_risk_flag'].value_counts()}")
print(f"- توزيع حالات الحضور:\n{df_students['attendance_status'].value_counts()}")
print(f"- توزيع تقييم المهام:\n{df_students['task_assessment_result'].value_counts()}")

print("\n" + "=" * 60)
print("2. ملخص بيانات الورشة والمخزون:")
print("=" * 60)
print(f"- إجمالي سجلات أوامر العمل: {len(df_vehicles)}")
print(f"- توزيع حالات إعادة الطلب (AI Reorder Status):\n{df_vehicles['ai_reorder_status'].value_counts()}")
print(f"- إجمالي الإيرادات (EGP): {df_vehicles['invoice_grand_total_egp'].sum():,.2f}")
print(f"- متوسط ساعات العمل لكل مهمة: {df_vehicles['labor_hours_logged'].mean():.1f} ساعة")

