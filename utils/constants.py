import os

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# WhatsApp (Evolution API)
EVOLUTION_API_URL = "https://evolution-api-lc58.onrender.com"
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE  = "lensbot-whatsapp"