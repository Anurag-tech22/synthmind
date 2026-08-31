import os
import time
from dotenv import load_dotenv
load_dotenv()
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

models = [
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3.7-flash"
]

for m in models:
    t0 = time.time()
    try:
        res = client.models.generate_content(
            model=m,
            contents="Say 'Ready' in one word.",
        )
        dt = time.time() - t0
        print(f"SUCCESS [{m}]: took {dt:.2f}s -> {res.text.strip()}", flush=True)
    except Exception as e:
        dt = time.time() - t0
        print(f"FAILED [{m}]: took {dt:.2f}s -> {str(e)[:100]}", flush=True)
