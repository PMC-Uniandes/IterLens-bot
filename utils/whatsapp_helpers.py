import httpx

from utils.constants import EVOLUTION_API_URL, EVOLUTION_INSTANCE, EVOLUTION_API_KEY

async def send_whatsapp_message(to: str, text: str):
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    payload = {"number": to, "text": text}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload, headers=headers)