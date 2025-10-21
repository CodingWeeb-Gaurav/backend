from fastapi import APIRouter
from services.agent_manager import run_pipeline

router = APIRouter()

@router.get("/test-pipeline")
async def test_pipeline(q: str):
    print("Step 1: User input received:", q)
    result = await run_pipeline(q, "dummy-session")
    print("Step 2: Pipeline result:", result)
    return {"result": result}
