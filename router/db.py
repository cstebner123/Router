import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://router:router@127.0.0.1:5432/router")

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

