from chroma_injection import vectorstore

sessions = {}  # user_id -> list of messages

def get_session_history(user_pass: str):
    if user_pass not in sessions:
        sessions[user_pass] = []
    return sessions[user_pass]

def trim_history(history, max_turns=6):
    # keep system prompt logic separate; just cap raw turns
    return history[-max_turns*2:]

def get_long_term_facts(user_pass: str, query: str, k=3):
    docs = vectorstore.similarity_search(
        query, k=k, filter={"$and": [{"user_pass": user_pass}, {"type": "memory"}]}
    )
    return "\n".join(d.page_content for d in docs)


# save_long_term_fact("100", "User prefers to be contacted by email, not phone.")
# print(get_long_term_facts("100", "how should I contact this user?"))