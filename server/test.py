# test_gemini.py
import os
from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
from google import genai
from google.genai import types

# ── Init ──────────────────────────────────────────────────────────────────────
API_KEY = os.getenv("GEMINI_API_KEY")

# LLM - gemini-2.0-flash-lite uses least quota (good for free tier)
from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Groq for LLM - free tier, no daily quota issues
llm = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",  # current vision model
    temperature=0,
    groq_api_key=os.getenv("GROQ_API_KEY")
)

embeddings_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-2",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    output_dimensionality=768  # ← truncates to 768, HNSW compatible ✅
)

# ── Test 1: Basic text ────────────────────────────────────────────────────────
def test_text():
    print("\n--- Test 1: Basic Text ---")
    response = llm.invoke([HumanMessage(content="Say hello in one sentence.")])
    print(f"✅ Response: {response.content}")

# ── Test 2: Vision (base64 image) ─────────────────────────────────────────────
def test_vision():
    print("\n--- Test 2: Vision ---")
    import base64

    image_path = r"D:\WhatsApp Image 2024-11-01 at 1.52.46 PM.jpeg"
    
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    message = HumanMessage(content=[
        {"type": "text", "text": "Describe this image in one sentence."},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
    ])

    response = llm.invoke([message])
    print(f"✅ Vision Response: {response.content}")

# ── Test 3: Embeddings ────────────────────────────────────────────────────────
def test_embeddings():
    print("\n--- Test 3: Embeddings ---")
    texts = ["Hello world", "Machine learning is great", "Document processing pipeline"]
    vectors = embeddings_model.embed_documents(texts)

    print(f"✅ Embedded {len(vectors)} texts")
    print(f"✅ Embedding dimensions: {len(vectors[0])}")

# ── Test 4: Similarity check ──────────────────────────────────────────────────
def test_similarity():
    print("\n--- Test 4: Similarity ---")
    import numpy as np

    v1 = embeddings_model.embed_query("cat sitting on a mat")
    v2 = embeddings_model.embed_query("a feline resting on a rug")
    v3 = embeddings_model.embed_query("quarterly revenue report")

    def cosine(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    sim_related = cosine(v1, v2)
    sim_unrelated = cosine(v1, v3)

    print(f"✅ Similar sentences score:   {sim_related:.4f}  (should be HIGH ~0.8+)")
    print(f"✅ Unrelated sentences score: {sim_unrelated:.4f}  (should be LOW ~0.3-)")

# ── Run all ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        test_text()
    except Exception as e:
        print(f"❌ Text test failed: {e}")

    try:
        test_vision()
    except Exception as e:
        print(f"❌ Vision test failed: {e}")

    try:
        test_embeddings()
    except Exception as e:
        print(f"❌ Embeddings test failed: {e}")

    try:
        test_similarity()
    except Exception as e:
        print(f"❌ Similarity test failed: {e}")

    print("\n--- Done ---")

