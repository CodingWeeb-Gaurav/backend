import asyncio

async def handle_product_request(user_input: str, session_data: dict):
    """
    Dummy Agent 1: Echo messages, 
    when 'forward' is sent, update session JSON and switch to Agent 2
    """
    response = f"Agent 1 (Product Request): {user_input}"

    # Check if we need to move to next agent
    if user_input.lower() == "forward":
        # Set dummy product info
        session_data["product_id"] = "12345"
        session_data["product_name"] = "Dummy Product"
        session_data["request"] = "quotation"
        session_data["agent"] = "request_details"
        response = "Agent 1 finished. Switching to Agent 2."

    # Add user input and response to session history
    session_data.setdefault("history", []).append({"user": user_input, "agent": response})

    await asyncio.sleep(0.1)  # simulate async work
    return response, session_data
