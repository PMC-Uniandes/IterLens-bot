"""FastAPI application entry point for the IterLens bot."""

import logging
import os
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import telegram, whatsapp, test

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN', '')}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Register the Telegram webhook on startup."""
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        logger.warning("WEBHOOK_URL not configured — webhook not registered automatically.")
    else:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{TELEGRAM_API}/setWebhook",
                    json={"url": webhook_url},
                )
                data = response.json()
                if data.get("ok"):
                    logger.info("Webhook registered at: %s", webhook_url)
                else:
                    logger.error("Webhook registration failed: %s", data)
        except Exception:
            logger.exception("Failed to register Telegram webhook")

    yield


app = FastAPI(title="IterLens API", lifespan=lifespan)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telegram.router)
app.include_router(whatsapp.router)
app.include_router(test.router)


@app.get("/")
async def root() -> dict:
    """Health check endpoint."""
    return {"status": "LensBot API running"}


if __name__ == "__main__":
    is_dev = os.getenv("DEV", "false").lower() == "true"
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=is_dev,
    )
