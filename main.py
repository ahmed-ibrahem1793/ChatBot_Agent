from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.prompts import ChatPromptTemplate
from chroma_injection import vectorstore
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from tools import tools, tools_by_name
import os
from dotenv import load_dotenv

load_dotenv()  
groq_api_key = os.getenv("GROQ_API_KEY")

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

