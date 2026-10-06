import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

from app.core.config import settings
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.neo4j_setup import setup_constraints
    try:
        await asyncio.to_thread(setup_constraints)
    except Exception as e:
        logger.error(f"Neo4j constraint setup skipped: {e}")
    yield

app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    description="Core AI analysis engine for AURA.",
    version="1.0.0"
)

# CORS configuration to allow the API Gateway to talk to this service
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    # When running directly, start the uvicorn server
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
