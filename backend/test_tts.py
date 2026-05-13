import asyncio
import edge_tts

async def main():
    text = "Nếu bạn sinh tháng 3, đây là điều vũ trụ muốn nói với bạn..."
    voice = "vi-VN-HoaiMyNeural"
    communicate = edge_tts.Communicate(text, voice)
    try:
        await communicate.save("test_tts.mp3")
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
