# TechNest Support Bot

A customer-support chatbot for a fictional electronics retailer, TechNest. It answers questions from a company handbook (RAG), checks order status in a database, searches the web when the handbook has no answer, and remembers things about each user across conversations.

Built with **LangChain**, the **Groq API**, **ChromaDB**, **PostgreSQL**, **FastAPI**, and **Gradio**.

---

## What the app does

- **Answers from a knowledge base.** The handbook in `assets/` is split into chunks, embedded, and stored in ChromaDB. For any question about products, policies, shipping, returns, and so on, the bot retrieves the most relevant chunk before answering, instead of answering from the model's memory.
- **Uses tools.** The model decides which tool to call: handbook search, order lookup, web search, or web page fetch.
- **Has short-term memory.** The last 6 turns of each conversation are kept in the prompt. They are also saved in PostgreSQL, so they survive a restart.
- **Has long-term memory.** After each reply, a background job extracts durable facts the user stated ("owns a TechNest X", "prefers email") and stores them in ChromaDB. On later messages, the most relevant facts are added to the prompt.
- **Has an HTTP API and a web UI.** FastAPI exposes the bot over HTTP, and a Gradio page uses that API.

### How a message flows through the system

```
Gradio UI (main.py)
   │  POST /chat  + header x-user-pass
   ▼
FastAPI (api.py)
   ▼
chat() in LLM.py
   1. load recent messages           (history.py → memory cache / PostgreSQL)
   2. load relevant user memories    (history.py → ChromaDB "user_memories")
   3. build the system prompt + history + new message
   4. call the Groq model            (it may call tools, in a loop, until it has an answer)
   5. save the exchange to PostgreSQL
   6. in a background thread: extract new facts → ChromaDB "user_memories"
   ▼
reply goes back to the UI
```

### How the bot chooses tools

The system prompt in `LLM.py` sets this order:

1. **`retrieve_context`**: always first for company, product, policy, or pricing questions.
2. **`web_search`, then `web_fetch_jina`**: only if the handbook search finds nothing useful (exchange rates, news, general facts).
3. **`get_order_state`**: only when the user asks about their own order, and only with a user ID. If it doesn't have one, the bot asks.
4. **No tool**: for greetings, chit-chat, and unrelated math or logic.

---

## Project structure

```
.
├── assets/
│   └── TechNest_Support_Handbook.md   # the knowledge base the bot answers from
├── api.py                             # FastAPI routes
├── chroma_injection.py                # loads, chunks, and embeds the handbook into ChromaDB
├── history.py                         # short-term history (PostgreSQL) + long-term memory (ChromaDB)
├── LLM.py                             # the chat() function, system prompt, tool loop, memory extraction
├── main.py                            # Gradio web UI (talks to the FastAPI routes)
├── SQL_load_data.py                   # creates and seeds the user_orders table (run once)
├── tools.py                           # the four tools the model can call
├── .env.example                       # template for your secrets and settings
├── .env                               # your real settings (you create this, never commit it)
└── chroma_db/                         # created automatically: the vector database on disk
```

### What each file does

