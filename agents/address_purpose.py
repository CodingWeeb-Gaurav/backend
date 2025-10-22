import asyncio

async def handle_address_purpose(user_input: str, session_data: dict):
    """
    Dummy Agent 3: Echo messages, final agent
    """
    response = f"Agent 3 (Address Purpose): {user_input}"

    # Final dummy values
    if user_input.lower() == "forward":
        session_data["address"] = "Dummy Address 123"
        session_data["industry"] = "Dummy Industry"
        response = "Agent 3 finished. Chat session complete."

    session_data.setdefault("history", []).append({"user": user_input, "agent": response})
    await asyncio.sleep(0.1)
    return response, session_data
