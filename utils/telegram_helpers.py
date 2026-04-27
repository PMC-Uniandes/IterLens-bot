import httpx

from utils.constants import TELEGRAM_API

async def send_message(chat_id: int, text: str, reply_to: int = None):
    """
    Envía un mensaje de vuelta al chat de Telegram.
    """
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to
 
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
 
 
def extract_message_data(update: dict) -> tuple[int, int, str, str] | None:
    """
    Extrae (chat_id, message_id, user_id, text) del Update de Telegram.
    Retorna None si el update no contiene un mensaje de texto.
    """
    message = update.get("message") or update.get("edited_message")
    if not message:
        return None
 
    text = message.get("text", "").strip()
    if not text:
        return None
 
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    user_id = str(message["from"]["id"])
 
    return chat_id, message_id, user_id, text
 
 
def build_thread_id(update: dict, user_id: str) -> str:
    """
    Construye el thread_id según el tipo de chat:
    - Chat privado  → user_id  (mismo comportamiento que antes con WhatsApp)
    - Grupo/Supergrupo → "group_{chat_id}:{user_id}"  (estado aislado por usuario dentro del grupo)
    """
    message = update.get("message") or update.get("edited_message")
    chat_type = message["chat"]["type"]  # private | group | supergroup | channel
 
    if chat_type == "private":
        return user_id
    else:
        chat_id = message["chat"]["id"]
        return f"group_{chat_id}:{user_id}"
 
 
def is_bot_mentioned(update: dict, bot_username: str) -> bool:
    """
    En grupos, el bot solo responde si:
    - Lo mencionan con @username, o
    - El mensaje es una respuesta (reply) a un mensaje anterior del bot
    En chats privados siempre responde.
    """
    message = update.get("message") or update.get("edited_message")
    if not message:
        return False
 
    chat_type = message["chat"]["type"]
    if chat_type == "private":
        return True
 
    # Verificar mención directa
    text = message.get("text", "")
    entities = message.get("entities", [])
    for entity in entities:
        if entity["type"] == "mention":
            mention = text[entity["offset"]: entity["offset"] + entity["length"]]
            if mention.lower() == f"@{bot_username.lower()}":
                return True
 
    # Verificar si es reply a un mensaje del bot
    reply_to = message.get("reply_to_message")
    if reply_to and reply_to.get("from", {}).get("is_bot"):
        return True
 
    return False