| File | Role |
|---|---|
| `api.py` | Defines the FastAPI app and its routes (see [API reference](#api-reference)). Reads the user from the `x-user-pass` header and passes it to `chat()`. |
| `LLM.py` | The core. `chat(user_pass, message)` builds the prompt, runs the tool-calling loop against Groq, saves the exchange, and starts memory extraction in a background thread. It also holds the extractor model, which turns a conversation into a list of facts. |
| `history.py` | Everything about memory. Creates the `chat_messages` table, caches recent messages in the `sessions` dict, and reads and writes long-term memories in the `user_memories` ChromaDB collection (with duplicate detection). |
| `tools.py` | The four tools: `retrieve_context` (handbook search), `get_order_state` (PostgreSQL lookup), `web_search` (DuckDuckGo via `ddgs`), and `web_fetch_jina` (reads a page through `r.jina.ai`). |
| `chroma_injection.py` | Reads `assets/TechNest_Support_Handbook.md`, splits it into ~500-character chunks (on `##` and `###` headers first), embeds them with `all-MiniLM-L6-v2`, and stores them in ChromaDB. It also creates the `embedding_model` that `history.py` reuses. |
| `SQL_load_data.py` | One-time setup script. Creates the `user_orders` table and inserts three sample users. |
| `main.py` | The Gradio UI: a chat window, a password box, and buttons to view or delete a user's stored memories. It only calls the API and never touches the database directly. |

### Where the data lives

| Data | Stored in | Notes |
|---|---|---|
| Handbook chunks | ChromaDB, collection `technest_handbook` | Searched by `retrieve_context` |
| User memories (facts) | ChromaDB, collection `user_memories` | Each fact is tagged with the user's ID |
| Chat messages | PostgreSQL, table `chat_messages` | Created automatically by `history.py` |
| Orders | PostgreSQL, table `user_orders` | Created by `SQL_load_data.py` |
| Recent messages (cache) | Python dict `sessions` | Lost when the API restarts, then reloaded from PostgreSQL |

---

## Getting started

### 1. Prerequisites

- **Python 3.10 or newer.** Download it from [python.org](https://www.python.org/downloads/). On Windows, tick **"Add Python to PATH"** during installation. Check with:
  ```
  python --version
  ```
- **PostgreSQL** ([postgresql.org/download](https://www.postgresql.org/download/)), installed and running. Remember the password you set for the `postgres` user.
- **A Groq API key.** Create a free account at [console.groq.com](https://console.groq.com) and generate a key under *API Keys*.
- **An internet connection.** The embedding model is downloaded from Hugging Face on the first run, and the web-search tools need internet access.

### 2. Get the project and create a virtual environment

Open a terminal in the project folder, then create and activate a virtual environment. A virtual environment keeps this project's packages separate from the rest of your system.

```
python -m venv venv
```

Activate it:

| System | Command |
|---|---|
| Windows (PowerShell) | `venv\Scripts\Activate.ps1` |
| Windows (cmd) | `venv\Scripts\activate.bat` |
| macOS / Linux | `source venv/bin/activate` |

When it works, your terminal prompt starts with `(venv)`.

> On Windows PowerShell, if activation is blocked, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

### 3. Install the dependencies

```
pip install fastapi "uvicorn[standard]" gradio requests python-dotenv "psycopg[binary]" ddgs pydantic langchain-core langchain-groq langchain-chroma langchain-huggingface langchain-text-splitters sentence-transformers
```

`sentence-transformers` installs PyTorch, so this step can be a large download. Once everything works, save the exact versions for later:

```
pip freeze > requirements.txt
```

Anyone else can then install everything with `pip install -r requirements.txt`.

### 4. Create the database

Open the PostgreSQL shell (`psql -U postgres`) and create an empty database:

```sql
CREATE DATABASE technest;
```

(You can use any name. It goes in `.env` in the next step.)

### 5. Configure your `.env`

Copy the template:

| System | Command |
|---|---|
| Windows (PowerShell) | `Copy-Item .env.example .env` |
| macOS / Linux | `cp .env.example .env` |

Open `.env` and fill it in:

```
DB_NAME=technest
DB_USER=postgres
DB_HOST=localhost
DB_PORT=5432
DB_PASSWORD=your_postgres_password
GROQ_API_KEY=your_groq_api_key
```

| Variable | Meaning |
|---|---|
| `DB_NAME` | The database you created in step 4 |
| `DB_USER` / `DB_PASSWORD` | Your PostgreSQL login |
| `DB_HOST` / `DB_PORT` | Where PostgreSQL runs (normally `localhost` and `5432`) |
| `GROQ_API_KEY` | Your key from console.groq.com |

Never commit `.env`. If you use git, add this to `.gitignore`:

```
.env
venv/
chroma_db/
__pycache__/
```

### 6. Check the handbook is in place

The knowledge base must be at:

```
assets/TechNest_Support_Handbook.md
```

Run all commands from the project root folder, because the code uses the relative paths `assets/` and `./chroma_db`.

### 7. Seed the orders table (once)

```
python SQL_load_data.py
```

This creates the `user_orders` table with these sample users:

| user_id | order_state |
|---|---|
| `user_001` | on (True) |
| `user_002` | off (False) |
| `user_003` | on (True) |

### 8. Start the API

```
uvicorn api:app --reload
```

The first start takes longer than usual. It downloads the embedding model, embeds the handbook, and creates the `chat_messages` table and the `chroma_db/` folder. The API runs at `http://127.0.0.1:8000`, and interactive docs are at `http://127.0.0.1:8000/docs`.

### 9. Start the UI

In a **second terminal** (activate the venv there too):

```
python main.py
```

Open `http://127.0.0.1:7860` in your browser.

---

## Using the app

1. Type a **user password** in the box on the right. This works as your user ID. Every password has its own chat history and its own memories. Use the same password to get the same "person" back later.
2. Type your message in the chat box and press Enter.
3. Try some questions:
   - *"How long does standard shipping take?"* (answered from the handbook)
   - *"Can I return opened headphones?"* (answered from the handbook)
   - *"What's the current USD to EGP exchange rate?"* (web search)
   - *"What's the status of my order?"* The bot asks for your user ID. Answer with `user_001`, `user_002`, or `user_003`.
   - *"I own a TechNest X and I prefer email."* Wait a few seconds, then click **Refresh** to see the stored fact.
4. **Memory panel:** **Refresh** shows the facts stored for your password, and **Delete all** erases them. Memory extraction runs in the background, so new facts can take a few seconds to appear.
5. **Clear screen** only clears the chat window. It does not delete anything on the server.

To test long-term memory, tell the bot a fact, stop and restart both servers, use the same password, and ask *"What do you know about me?"*.

---

## API reference

Every route needs the header `x-user-pass: <your password>`.

| Method | Route | Body | What it does |
|---|---|---|---|
| `POST` | `/chat` | `{"message": "..."}` | Sends a message and returns `{"reply": "..."}` |
| `GET` | `/memories` | none | Lists the user's stored long-term facts |
| `DELETE` | `/memories` | none | Deletes all of the user's long-term facts |
| `POST` | `/reset` | none | Clears the in-memory cache for the user (see the note below) |

Example:

```
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -H "x-user-pass: chroma_test" \
  -d '{"message": "How long does express shipping take?"}'
```

> `/reset` only empties the in-memory cache. On the next message, the last 12 messages are reloaded from PostgreSQL, so the bot still remembers the conversation. To start a truly fresh conversation, delete the user's rows from `chat_messages`.

---

## Customizing

- **Change the knowledge base:** put a new `.md` file in `assets/` and update `FILENAME` in `chroma_injection.py`.
- **Change the models:** both the chat model and the memory extractor are set to `openai/gpt-oss-120b` in `LLM.py`. You can give the extractor a smaller, cheaper Groq model.
- **Change how much is remembered:** `max_turns` in `trim_history` (short-term window), `k` in `get_memories` (facts injected per message), and the `0.25` distance threshold in `add_memories` (duplicate detection).
- **Change the bot's behavior:** edit `SYSTEM_PROMPT` in `LLM.py`.

---

## Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| `422 Unprocessable Content`, `"loc": ["header", "x-user-pass"]` | The `x-user-pass` header is missing. The name must use hyphens, not underscores. |
| The UI says it can't reach the API | The API isn't running. Start it with `uvicorn api:app --reload`. |
| `connection refused` or `password authentication failed` | PostgreSQL isn't running, or the values in `.env` are wrong. |
| `FileNotFoundError: assets/TechNest_Support_Handbook.md` | The file is missing or misnamed, or you're not running from the project root. |
| `ModuleNotFoundError` | The venv isn't activated, or step 3 didn't finish. |
| Groq errors (401 or 429) | The API key is wrong, or you hit the rate limit. Wait a bit or check your key. |
| Memories don't appear right after a reply | Extraction runs in the background. Wait a few seconds and click Refresh. |

---

## Known limitations

- **Authentication is a placeholder.** The "password" is sent in a header and used directly as the user ID, and it is stored as-is in PostgreSQL and ChromaDB. Anyone can pretend to be any user. Before going public, add real login (for example JWT) and store a hashed or generated ID instead.
- **Order lookups trust the model.** The model supplies the `user_id` for `get_order_state`, so a user could ask about someone else's order. A safer design ties the lookup to the authenticated user.
- **The handbook is re-ingested on every start.** `chroma_injection.py` runs at import time, and `Chroma.from_texts` appends. Restarting adds duplicate handbook chunks. Guard the ingestion with a check like `if vectorstore._collection.count() == 0:`, or move it into a one-time script.
- **Only the top handbook chunk is used.** `retrieve_context` uses `k=1`, so answers that span several sections can be incomplete. Raising it to 3 usually helps.
- **`history.py` ignores `DB_HOST` and `DB_PORT`.** It uses `localhost` and `5432` directly, while `tools.py` and `SQL_load_data.py` read them from `.env`.
- **The cache is per process.** `sessions` lives in memory, so running several API workers gives each its own copy.
- **`/memories` deletion uses a private Chroma attribute** (`_collection`), which could change in a future version.

---

## Tech stack

| Part | Technology |
|---|---|
| LLM | Groq API (`openai/gpt-oss-120b`) through `langchain-groq` |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` through `langchain-huggingface` |
| Vector database | ChromaDB through `langchain-chroma` |
| Relational database | PostgreSQL through `psycopg` |
| Web search and page reading | `ddgs` (DuckDuckGo) and Jina Reader (`r.jina.ai`) |
| API | FastAPI + Uvicorn |
| UI | Gradio |
