from fastapi import FastAPI
from routes import agent_test, chat
from fastapi.middleware.cors import CORSMiddleware

origins = ["*"]  # or restrict to your frontend URL
app = FastAPI(title="Falcon Chatbot API")
app.include_router(chat.router, prefix="/api/chat")
# Register routes
app.include_router(agent_test.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Falcon Chatbot Backend Running ✅"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
