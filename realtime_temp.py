import asyncio
from gnani.stt import GnaniSTTStreamClient,StreamTranscriptEvent
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    async with GnaniSTTStreamClient(
        api_key=os.getenv("GNANI_API_KEY"),
        language_code="indic-auto",
        model="prisma-v3.0",
        sample_rate=16000
    ) as stream:
        print("Websocket Connected!")
        with open(r"C:\Deep Learning\Gnani_AI_Project\testing_audio.pcm","rb") as f:
            while chunk:=f.read(1024):
                await stream.send_audio(chunk)
                
                await asyncio.sleep(0.032)
                
        async for event in stream:
            if isinstance(event,StreamTranscriptEvent):
                print(event.text)

asyncio.run(main())