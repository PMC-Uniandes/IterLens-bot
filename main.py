"""FastAPI application entry point for the IterLens bot."""

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import test, whatsapp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("IterLens API starting — WhatsApp mode (Telegram disabled)")
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
