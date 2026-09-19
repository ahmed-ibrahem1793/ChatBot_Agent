import os
import psycopg
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()
DB = dict(
    host="localhost",
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=5432,
)

def init_memory_tables():
    with psycopg.connect(**DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id BIGSERIAL PRIMARY KEY,
                user_pass VARCHAR(64) NOT NULL,
                role VARCHAR(10) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_messages (user_pass, id DESC);

            CREATE TABLE IF NOT EXISTS user_memories (
                id BIGSERIAL PRIMARY KEY,
                user_pass VARCHAR(64) NOT NULL,
                fact TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (user_pass, fact)
            );
        """)

init_memory_tables()

sessions = {}  # in-memory cache: user_id -> list of messages

def load_recent_messages(user_pass: str, limit: int = 12):
    with psycopg.connect(**DB) as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages WHERE user_pass = %s ORDER BY id DESC LIMIT %s;",
            (user_pass, limit),
        ).fetchall()
    rows.reverse()
    return [HumanMessage(content=c) if r == "human" else AIMessage(content=c) for r, c in rows]

def get_session_history(user_pass: str):
    if user_pass not in sessions:
        sessions[user_pass] = load_recent_messages(user_pass)
    return sessions[user_pass]

def trim_history(history, max_turns=6):
    return history[-max_turns * 2:]

def save_exchange(user_pass: str, user_text: str, ai_text: str):
    with psycopg.connect(**DB) as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_pass, role, content) VALUES (%s, 'human', %s), (%s, 'ai', %s);",
            (user_pass, user_text, user_pass, ai_text),
        )

def get_memories(user_pass: str, limit: int = 25):
    with psycopg.connect(**DB) as conn:
        rows = conn.execute(
            "SELECT fact FROM user_memories WHERE user_pass = %s ORDER BY id DESC LIMIT %s;",
            (user_pass, limit),
        ).fetchall()
    return [r[0] for r in rows]

def add_memories(user_pass: str, facts: list[str]):
    facts = [f.strip() for f in facts if f and f.strip()]
    if not facts:
        return
    with psycopg.connect(**DB) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO user_memories (user_pass, fact) VALUES (%s, %s) ON CONFLICT (user_pass, fact) DO NOTHING;",
                [(user_pass, f) for f in facts],
            )