import requests, os
import psycopg
from ddgs import DDGS
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()  
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")



@tool
def web_search(query: str, max_results: int = 5):
    """Search the web for up-to-date information not in the knowledge base."""
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)
    return [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results]

@tool
def web_fetch_jina(url: str):
    """Fetch the full readable content of a specific URL from search results."""
    try:
        resp = requests.get(f"https://r.jina.ai/{url}", timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"url": url, "error": str(e)}
    return {"url": url, "content": resp.text}

@tool
def get_order_state(user_id: str):
    """Get a user's order state (on/off) from the database."""
    with psycopg.connect(host="localhost", dbname=db_name, user=db_user, password=db_password, port=5432) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT order_state FROM user_orders WHERE user_id = %s;", (user_id,))
            row = cur.fetchone()
    return {"order_state": row[0]} if row else {"error": "user not found"}

tools = [web_search, web_fetch_jina, get_order_state]
tools_by_name = {t.name: t for t in tools}