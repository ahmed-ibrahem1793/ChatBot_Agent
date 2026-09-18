import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# --- 1. Load the markdown file from assets/ ---
ASSETS_DIR = "assets"
FILENAME = "TechNest_Support_Handbook.md"
file_path = os.path.join(ASSETS_DIR, FILENAME)

with open(file_path, "r", encoding="utf-8") as f:
    document_text = f.read()

# --- 2. Chunk it, splitting on headers first ---
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=75,
    separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""]
)
chunks = splitter.split_text(document_text)

# --- 3. Embed and store in Chroma ---
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore = Chroma.from_texts(
    texts=chunks,
    embedding=embedding_model,
    collection_name="technest_handbook",
    persist_directory="./chroma_db"
)
