# diagnose.py
import os
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("=== Models available for generateContent ===")
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(f"  {m.name}")

print("\n=== Models available for embedContent ===")
for m in genai.list_models():
    if "embedContent" in m.supported_generation_methods:
        print(f"  {m.name}")