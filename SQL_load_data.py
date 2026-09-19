import psycopg
import os
from dotenv import load_dotenv

load_dotenv()  
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")

with psycopg.connect(
    host=db_host,
    dbname=db_name,
    user=db_user,
    password=db_password,
    port=db_port
) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_orders (
                user_id VARCHAR(50) PRIMARY KEY,
                order_state BOOLEAN NOT NULL
            );
        """)

        sample_data = [
            ("user_001", True),
            ("user_002", False),
            ("user_003", True),
        ]
        cur.executemany(
            "INSERT INTO user_orders (user_id, order_state) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING;",
            sample_data
        )
    conn.commit()