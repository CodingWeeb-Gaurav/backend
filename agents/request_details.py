import asyncio

async def handle_request_details(user_input: str, session_data: dict):
    """
    Dummy Agent 2: Echo messages, 
    when 'forward' is sent, update JSON and switch to Agent 3
    """
    response = f"Agent 2 (Request Details): {user_input}"

    if user_input.lower() == "forward":
        # Add placeholder fields for testing
        session_data["product_details"] = {
            "unit": "KG",
            "quantity": 100,
            "price_per_unit": 50,
            "expected_price": 5000
        }
        session_data["agent"] = "address_purpose"
        response = "Agent 2 finished. Switching to Agent 3."

    session_data.setdefault("history", []).append({"user": user_input, "agent": response})
    await asyncio.sleep(0.1)
    return response, session_data
