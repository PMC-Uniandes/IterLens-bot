"""Telegram message parsing utilities."""

from integrations.elevenlabs.stt import transcribe_audio


async def extract_message_data(update: dict) -> tuple[int, int, str, str] | None:
    """Extract (chat_id, message_id, user_id, text) from a Telegram update.

    Handles text messages and voice messages (via ElevenLabs transcription).

    Args:
        update: The raw Telegram update dictionary.

    Returns:
        A tuple of (chat_id, message_id, user_id, text), or None if no valid message.
    """
    message = update.get("message") or update.get("edited_message")
    if not message:
        return None

    text = message.get("text", "").strip()
    if not text:
        voice = message.get("voice")
        if voice:
            text = await transcribe_voice(voice["file_id"])
            if not text:
                return None

    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    user_id = str(message["from"]["id"])

    return chat_id, message_id, user_id, text


async def transcribe_voice(file_id: str) -> str:
    """Download a voice message from Telegram and transcribe it.

    Args:
        file_id: The Telegram file identifier for the voice message.

    Returns:
        The transcribed text, or empty string on failure.
    """
    import httpx
    import os

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_api = f"https://api.telegram.org/bot{telegram_token}"

    async with httpx.AsyncClient() as client:
        res = await client.get(f"{telegram_api}/getFile", params={"file_id": file_id})
        file_path = res.json().get("result", {}).get("file_path")
        if not file_path:
            return ""

        audio_res = await client.get(
            f"https://api.telegram.org/file/bot{telegram_token}/{file_path}"
        )
        audio_bytes = audio_res.content

    return await transcribe_audio(audio_bytes)


def build_thread_id(update: dict, user_id: str) -> str:
    """Build a thread ID based on chat type.

    Private chats use user_id directly. Group chats use a composite key
    to isolate state per user within the group.

    Args:
        update: The raw Telegram update dictionary.
        user_id: The Telegram user ID as string.

    Returns:
        A thread ID string for LangGraph state persistence.
    """
    message = update.get("message") or update.get("edited_message")
    chat_type = message["chat"]["type"]

    if chat_type == "private":
        return user_id

    chat_id = message["chat"]["id"]
    return f"group_{chat_id}:{user_id}"


def is_bot_mentioned(update: dict, bot_username: str) -> bool:
    """Check if the bot should respond to this update.

    In private chats, always respond. In groups, only respond if
    mentioned by @username or if replying to the bot's message.

    Args:
        update: The raw Telegram update dictionary.
        bot_username: The bot's Telegram username.

    Returns:
        True if the bot should respond, False otherwise.
    """
    message = update.get("message") or update.get("edited_message")
    if not message:
        return False

    chat_type = message["chat"]["type"]
    if chat_type == "private":
        return True

    text = message.get("text", "")
    entities = message.get("entities", [])
    for entity in entities:
        if entity["type"] == "mention":
            mention = text[entity["offset"]: entity["offset"] + entity["length"]]
            if mention.lower() == f"@{bot_username.lower()}":
                return True

    reply_to = message.get("reply_to_message")
    if reply_to and reply_to.get("from", {}).get("is_bot"):
        return True

    return False
