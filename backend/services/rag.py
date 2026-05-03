import os
import re
from dotenv import load_dotenv

load_dotenv()

from groq import Groq
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# ── Config ──
GROQ_MODEL = "llama-3.3-70b-versatile"   # Free, fast, generous limits
MAX_CONTEXT  = 2000
MAX_QUESTION = 300

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Load embeddings once (local, free, no API) ──
print("[INFO] Loading embedding model...")
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"}
)
print("[INFO] Embedding model ready.")

# ── FAISS index cache ──
_faiss_cache = {}


def build_faiss_index(transcript: str, meeting_id: int):
    if meeting_id in _faiss_cache:
        return _faiss_cache[meeting_id]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=40,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = splitter.split_text(transcript)
    if not chunks:
        chunks = [transcript[:400]]

    print(f"[INFO] Building FAISS index: {len(chunks)} chunks for meeting {meeting_id}")
    vectorstore = FAISS.from_texts(chunks, embeddings)
    _faiss_cache[meeting_id] = vectorstore
    print(f"[INFO] FAISS index built and cached for meeting {meeting_id}")
    return vectorstore


def retrieve_context(question: str, vectorstore, k: int = 3) -> str:
    docs = vectorstore.similarity_search(question, k=k)
    context = "\n\n".join([doc.page_content for doc in docs])
    return context[:MAX_CONTEXT]


def call_groq(prompt: str) -> str:
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        temperature=0.3,
    )
    return response.choices[0].message.content


def format_history(chat_history: list) -> str:
    if not chat_history:
        return ""
    recent = chat_history[-8:]
    lines = []
    for msg in recent:
        role = "User" if msg['role'] == 'user' else "Assistant"
        lines.append(f"{role}: {msg['message'][:200]}")
    return "\n".join(lines)


def get_answer(question: str, transcript: str, chat_history: list, meeting_id: int = 0) -> str:
    question = question[:MAX_QUESTION].strip()
    if not question:
        return "Please ask a valid question."

    try:
        vectorstore = build_faiss_index(transcript, meeting_id)
        context = retrieve_context(question, vectorstore)
        history_str = format_history(chat_history)
        history_section = f"\nCONVERSATION HISTORY:\n{history_str}\n" if history_str else ""

        prompt = f"""You are a meeting assistant. Answer the question using ONLY the context below.
If the answer is not in the context, say "I couldn't find that in the transcript."
Keep your answer concise and direct — 2-4 sentences max.
{history_section}
CONTEXT FROM TRANSCRIPT:
{context}

QUESTION: {question}

ANSWER:"""

        return call_groq(prompt)

    except Exception as e:
        print(f"[ERROR] RAG answer failed: {e}")
        return f"Could not get answer: {str(e)[:120]}"