import os
import requests
from dotenv import load_dotenv

load_dotenv()

openrouter_key = os.getenv("OPENROUTER_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

print(f"OpenRouter Key: {openrouter_key[:10] if openrouter_key else 'None'}...")
print(f"Gemini Key: {gemini_key[:10] if gemini_key else 'None'}...")

print("\n--- Testing OpenRouter ---")
if openrouter_key:
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "google/gemini-2.5-flash",
                "messages": [{"role": "user", "content": "Hello"}],
            },
            timeout=10
        )
        print("Status:", response.status_code)
        print("Response:", response.text[:200])
    except Exception as e:
        print("Error:", e)
else:
    print("No OpenRouter Key")

print("\n--- Testing Gemini ---")
if gemini_key:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        payload = {
            "contents": [{"parts": [{"text": "Hello"}]}]
        }
        response = requests.post(url, json=payload, timeout=10)
        print("Status:", response.status_code)
        print("Response:", response.text[:200])
    except Exception as e:
        print("Error:", e)
else:
    print("No Gemini Key")
