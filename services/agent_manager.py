# agent_manager.py
from typing import Dict, Any
import datetime
from core.db import db  # your MongoDB client
from agents.product_request import handle_product_request
from agents.request_details import handle_request_details
from agents.address_purpose import handle_address_purpose



# ---------- Field Definitions ---------- #

FIELD_METADATA = {
    "unit": {
        "type": "select",
        "options": ["KG", "TON"],
        "required_for": ["Order", "Sample", "Quote", "ppr"],  # CHANGED HERE
        "agent": 2,
        "description": "Unit of measurement for the product"
    },
    "quantity": {
        "type": "number", 
        "validation": "positive_number",
        "required_for": ["Order", "Sample", "Quote", "ppr"],  # CHANGED HERE
        "agent": 2,
        "description": "Quantity required (must be positive number), greater than or equal to minQuantity and less than available stock" 
    },
    "price_per_unit": {
        "type": "number",
        "validation": "positive_number", 
        "required_for": ["Order", "Sample", "Quote", "ppr"],  # CHANGED HERE
        "agent": 2,
        "description": "Price per unit (must be positive number)"
    },
    "expected_price": {
        "type": "calculated",
        "calculation": "quantity * price_per_unit",
        "required_for": ["Order", "Sample", "Quote", "ppr"],  # CHANGED HERE
        "agent": 2,
        "description": "Automatically calculated total price"
    },
    "address": {
        "type": "select",
        "options": "fetch_from_user_account via API",
        "required_for": ["Order", "Sample", "Quote", "ppr"],  # CHANGED HERE
        "agent": 3,
        "description": "Delivery address (choose from saved addresses)"
    },
    "phone": {
        "type": "phone",
        "validation": "phone_number",
        "required_for": ["Order", "Sample", "Quote"],  # CHANGED HERE
        "agent": 2,
        "description": "Contact phone number"
    },
    "incoterm": {
        "type": "select",
        "options": ["Ex Factory", "Deliver to Buyer Factory"],
        "required_for": ["Order", "Sample", "Quote"],  # CHANGED HERE
        "agent": 2,
        "description": "International commercial terms"
    },
    "mode_of_payment": {
        "type": "select", 
        "options": ["LC", "TT", "Cash"],
        "required_for": ["Order", "Sample", "Quote"],  # CHANGED HERE
        "agent": 2,
        "description": "Payment method"
    },
    "packaging_pref": {
        "type": "select",
        "options": ["Bulk Tanker", "PP Bag", "Jerry Can", "Drum"],
        "required_for": ["Order", "Sample", "Quote"],  # CHANGED HERE
        "agent": 2,
        "description": "Packaging preference"
    },
    "delivery_date": {
        "type": "date",
        "validation": "future_date",
        "required_for": ["Order", "Sample","Quote", "ppr"],  # CHANGED HERE
        "agent": 2,
        "description": "Delivery date (must be after today)"
    },
    "market": {
        "type": "select",
        "options": "fetch_from_site via API",
        "required_for": ["Order", "ppr"],  # CHANGED HERE
        "agent": 3,
        "description": "Target market"
    }
}

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
        "field_metadata": FIELD_METADATA,  # Store field definitions
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
    Add new fields dynamically based on request type with validation rules.
    """
    request_type = data.get("request", "").lower()  # Convert to lowercase for comparison
    
    # Initialize all fields with empty values and metadata
    for field_name, field_meta in FIELD_METADATA.items():
        # Convert required_for values to lowercase for comparison
        required_for_lower = [req.lower() for req in field_meta["required_for"]]
        
        if request_type in required_for_lower:
            if field_name not in data["product_details"]:
                data["product_details"][field_name] = ""
            
            # Store validation info with the field
            if "validation_info" not in data["product_details"]:
                data["product_details"]["validation_info"] = {}
            data["product_details"]["validation_info"][field_name] = {
                "type": field_meta["type"],
                "options": field_meta.get("options", []),
                "validation": field_meta.get("validation", ""),
                "description": field_meta["description"]
            }
    
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

    # If session doesn't exist, start a new one
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