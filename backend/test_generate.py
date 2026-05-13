import httpx
import asyncio
import os

async def main():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise SystemExit("Set GEMINI_API_KEY before running this script.")
    
    # Try gemini-2.0-flash
    model = "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": key}
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": "Hello"}]
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        print(f"{model}: {resp.status_code}")
        if resp.status_code != 200:
            print(resp.text)

if __name__ == "__main__":
    asyncio.run(main())
