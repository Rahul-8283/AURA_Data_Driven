import requests
from app.core.config import settings

def test_gemini_api():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents?key={settings.gemini_api_key}"
    requests_data = {
        "requests": [{"model": "models/text-embedding-004", "content": {"parts": [{"text": "Hello world"}]}}]
    }
    print(f"Key length: {len(settings.gemini_api_key)}, starts with: {settings.gemini_api_key[:5]}")
    resp = requests.post(url, json=requests_data)
    print("Status:", resp.status_code)
    print("Response:", resp.text)

if __name__ == "__main__":
    test_gemini_api()
