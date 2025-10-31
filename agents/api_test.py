import requests

API_KEY = "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"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

data = {
    "model": "gpt-4o-mini",  # you can also try gpt-4o or claude-3-opus
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Test message from my backend — reply with '✅ working' if you received this."}
    ],
}

response = requests.post(API_URL, headers=headers, json=data)

if response.status_code == 200:
    result = response.json()
    print("Response:", result["choices"][0]["message"]["content"])
else:
    print("Error:", response.status_code, response.text)
    