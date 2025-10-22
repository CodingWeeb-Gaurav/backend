import asyncio
from core.db import db

async def init_database():
    # Create indexes
    await db.session_states.create_index("_id")
    await db.chat_sessions.create_index("_id")
    print("Database indexes created!")

if __name__ == "__main__":
    asyncio.run(init_database())