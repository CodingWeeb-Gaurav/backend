async def reason_about_data(fetched: dict):
    data = fetched.get("fetched_data", "")
    return {"reasoned_data": f"Reasoned insight based on: {data}"}
