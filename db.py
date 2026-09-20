import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """يرجع اتصال جديد بالداتا بيز. المسؤول عن قفله هو الكود اللي بيستدعيه."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

if __name__ == "__main__":
    try:
        conn = get_connection()
        print("✅ الاتصال نجح")
        conn.close()
    except Exception as e:
        print("❌ فشل الاتصال:")
        print(e)