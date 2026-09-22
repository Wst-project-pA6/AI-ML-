import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report

print("=" * 60)
print("1. تدريب نموذج مخاطر الطلاب (Student Risk Model)")
print("=" * 60)

df_students = pd.read_csv('students_and_practical_training.csv')

print(f"عدد سجلات الطلاب: {len(df_students)}")

# Encoding Categorical Variables
le_attendance = LabelEncoder()
df_students['attendance_code'] = le_attendance.fit_transform(
    df_students['attendance_status']
)

le_assessment = LabelEncoder()
df_students['assessment_code'] = le_assessment.fit_transform(
    df_students['task_assessment_result']
)

# Features & Target
X_stu = df_students[
    ['attendance_code', 'assessment_code', 'time_on_task_minutes']
]

y_stu = df_students['ai_training_risk_flag']

# Train / Test Split
X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(
    X_stu,
    y_stu,
    test_size=0.2,
    random_state=42,
    stratify=y_stu
)

print(f"Training samples: {len(X_train_s)}")
print(f"Testing samples: {len(X_test_s)}")

# Random Forest Model
model_students = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model_students.fit(X_train_s, y_train_s)

# Evaluation
y_pred_s = model_students.predict(X_test_s)

print("\nStudent Risk Model Results:")
print(classification_report(y_test_s, y_pred_s))

# Save Student Model + Encoders
joblib.dump(model_students, 'student_risk_model.joblib')
joblib.dump(le_attendance, 'le_attendance.joblib')
joblib.dump(le_assessment, 'le_assessment.joblib')

print("✅ تم حفظ نموذج الطلاب والـ Encoders بنجاح.")


print("\n" + "=" * 60)
print("2. تدريب نموذج إعادة طلب المخزون (Inventory Reorder Model)")
print("=" * 60)

df_vehicles = pd.read_csv('vehicles_and_workshop_jobs.csv')

print(f"عدد سجلات المخزون: {len(df_vehicles)}")

# Features & Target
X_veh = df_vehicles[
    [
        'inventory_on_hand_qty',
        'inventory_min_reorder_level',
        'part_issued_qty',
        'part_unit_cost'
    ]
]

y_veh = df_vehicles['ai_reorder_status']

# Train / Test Split
X_train_v, X_test_v, y_train_v, y_test_v = train_test_split(
    X_veh,
    y_veh,
    test_size=0.2,
    random_state=42,
    stratify=y_veh
)

# Random Forest Model
model_inventory = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model_inventory.fit(X_train_v, y_train_v)

# Evaluation
y_pred_v = model_inventory.predict(X_test_v)

print("\nInventory Reorder Model Results:")
print(classification_report(y_test_v, y_pred_v))

# Save Inventory Model
joblib.dump(model_inventory, 'inventory_reorder_model.joblib')

print("✅ تم حفظ نموذج المخزون بنجاح.")
print("\n🎉 تم الانتهاء من إعادة تدريب جميع النماذج.")