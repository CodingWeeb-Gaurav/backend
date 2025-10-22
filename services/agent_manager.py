# agent_manager.py
from typing import Dict, Any
import datetime
from core.db import db  # your MongoDB client
from agents.product_request import handle_product_request
from agents.request_details import handle_request_details
from agents.address_purpose import handle_address_purpose

# ---------- Helper Functions ---------- #

async def save_to_mongo_stub(session_id: str, message: str, response: str):
    """
    Placeholder for saving conversation logs to MongoDB.
    Currently does nothing. Can implement detailed logging here later.
    """
    pass

async def create_new_session(session_id: str, user_auth: str) -> Dict[str, Any]:
    """
    Create a new session document in MongoDB.
    """
    data = {
        "agent": "product_request",
        "product_id": "",
        "product_name": "",
        "product_details": {},
        "request": "",
        "session_id": session_id,
        "userAuth": user_auth,
        "history": [],
        "last_updated": datetime.datetime.utcnow()
    }
    await db.agent_sessions.update_one(
        {"_id": session_id},
        {"$set": data},
        upsert=True
    )
    return data

async def load_session(session_id: str) -> Dict[str, Any]:
    """
    Load session document from MongoDB.
    """
    # Clean old sessions (>1 day)
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    await db.agent_sessions.delete_many({"last_updated": {"$lt": cutoff}})

    session = await db.agent_sessions.find_one({"_id": session_id})
    return session

async def save_session(session_id: str, data: Dict[str, Any]):
    """
    Save session document to MongoDB.
    """
    data["last_updated"] = datetime.datetime.utcnow()
    await db.agent_sessions.update_one(
        {"_id": session_id},
        {"$set": data},
        upsert=True
    )

# ---------- Dynamic Field Management ---------- #

def expand_session_for_request(data: Dict[str, Any]):
    """
    Add new fields dynamically based on request type.
    """
    request_type = data.get("request", "").lower()
    base_fields = {
        "unit": "",
        "quantity": "",
        "price_per_unit": "",
        "expected_price": "",
        "address": "",
        "phone": "",
        "incoterm": "",
        "mode_of_payment": "",
        "packaging_pref": "",
        "delivery_date": "",
        "market": "",
    }

    new_fields = {}
    if request_type in ["order", "sample", "quotation", "ppr"]:
        new_fields.update(base_fields)
        if request_type == "quotation":
            del new_fields["market"]
            del new_fields["delivery_date"]
        elif request_type in ["sample", "order"]:
            del new_fields["market"]
        elif request_type == "ppr":
            del new_fields["phone"]

    data["product_details"].update(new_fields)
    return data

def expand_session_for_address_purpose(data: Dict[str, Any]):
    """
    Add address and industry fields for final agent.
    """
    data["address"] = ""
    data["industry"] = ""
    return data

# ---------- Agent Manager Core ---------- #

async def route_message(user_input: str, session_id: str, user_auth: str) -> str:
    """
    Main function that routes user input to the correct agent,
    updates MongoDB state, and returns the AI response.
    """
    session_data = await load_session(session_id)

    # If session doesn’t exist, start a new one
    if not session_data:
        session_data = await create_new_session(session_id, user_auth)
        current_agent = "product_request"
    else:
        current_agent = session_data.get("agent", "product_request")

    response = ""

    # ---------- Agent Routing ----------
    if current_agent == "product_request":
        response, session_data = await handle_product_request(user_input, session_data)
        if session_data.get("agent") == "request_details":
            session_data = expand_session_for_request(session_data)

    elif current_agent == "request_details":
        response, session_data = await handle_request_details(user_input, session_data)
        if session_data.get("agent") == "address_purpose":
            session_data = expand_session_for_address_purpose(session_data)

    elif current_agent == "address_purpose":
        response, session_data = await handle_address_purpose(user_input, session_data)

    else:
        response = "⚠️ Unknown agent state. Restarting session..."
        session_data = await create_new_session(session_id, user_auth)

    # Save session to MongoDB
    await save_session(session_id, session_data)
    await save_to_mongo_stub(session_id, user_input, response)

    return response
