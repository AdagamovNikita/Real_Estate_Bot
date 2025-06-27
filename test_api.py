import requests
import json
from config import API_KEY, LLM_URL, LLM_MODEL

def test_api():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/OpenRouterTeam/openrouter-python",
        "X-Title": "Real Estate Bot"
    }
    
    data = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": "Say 'Hello, this is a test!'"
            }
        ]
    }
    
    print("Sending request to OpenRouter API...")
    print(f"URL: {LLM_URL}")
    print(f"Model: {LLM_MODEL}")
    
    try:
        response = requests.post(LLM_URL, headers=headers, json=data, timeout=30)
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and result['choices']:
                print("\nSuccess! Response content:")
                print(result['choices'][0]['message']['content'])
            else:
                print("\nError: Unexpected response format")
                print(json.dumps(result, indent=2))
        else:
            print(f"\nError: API returned status code {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_api() 