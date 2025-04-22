from dotenv import load_dotenv
import os
import psycopg2
from contextlib import contextmanager

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}


@contextmanager
def get_cursor():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        yield cur
        conn.commit()
    finally:
        cur.close()
        conn.close()
