import httpx
import asyncio
import os

async def main():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise SystemExit("Set GEMINI_API_KEY before running this script.")
    url = "https://generativelanguage.googleapis.com/v1beta/models"
    headers = {"x-goog-api-key": key}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        data = resp.json()
        models = [m["name"] for m in data.get("models", []) if "flash" in m["name"].lower() or "gemini" in m["name"].lower()]
        print(models)

if __name__ == "__main__":
    asyncio.run(main())
