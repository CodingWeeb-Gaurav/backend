from fastapi import FastAPI
from routes import agent_test, chat
from fastapi.middleware.cors import CORSMiddleware

# Update origins to include your PERMANENT ngrok domain
origins = [
    "http://localhost:3000",
    "https://nathaly-purest-ariella.ngrok-free.dev",  # ADD THIS
    "https://localhost:3000",
    "https://nischem.com",
]

app = FastAPI(title="Falcon Chatbot API")

# Add CORS middleware FIRST
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Then include routers
app.include_router(chat.router, prefix="/api/chat")
app.include_router(agent_test.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Falcon Chatbot Backend Running ✅"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)