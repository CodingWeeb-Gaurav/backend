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
