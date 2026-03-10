from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from src.graph import build_graph
import uvicorn

app = FastAPI(title="IterLens API")
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


@app.get("/")
def root():
    return {"status": "Axel API corriendo"}


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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)