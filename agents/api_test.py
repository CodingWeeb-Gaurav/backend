import os
from openai import OpenAI
# from dotenv import load_dotenv

# Load environment variables (optional; comment out if hardcoding)
# load_dotenv()

# Hardcode OpenRouter API key (replace with your full key)
OPENROUTER_API_KEY = "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"

# Alternatively, use .env file (uncomment to use)
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# if not OPENROUTER_API_KEY:
#     raise ValueError("OPENROUTER_API_KEY not found in .env file")

# Initialize OpenAI client for OpenRouter
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

def test_openrouter_api(model: str):
    """Tests the OpenRouter API with a given model."""
    print(f"\nTesting OpenRouter API with {model}...")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'API Test Successful'"}
            ],
            max_tokens=20
        )
        reply = response.choices[0].message.content.strip()
        print(f"API Response: '{reply}'")

        if "API Test Successful" in reply:
            print(f"✅ {model} test successful!")
            return True
        else:
            print(f"⚠️ {model} test completed, but response did not match expected output.")
            return False

    except Exception as e:
        print(f"❌ {model} test failed: {e}")
        return False

# Run tests for both models
if __name__ == "__main__":
    # Test Claude-3.5-Sonnet
    test_openrouter_api("anthropic/claude-3.5-sonnet")
    
    # Test GPT-4o
    test_openrouter_api("openai/gpt-4o")