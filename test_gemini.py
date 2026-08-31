import json
import os
import time
import urllib.request

# Read key from backend/.env
key = None
if os.path.exists("backend/.env"):
    with open("backend/.env", "r") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                key = line.strip().split("=", 1)[1]
                break

if not key:
    key = os.environ.get("GEMINI_API_KEY", "")

if not key:
    print("❌ Error: GEMINI_API_KEY not found in backend/.env or environment.")
    exit(1)

models = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-2.5-flash",
]

print("=" * 60)
print("🚀 Testing Google Gemini Models (SynthMind)")
print("=" * 60)

for m in models:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": "Say 'SynthMind Online' in Marathi and English."}]}]
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            dt = time.time() - t0
            print(f"✅ [{m}] ({dt:.2f}s): {text[:60]}")
    except Exception as e:
        dt = time.time() - t0
        print(f"⚠️  [{m}] ({dt:.2f}s): {str(e)[:70]}")

print("=" * 60)
