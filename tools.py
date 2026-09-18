import requests, os
import psycopg
from ddgs import DDGS
from dotenv import load_dotenv
from chroma_injection import vectorstore
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

@tool
def retrieve_context(query: str):
    """Retrieve relevant context from the vectorstore."""
    from chroma_injection import vectorstore
    results = vectorstore.similarity_search(query, k=1)
    return results[0].page_content if results else "No relevant context found."

@tool
def save_long_term_fact(user_pass: str, fact: str):
    """Save an important fact about the user for future conversations,
    e.g. preferences, contact info, or details they explicitly ask you to remember."""
    vectorstore.add_texts([fact], metadatas=[{"user_pass": user_pass, "type": "memory"}])
    return "Saved."

@tool
def get_long_term_facts(user_pass: str, query: str, k=3):
    """Retrieve important facts about the user for context in conversations."""
    docs = vectorstore.similarity_search(
        query, k=k, filter={"$and": [{"user_pass": user_pass}, {"type": "memory"}]}
    )
    return "\n".join(d.page_content for d in docs)

tools = [web_search, web_fetch_jina, get_order_state, retrieve_context, save_long_term_fact, get_long_term_facts]
tools_by_name = {t.name: t for t in tools}