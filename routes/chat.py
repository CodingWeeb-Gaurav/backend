from fastapi import APIRouter, Request
from pydantic import BaseModel
from services.agent_manager import route_message  # <-- changed
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

    # Save incoming message to Mongo
    await db.chat_sessions.update_one(
        {"_id": session_id},
        {"$push": {"messages": {"role": "user", "message": user_message, "time": datetime.datetime.utcnow()}}},
        upsert=True
    )

    # --- Run agent manager pipeline ---
    try:
        ai_reply = await route_message(user_message, session_id, user_auth)
        if not ai_reply:
            ai_reply = "Sorry, something went wrong. Please try again."
    except Exception as e:
        print("Error in route_message:", e)
        ai_reply = "Sorry, something went wrong. Please try again."

    # Save AI reply to Mongo
    await db.chat_sessions.update_one(
        {"_id": session_id},
        {"$push": {"messages": {"role": "ai", "message": ai_reply, "time": datetime.datetime.utcnow()}}},
        upsert=True
    )

    # Always return a valid dict to FE
    return {"reply": ai_reply, "sessionId": session_id}
