import requests
from app.core.config import settings

def test_gemini_models():
    if not settings.gemini_api_key:
        print("No Gemini API key found in settings (.env).")
        return
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.gemini_api_key}"
    
    print("Fetching available Gemini models for your API key...")
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        
        models = data.get("models", [])
        if not models:
            print("No models found!")
            return
            
        print(f"\nSuccessfully found {len(models)} models!\n")
        print("Available Model Names:")
        print("-" * 40)
        
        for m in models:
            name = m.get('name')
            display_name = m.get('displayName', 'No Display Name')
            # Only print models that support generateContent
            supported = m.get('supportedGenerationMethods', [])
            if 'generateContent' in supported:
                print(f"- {name}  (Display: {display_name})")
            
    except Exception as e:
        print(f"Failed to fetch models: {e}")
        
if __name__ == "__main__":
    test_gemini_models()
