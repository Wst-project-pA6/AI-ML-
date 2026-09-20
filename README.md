# WST AI — Reorder & Training-Risk Predictions

جزء الـ AI/ML من مشروع WST (Workshop Management & Student Practical Training)،
Badr University DevHub — Project 6. يغطي متطلب WST-FR-14 (Parts-demand و
training-risk flags) بالكامل: rule baseline إلزامي + تجربة موديل ML مقارنة بيه،
مع تسجيل كل تنبؤ في جدول predictions حسب schema المشروع.

## الملفات

| الملف | الوظيفة |
|---|---|
| db.py | الاتصال بـ PostgreSQL (بيانات الاتصال في .env، مش متتبعة في git) |
| reorder_baseline.py | Rule baseline لاقتراح إعادة طلب القطع |
| training_risk_baseline.py | Rule baseline لخطر عدم إتمام التدريب |
| seed_data.py | يولّد بيانات مخزون وتدريب وهمية — إضافي فقط |
| predictions_log.py | تسجيل موحّد لأي تنبؤ في predictions و prediction_runs |
| reorder_forecast_experiment.py | مقارنة موديل اتجاه خطي بالـ baseline — MAE/WAPE |
| training_risk_experiment.py | مقارنة Logistic Regression بالـ baseline — precision/recall |

## الإعداد

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

اعمل .env (مش متتبع في git):

DB_HOST=localhost
DB_PORT=5432
DB_NAME=wst_dev
DB_USER=your_user
DB_PASSWORD=your_password

## الترتيب اللي تشغّل بيه

python3 db.py
python3 seed_data.py
python3 reorder_baseline.py
python3 training_risk_baseline.py
python3 reorder_forecast_experiment.py
python3 training_risk_experiment.py

## قيود موثقة (Known Limitations)

- بيانات الاستهلاك في seed_data.py عشوائية بالكامل، فمفيهاش اتجاه حقيقي.
  النتيجة المتوقعة إن الـ rule baseline يغلب موديل الاتجاه الخطي على البيانات دي.
  ده سلوك صحيح، مش خطأ. على بيانات إنتاج حقيقية النتيجة هتختلف.
- training_risk_experiment.py بيستخدم proxy target (completion_rate اقل من 0.5)
  لأنه مفيش outcome حقيقي مرصود في بيانات صناعية صغيرة كده.
  المفروض يتستبدل بـ outcome حقيقي بعد ما يبقى فيه تيرمات كفاية من بيانات حقيقية.
- الموديلات هنا استشارية بس (advisory-only) — مفيش أي أوردر شراء أو قرار طالب
  بيتاخد تلقائيًا؛ القرار دايمًا محتاج مستخدم بشري.

## ملاحظة عن Gemini prototype

فيه نسخة سابقة اتعملت بأداة AI تانية (train_models.py, app.py, الخ) كانت بتتدرب
على CSV فيه عمود نتيجة مُولّد صناعيًا مسبقًا، وده بيخلي أي تقييم للموديل غير حقيقي.
الملفات دي اتشالت من تتبع git (لسه موجودة محليًا للمراجعة) واستُبدلت بالكامل
بالنهج ده اللي بيتدرب على بيانات الـ schema الحقيقية.
