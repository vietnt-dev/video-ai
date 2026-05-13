import asyncio
from app.config import settings
from app.services.gemini_service import imagen_generate

async def main():
    # Use user's new API
    out = await imagen_generate("a beautiful futuristic city at night", "test_imagen.png", "9:16")
    print(f"Result: {out}")

if __name__ == "__main__":
    asyncio.run(main())
