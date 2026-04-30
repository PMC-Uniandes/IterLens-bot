import os

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# WhatsApp (Evolution API)
EVOLUTION_API_URL = "https://evolution-api-lc58.onrender.com"
EVOLUTION_INSTANCE_TOKEN = os.getenv("EVOLUTION_INSTANCE_TOKEN")
EVOLUTION_INSTANCE  = "lensbot-whatsapp"