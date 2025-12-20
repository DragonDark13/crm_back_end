import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def create_database():
    print("DB_USER:", os.getenv("DB_USER"))
    print("DB_PASSWORD:", os.getenv("DB_PASSWORD"))
    conn = psycopg2.connect(
        dbname="postgres",  # підключаємось до системної БД
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    cur = conn.cursor()
    cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")

    exists = cur.fetchone()
    if not exists:
        cur.execute(f'CREATE DATABASE "{DB_NAME}"')
        print(f"[OK] Database '{DB_NAME}' created")
    else:
        print(f"[INFO] Database '{DB_NAME}' already exists")

    cur.close()
    conn.close()


if __name__ == "__main__":
    create_database()
