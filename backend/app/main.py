from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.routes import overlay
import asyncio
from app.chatbot import run_twitch_bot, run_tiktok_bot
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background tasks
    tiktok_task = asyncio.create_task(run_tiktok_bot())
    twitch_task = asyncio.create_task(run_twitch_bot())

    print("✅ Bots started via lifespan")

    yield  # App is running here

    # Optional: Cleanup logic
    print("🛑 Shutting down...")
    tiktok_task.cancel()
    twitch_task.cancel()

app = FastAPI(lifespan=lifespan)

app.include_router(overlay.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.websocket("/ws/test")
async def websocket_test(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Connected!")