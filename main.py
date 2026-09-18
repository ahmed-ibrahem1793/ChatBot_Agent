from ddgs import DDGS
import requests
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.prompts import ChatPromptTemplate
import psycopg
from chroma_injection import vectorstore
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
import os
from dotenv import load_dotenv

load_dotenv()  
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
groq_api_key = os.getenv("GROQ_API_KEY")

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

llm = ChatGroq(model="openai/gpt-oss-120b").bind_tools(tools)

def chat(user_message: str, retrieved_context: str):
    system_prompt = f"""You are a customer service assistant.
Use the RETRIEVED CONTEXT as your primary source. If it doesn't answer the
question, use web_search then web_fetch_jina. Use get_order_state only for
order-status questions, and ask for user_id if missing.

RETRIEVED CONTEXT:
{retrieved_context}"""

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
    response = llm.invoke(messages)

    while response.tool_calls:
        messages.append(response)
        for call in response.tool_calls:
            result = tools_by_name[call["name"]].invoke(call["args"])
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
        response = llm.invoke(messages)

    return response.content

while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        break

    query = user_input
    results = vectorstore.similarity_search(query, k=1)
    top_result = results[0].page_content if results else "No relevant context found."

    print(chat(query, top_result))
# query = "Is my order active?"
# results = vectorstore.similarity_search(query, k=1)
# top_result = results[0].page_content if results else "No relevant context found."

# print(chat(query, top_result))

