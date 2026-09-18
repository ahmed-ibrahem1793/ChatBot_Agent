from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from tools import tools, tools_by_name
import os
from dotenv import load_dotenv

load_dotenv()  
groq_api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(model="openai/gpt-oss-120b").bind_tools(tools)

def chat(user_message: str):
    SYSTEM_PROMPT = """You are a customer service assistant with four tools. Follow this decision order strictly:

        1. retrieve_context — ALWAYS call this first for any question about products, policies, procedures, pricing, or company info. Never answer such questions from memory, even if you think you know the answer.

        2. If retrieve_context returns "No relevant context found" or the info is clearly insufficient, THEN call web_search, followed by web_fetch_jina on the most relevant result, to find current external information (e.g. exchange rates, live news, general facts outside company knowledge).

        3. get_order_state — ONLY call this when the user asks about their own order/account status. Never call it speculatively. If you don't have their user_id, ask for it instead of calling the tool.

        4. For simple greetings, chit-chat, or math/logic questions unrelated to the business or the user's account, answer directly without calling any tool.

        Rules:
        - Never call retrieve_context and web_search in the same turn unless retrieve_context came back empty.
        - Never fabricate order status, prices, or policy details — always retrieve or search first.
        - If a tool returns no useful result, say so honestly rather than guessing.
        - Keep answers short and direct. Cite web sources briefly by name when used.
        """

    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_message)]
    response = llm.invoke(messages)

    while response.tool_calls:
        messages.append(response)
        for call in response.tool_calls:
            result = tools_by_name[call["name"]].invoke(call["args"])
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
        response = llm.invoke(messages)

    return response.content

while True:
    query = input("You: ")
    if query.lower() in ["exit", "quit"]:
        break
    print(chat(query))


