import requests, os
import psycopg
from ddgs import DDGS
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()  
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")

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
    with psycopg.connect(host=db_host, dbname=db_name, user=db_user, password=db_password, port=db_port) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT order_state FROM user_orders WHERE user_id = %s;", (user_id,))
            row = cur.fetchone()
    return {"order_state": row[0]} if row else {"error": "user not found"}

@tool
def retrieve_context(query: str):
    """Retrieve relevant context from the vectorstore."""
    from chroma_injection import vectorstore
    results = vectorstore.similarity_search(query, k=1)
    return results[0].page_content if results else "No relevant context found."

tools = [web_search, web_fetch_jina, get_order_state, retrieve_context]
tools_by_name = {t.name: t for t in tools}