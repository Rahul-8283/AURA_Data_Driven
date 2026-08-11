import requests
from app.core.config import settings

def test_hf_api():
    api_url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
    headers = {"Authorization": f"Bearer {settings.HF_API_key}"}
    response = requests.post(api_url, headers=headers, json={"inputs": "This is a test sentence."})
    print("Status:", response.status_code)
    print("Response:", response.text[:200])

if __name__ == "__main__":
    test_hf_api()
