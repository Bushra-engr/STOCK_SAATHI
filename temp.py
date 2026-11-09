from gnani.stt import GnaniSTTClient
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("GNANI_API_KEY")

client = GnaniSTTClient(api_key=API_KEY)

result = client.transcribe(
    audio=r"C:\Deep Learning\Gnani_AI_Project\testing_audio.ogg",
    language_code="indic-auto",
    model="prisma-v3.0",
    format="transcribe",
    itn_native_numerals=True,
)

print(result["transcript"])