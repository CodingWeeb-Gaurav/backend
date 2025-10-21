from agents.fetch_agent import fetch_data
from agents.reasoning_agent import reason_about_data
from agents.summarizer_agent import summarize_response

async def run_pipeline(user_input: str, session_id: str):
    fetched = await fetch_data(user_input)
    reasoned = await reason_about_data(fetched)
    summary = await summarize_response(reasoned)
    return summary
