"""
Synthetic seed data generator for WST — ADDITIVE version.
Preserves existing organization_scopes/users/students/customers/vehicles
(e.g. from wst_seed_data.sql) and only adds inventory + training data on top,
linking training records to the students that already exist.
Safe to re-run: only truncates the tables it owns (inventory + training),
never touches users/students/customers/vehicles.
NO REAL DATA — every value here is fake/random (synthetic data only).
"""

import random
import uuid
from datetime import datetime, timedelta, timezone

from db import get_connection

random.seed(42)
NOW = datetime.now(timezone.utc)


def new_id():
    return str(uuid.uuid4())


def weeks_ago(n):
    return NOW - timedelta(weeks=n)


def main():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM organization_scopes LIMIT 1")
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("no organization_scope found — run wst_seed_data.sql first")
        org_id = row[0]

        cur.execute("SELECT id FROM students ORDER BY student_number")
        student_ids = [r[0] for r in cur.fetchall()]
        if not student_ids:
            raise RuntimeError("no students found — run wst_seed_data.sql first")

        print(f"Found {len(student_ids)} existing students, reusing them.")

        cur.execute("""
            TRUNCATE TABLE
                assessments, attendance_records, enrollments, training_sessions,
                training_groups, course_tasks, courses, practical_tasks,
                competencies, training_terms, bays,
                stock_movements, stock_balances, parts, stores
            CASCADE
        """)

        cur.execute("SELECT id FROM users WHERE email = 'ai.seed.admin@wst-ai.local'")
        row = cur.fetchone()
        if row:
            admin_id = row[0]
        else:
            admin_id = new_id()
            cur.execute("""
                INSERT INTO users (id, email, display_name, password_hash, preferred_locale, status, must_change_password)
                VALUES (%s, 'ai.seed.admin@wst-ai.local', 'Seed Admin', 'fake-hash-not-real', 'en', 'ACTIVE', FALSE)
            """, (admin_id,))
            cur.execute("INSERT INTO user_roles (user_id, role_code) VALUES (%s, 'SYSTEM_ADMIN')", (admin_id,))

        cur.execute("SELECT id FROM users WHERE email = 'ai.seed.mentor@wst-ai.local'")
        row = cur.fetchone()
        if row:
            mentor_id = row[0]
        else:
            mentor_id = new_id()
            cur.execute("""
                INSERT INTO users (id, email, display_name, password_hash, preferred_locale, status, must_change_password)
                VALUES (%s, 'ai.seed.mentor@wst-ai.local', 'Seed Mentor', 'fake-hash-not-real', 'en', 'ACTIVE', FALSE)
            """, (mentor_id,))
            cur.execute("INSERT INTO user_roles (user_id, role_code) VALUES (%s, 'MENTOR')", (mentor_id,))

        cur.execute("SELECT id FROM users WHERE email = 'ai.seed.supervisor@wst-ai.local'")
        row = cur.fetchone()
        if row:
            supervisor_id = row[0]
        else:
            supervisor_id = new_id()
            cur.execute("""
                INSERT INTO users (id, email, display_name, password_hash, preferred_locale, status, must_change_password)
                VALUES (%s, 'ai.seed.supervisor@wst-ai.local', 'Seed Supervisor', 'fake-hash-not-real', 'en', 'ACTIVE', FALSE)
            """, (supervisor_id,))
            cur.execute("INSERT INTO user_roles (user_id, role_code) VALUES (%s, 'TRAINING_SUPERVISOR')", (supervisor_id,))

        store_id = new_id()
        cur.execute("""
            INSERT INTO stores (id, organization_scope_id, code, name, status)
            VALUES (%s, %s, 'ST1', 'Main Store', 'ACTIVE')
        """, (store_id, org_id))

        part_specs = [
            ("Oil Filter", "OILFLT001", 10, 40),
            ("Brake Pad Set", "BRKPAD002", 5, 20),
            ("Air Filter", "AIRFLT003", 8, 30),
            ("Spark Plug", "SPKPLG004", 15, 60),
            ("Timing Belt", "TMBELT005", 3, 12),
        ]

        for name_en, sku, min_level, max_level in part_specs:
            part_id = new_id()
            cur.execute("""
                INSERT INTO parts (id, sku, name_en, category, unit_of_measure,
                                    selling_price_amount, selling_price_currency, status)
                VALUES (%s, %s, %s, 'GENERAL', 'EA', %s, 'EGP', 'ACTIVE')
            """, (part_id, sku, name_en, round(random.uniform(50, 500), 2)))

            on_hand = random.randint(min_level, max_level)

            opening_id = new_id()
            cur.execute("""
                INSERT INTO stock_movements (id, store_id, part_id, type,
                    on_hand_delta, reserved_delta, on_hand_after, reserved_after,
                    actor_id, occurred_at)
                VALUES (%s, %s, %s, 'OPENING_BALANCE', %s, 0, %s, 0, %s, %s)
            """, (opening_id, store_id, part_id, on_hand, on_hand, admin_id, weeks_ago(9)))

            running_balance = on_hand
            for week in range(8, 0, -1):
                qty = random.randint(1, max(1, min_level // 2))
                qty = min(qty, running_balance)
                running_balance -= qty
                cur.execute("""
                    INSERT INTO stock_movements (id, store_id, part_id, type,
                        on_hand_delta, reserved_delta, on_hand_after, reserved_after,
                        actor_id, occurred_at)
                    VALUES (%s, %s, %s, 'ISSUE', %s, 0, %s, 0, %s, %s)
                """, (new_id(), store_id, part_id, -qty, running_balance, admin_id, weeks_ago(week)))

            cur.execute("""
                INSERT INTO stock_balances (store_id, part_id, on_hand, reserved, min_level, max_level,
                                             average_cost_amount, average_cost_currency)
                VALUES (%s, %s, %s, 0, %s, %s, %s, 'EGP')
            """, (store_id, part_id, running_balance, min_level, max_level, round(random.uniform(40, 400), 2)))

        bay_id = new_id()
        cur.execute("""
            INSERT INTO bays (id, organization_scope_id, code, name, capacity, status)
            VALUES (%s, %s, 'BAY1', 'Training Bay 1', 4, 'ACTIVE')
        """, (bay_id, org_id))

        term_id = new_id()
        cur.execute("""
            INSERT INTO training_terms (id, organization_scope_id, name, start_date, end_date, status)
            VALUES (%s, %s, 'Term 1', %s, %s, 'ACTIVE')
        """, (term_id, org_id, (NOW - timedelta(weeks=12)).date(), (NOW + timedelta(weeks=4)).date()))

        competency_id = new_id()
        cur.execute("""
            INSERT INTO competencies (id, code, name_en, status)
            VALUES (%s, 'COMP1', 'Basic Engine Maintenance', 'ACTIVE')
        """, (competency_id,))

        task_ids = []
        for i in range(3):
            task_id = new_id()
            cur.execute("""
                INSERT INTO practical_tasks (id, code, title_en, competency_id, expected_minutes, status)
                VALUES (%s, %s, %s, %s, 60, 'ACTIVE')
            """, (task_id, f"TASK{i+1}", f"Practical Task {i+1}", competency_id))
            task_ids.append(task_id)

        course_id = new_id()
        cur.execute("""
            INSERT INTO courses (id, organization_scope_id, code, name_en, term_id,
                                  minimum_attendance_percent, status)
            VALUES (%s, %s, 'CRS1', 'Automotive Basics', %s, 75, 'ACTIVE')
        """, (course_id, org_id, term_id))

        for task_id in task_ids:
            cur.execute("INSERT INTO course_tasks (course_id, task_id, required) VALUES (%s, %s, TRUE)",
                        (course_id, task_id))

        group_id = new_id()
        cur.execute("""
            INSERT INTO training_groups (id, name, course_id, status)
            VALUES (%s, 'Group A', %s, 'ACTIVE')
        """, (group_id, course_id))

        session_ids = []
        for week in range(4, 0, -1):
            session_id = new_id()
            start = weeks_ago(week)
            cur.execute("""
                INSERT INTO training_sessions (id, title, course_id, group_id, bay_id, mentor_id,
                                                starts_at, ends_at, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'COMPLETED')
            """, (session_id, f"Session Week {week}", course_id, group_id, bay_id, mentor_id,
                  start, start + timedelta(hours=2)))
            session_ids.append(session_id)

        third = max(1, len(student_ids) // 3)
        for i, student_id in enumerate(student_ids):
            cur.execute("""
                INSERT INTO enrollments (id, group_id, course_id, student_id, status)
                VALUES (%s, %s, %s, %s, 'ACTIVE')
            """, (new_id(), group_id, course_id, student_id))

            if i < third:
                absence_chance, weak_chance, pending_chance = 0.05, 0.05, 0.1
            elif i < 2 * third:
                absence_chance, weak_chance, pending_chance = 0.25, 0.2, 0.3
            else:
                absence_chance, weak_chance, pending_chance = 0.5, 0.5, 0.6

            for session_id in session_ids:
                status = "ABSENT" if random.random() < absence_chance else "PRESENT"
                cur.execute("""
                    INSERT INTO attendance_records (id, session_id, student_id, status, recorded_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (new_id(), session_id, student_id, status, mentor_id))

                task_id = random.choice(task_ids)
                if random.random() < weak_chance:
                    result = random.choice(["FAIL", "NEEDS_IMPROVEMENT"])
                else:
                    result = "PASS"

                is_pending = random.random() < pending_chance
                sign_off_status = "PENDING" if is_pending else "SIGNED_OFF"
                signed_off_by = None if is_pending else supervisor_id
                signed_off_at = None if is_pending else NOW
                counts = (not is_pending) and (result == "PASS")

                cur.execute("""
                    INSERT INTO assessments (id, session_id, student_id, task_id, course_id,
                        result, time_on_task_minutes, assessed_by, sign_off_status,
                        signed_off_by, signed_off_at, counts_toward_completion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (new_id(), session_id, student_id, task_id, course_id,
                      result, random.randint(20, 90), mentor_id, sign_off_status,
                      signed_off_by, signed_off_at, counts))

        conn.commit()
        print("Done. Inventory and training data generated (existing students/customers untouched):")
        print(f"   - {len(part_specs)} parts with 8 weeks of stock movements")
        print(f"   - {len(student_ids)} existing students with attendance/assessments for {len(session_ids)} sessions")

    except Exception as e:
        conn.rollback()
        print("FAILED — rolled back all changes:")
        print(e)
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
