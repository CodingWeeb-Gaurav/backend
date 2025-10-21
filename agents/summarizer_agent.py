async def summarize_response(reasoned: dict):
    text = reasoned.get("reasoned_data", "")
    return f"Final summary prepared from: {text}"
