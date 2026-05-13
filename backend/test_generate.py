import httpx
import asyncio

async def main():
    key = "AIzaSyCNgeuMfwXtTGX9HfN1LDglAU-1MY5EO20"
    
    # Try gemini-2.0-flash
    model = "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": "Hello"}]
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        print(f"{model}: {resp.status_code}")
        if resp.status_code != 200:
            print(resp.text)

if __name__ == "__main__":
    asyncio.run(main())
