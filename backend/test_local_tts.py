import asyncio
import numpy as np
import soundfile as sf

from app.agents.local_tts import LocalKokoroTTS


async def main():
    print("Initializing Kokoro TTS...")

    tts = LocalKokoroTTS()
    stream = tts.synthesize(
        "Hello Rutvik! Let us begin your interview."
    )

    chunks = []

    async with stream:
        async for event in stream:
            audio = event.frame

            samples = np.frombuffer(
                audio.data,
                dtype=np.int16
            )

            chunks.append(samples.copy())

    if not chunks:
        print("ERROR: No audio generated.")
        return

    complete_audio = np.concatenate(chunks)

    duration = len(complete_audio) / 24000

    sf.write(
        "kokoro_test.wav",
        complete_audio.astype(np.float32) / 32768.0,
        24000
    )

    print("\nAudio generation completed!")
    print("Total chunks:", len(chunks))
    print("Total samples:", len(complete_audio))
    print("Total duration:", round(duration, 2), "seconds")
    print("Saved file: kokoro_test.wav")


if __name__ == "__main__":
    asyncio.run(main())
