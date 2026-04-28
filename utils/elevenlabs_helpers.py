import httpx
import os

from utils.constants import TELEGRAM_API, TELEGRAM_TOKEN
from io import BytesIO

from elevenlabs.client import ElevenLabs

elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

async def transcribe_voice(file_id: str) -> str:
    """Descarga un audio de Telegram y lo transcribe con ElevenLabs Scribe."""
    async with httpx.AsyncClient() as client:

        # 1. Obtener file_path desde file_id
        res = await client.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id})
        file_path = res.json()["result"]["file_path"]

        # 2. Descargar el audio en bytes
        audio_res = await client.get(
            f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        )
        audio_bytes = audio_res.content

    # 3. Transcribir con ElevenLabs
    transcription = elevenlabs_client.speech_to_text.convert(
        file=("audio.ogg", BytesIO(audio_bytes)),
        model_id="scribe_v2",
        language_code="spa",  # español
        tag_audio_events=False,
        diarize=False,
    )
    return transcription.text