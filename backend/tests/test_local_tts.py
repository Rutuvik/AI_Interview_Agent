import asyncio
from app.agents.local_tts import LocalKokoroTTS


async def main():
    print("Initializing Kokoro TTS...")

    tts = LocalKokoroTTS()

    print("Creating synthesis stream...")

    stream = tts.synthesize(
        "Hello Rutvik! Let us begin your interview."
    )

    print("Stream created:", type(stream).__name__)

    await stream.aclose()

    print("Stream closed successfully.")


if __name__ == "__main__":
    asyncio.run(main())