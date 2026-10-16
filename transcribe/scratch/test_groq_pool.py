import asyncio
import sys
import httpx
sys.path.insert(0, ".")
from app.config import get_settings

async def main():
    get_settings.cache_clear()
    s = get_settings()
    keys = s.get_groq_keys()
    print("Testing pool of", len(keys), "keys:")
    for idx, k in enumerate(keys, 1):
        headers = {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}
        payload = {
            "model": s.LLM_MODEL,
            "messages": [
                {"role": "system", "content": "You output JSON."},
                {"role": "user", "content": "Return valid JSON with key status and value ok"}
            ],
            "response_format": {"type": "json_object"}
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content")
            print(f"Key {idx} ({k[:15]}...): HTTP {resp.status_code} -> {content}")

if __name__ == "__main__":
    asyncio.run(main())
