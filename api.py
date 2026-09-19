from fastapi import FastAPI, Depends, Header
from pydantic import BaseModel
from LLM import chat
from history import memory_store, sessions

app = FastAPI(title="TechNest Support Bot")

class ChatRequest(BaseModel):
    message: str

def current_user(x_user_pass: str = Header(...)):
    # PLACEHOLDER auth: anyone can fake this header.
    # Replace with real login / JWT before going public.
    return x_user_pass

@app.post("/chat")
def chat_route(req: ChatRequest, user_pass: str = Depends(current_user)):
    return {"reply": chat(user_pass, req.message)}

@app.get("/memories")
def list_memories(user_pass: str = Depends(current_user)):
    data = memory_store.get(where={"user_pass": user_pass})
    return {"memories": data["documents"]}

@app.delete("/memories")
def delete_memories(user_pass: str = Depends(current_user)):
    memory_store._collection.delete(where={"user_pass": user_pass})
    return {"deleted": True}

@app.post("/reset")
def reset_session(user_pass: str = Depends(current_user)):
    sessions.pop(user_pass, None)   # clears the in-memory cache only
    return {"ok": True}