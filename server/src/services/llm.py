from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os

models = {
    "chat_llm": ChatGroq(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0,
        groq_api_key=os.getenv("GROQ_API_KEY")
    ),
    "embeddings_llm": ChatGroq(
        model="meta-llama/llama-4-scout-17b-16e-instruct",  # same vision model
        temperature=0,
        groq_api_key=os.getenv("GROQ_API_KEY")
    ),
    "embeddings": GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        output_dimensionality=768
    ),
}