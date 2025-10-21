from fastapi import APIRouter, Request
from pydantic import BaseModel
from services.agent_manager import run_pipeline
from core.db import db
import uuid
import datetime
from typing import Optional
router = APIRouter()

# Pydantic model for frontend request
class ChatMessage(BaseModel):
    sessionId: Optional[str] = None
    userAuth: str
    message: str

@router.post("/")
async def chat_endpoint(chat: ChatMessage):
    session_id = chat.sessionId or str(uuid.uuid4())
    user_message = chat.message
    user_auth = chat.userAuth

    # --- Save incoming message to Mongo ---
    await db.chat_sessions.update_one(
        {"_id": session_id},
        {"$push": {"messages": {"role": "user", "message": user_message, "time": datetime.datetime.utcnow()}}},
        upsert=True
    )

    # --- Run dummy agent pipeline for now ---
    ai_reply = await run_pipeline(user_message, session_id)

    # --- Save AI reply to Mongo ---
    await db.chat_sessions.update_one(
        {"_id": session_id},
        {"$push": {"messages": {"role": "ai", "message": ai_reply, "time": datetime.datetime.utcnow()}}},
        upsert=True
    )

    return {"reply": ai_reply, "sessionId": session_id}
