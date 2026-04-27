import httpx
import os
import uvicorn

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from src.graph import build_graph
from utils.constants import TELEGRAM_API
from utils.telegram_helpers import extract_message_data, is_bot_mentioned, send_message, build_thread_id


# -----------------------
# App Startup
# -----------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        print("⚠️ WEBHOOK_URL no definida — webhook no registrado automáticamente.")
    else:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TELEGRAM_API}/setWebhook",
                json={"url": webhook_url}
            )
            data = response.json()
            if data.get("ok"):
                print(f"✅ Webhook registrado en: {webhook_url}")
            else:
                print(f"❌ Error registrando webhook: {data}")
 
    yield  # la app corre aquí
 
    # --- Shutdown (opcional, agregar cleanup si se necesita) ---


app = FastAPI(title="IterLens API", lifespan=lifespan)
graph = build_graph()

# -----------------------
# CORS (obligatorio)
# -----------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# Modelo de datos
# -----------------------
class Message(BaseModel):
    from_number: str
    body: str


# -----------------------
# Test Webhook
# -----------------------
@app.post("/webhook/whatsapp")
async def whatsapp_webhook(message: Message):

    result = graph.invoke(
        {
            "messages": [HumanMessage(content=message.body)],
            "user_id": message.from_number
        },
        config={
            "configurable": {
                "thread_id": message.from_number
            }
        }
    )

    # Obtener último mensaje del asistente
    last_message = result["messages"][-1].content

    return {
        "reply": last_message
    }
 
 
# -----------------------
# Webhook principal
# -----------------------
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    update = await request.json()
 
    extracted = extract_message_data(update)
    if not extracted:
        # Update sin texto (sticker, foto, etc.) — ignorar silenciosamente
        return {"ok": True}
 
    chat_id, message_id, user_id, text = extracted
 
    # En grupos, solo responder si el bot fue mencionado o le replican
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "")
    if not is_bot_mentioned(update, bot_username):
        return {"ok": True}
 
    thread_id = build_thread_id(update, user_id)
 
    # Invocar el grafo (misma lógica que antes)
    result = graph.invoke(
        {
            "messages": [HumanMessage(content=text)],
            "user_id": user_id,
        },
        config={
            "configurable": {
                "thread_id": thread_id
            }
        }
    )
 
    reply_text = result["messages"][-1].content
 
    # En grupos, responder en hilo (reply) para que quede claro a quién le habla
    message = update.get("message") or update.get("edited_message")
    chat_type = message["chat"]["type"]
    reply_to = message_id if chat_type != "private" else None
 
    await send_message(chat_id, reply_text, reply_to=reply_to)
 
    return {"ok": True}


# -----------------------
# Health check
# -----------------------
@app.get("/")
def root():
    return {"status": "LensBot API corriendo"}


if __name__ == "__main__":
    dev = os.getenv("DEV", "false").lower() == "true"
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=dev)