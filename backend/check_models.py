import httpx
import asyncio

async def main():
    key = "AIzaSyCNgeuMfwXtTGX9HfN1LDglAU-1MY5EO20"
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()
        models = [m["name"] for m in data.get("models", []) if "flash" in m["name"].lower() or "gemini" in m["name"].lower()]
        print(models)

if __name__ == "__main__":
    asyncio.run(main())
