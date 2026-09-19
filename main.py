import requests
import gradio as gr

API_URL = "http://127.0.0.1:8000"   # where `uvicorn api:app` is running
TIMEOUT = 120                        # seconds to wait for the bot's reply


def auth_headers(user_pass: str) -> dict:
    # Must match the header name in api.py: x_user_pass -> "x-user-pass"
    return {"x-user-pass": user_pass.strip()}


def has_password(user_pass: str) -> bool:
    return bool(user_pass and user_pass.strip())


# ---------- Chat ----------
def respond(message, history, user_pass):
    """Generator: show the user's message right away, then the bot's reply."""
    history = history or []

    if not has_password(user_pass):
        history = history + [{"role": "assistant", "content": "Enter your user password on the right first."}]
        yield message, history
        return

    if not message or not message.strip():
        yield "", history
        return

    # 1) show the user's message immediately and clear the input box
    history = history + [{"role": "user", "content": message}]
    yield "", history

    # 2) call the API and show the reply
    try:
        r = requests.post(
            f"{API_URL}/chat",
            json={"message": message},
            headers=auth_headers(user_pass),
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        reply = r.json()["reply"]
    except requests.exceptions.ConnectionError:
        reply = f"Can't reach the API at {API_URL}. Start it with: uvicorn api:app --reload"
    except requests.exceptions.RequestException as e:
        reply = f"The request failed: {e}"

    yield "", history + [{"role": "assistant", "content": reply}]


def clear_screen():
    # Only clears what you see. It does NOT delete anything on the server.
    return []


# ---------- Long-term memory ----------
def load_memories(user_pass):
    if not has_password(user_pass):
        return "Enter your user password first."
    try:
        r = requests.get(f"{API_URL}/memories", headers=auth_headers(user_pass), timeout=30)
        r.raise_for_status()
        memories = r.json()["memories"]
    except requests.exceptions.RequestException as e:
        return f"Couldn't load memories: {e}"
    return "\n".join(f"- {m}" for m in memories) or "No memories stored yet."


def delete_memories(user_pass):
    if not has_password(user_pass):
        return "", "Enter your user password first."
    try:
        r = requests.delete(f"{API_URL}/memories", headers=auth_headers(user_pass), timeout=30)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        return gr.update(), f"Couldn't delete memories: {e}"
    return "No memories stored yet.", "All memories deleted."


# ---------- Layout ----------
# Gradio 5 needs type="messages" for the dict format used above.
# Gradio 6 removed that argument (messages is the only format), so fall back.
try:
    chatbot = gr.Chatbot(type="messages", height=480, label="Conversation")
except TypeError:
    chatbot = gr.Chatbot(height=480, label="Conversation")

with gr.Blocks(title="TechNest Support Bot") as demo:
    gr.Markdown("# TechNest Support Bot")

    with gr.Row():
        with gr.Column(scale=3):
            chatbot.render()
            msg = gr.Textbox(
                placeholder="Type your message and press Enter",
                show_label=False,
                container=False,
            )
            with gr.Row():
                send_btn = gr.Button("Send", variant="primary")
                clear_btn = gr.Button("Clear screen")

        with gr.Column(scale=1):
            user_pass = gr.Textbox(label="User password", type="password", placeholder="e.g. chroma_test")
            gr.Markdown("### Long-term memory")
            memories_box = gr.Textbox(label="Stored facts", lines=10, interactive=False)
            with gr.Row():
                refresh_btn = gr.Button("Refresh")
                delete_btn = gr.Button("Delete all", variant="stop")
            status = gr.Markdown()

    # chat events
    msg.submit(respond, [msg, chatbot, user_pass], [msg, chatbot])
    send_btn.click(respond, [msg, chatbot, user_pass], [msg, chatbot])
    clear_btn.click(clear_screen, None, chatbot)

    # memory events
    refresh_btn.click(load_memories, user_pass, memories_box)
    delete_btn.click(delete_memories, user_pass, [memories_box, status])

if __name__ == "__main__":
    demo.launch()   # opens at http://127.0.0.1:7860