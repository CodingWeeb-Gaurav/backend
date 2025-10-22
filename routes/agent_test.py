from fastapi import APIRouter
from services.agent_manager import route_message


router = APIRouter()

@router.get("/test-pipeline")
async def test_pipeline(q: str):
    print("Step 1: User input received:", q)
    # Pass dummy session_id and user_auth
    result = await route_message(q, session_id="dummy-session", user_auth="dummy-auth")
    print("Step 2: Pipeline result:", result)
    return {"result": result}
