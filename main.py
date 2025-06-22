"""
Municipal Records Processing API - PRODUCTION READY

Transform 18-month waits into 48-hour turnarounds.
Ready to make your first $49 TODAY!
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from datetime import datetime

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from dotenv import load_dotenv

from proprietary.api.endpoints import router as api_router, limiter
from proprietary.api.webhooks import router as webhook_router
from proprietary.api.pricing_assistant import router as pricing_router
from proprietary.database.models import Base
from proprietary.billing.stripe_handler import StripeHandler


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifecycle management."""
    # Startup
    logger.info("=� Starting Municipal Records Processing API - Let's make money! [v2]")
    
    # Database setup
    database_url = os.getenv("DATABASE_URL")
    # Convert postgres:// to postgresql+asyncpg:// for async support
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    
    # Log the database URL pattern (hide sensitive parts)
    if database_url:
        url_parts = database_url.split("@")
        if len(url_parts) > 1:
            logger.info(f"Database URL pattern: {url_parts[0].split('://')[0]}://***@{url_parts[1]}")
    
    # Also handle postgresql:// URLs that need asyncpg
    if database_url and database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(
        database_url,
        echo=os.getenv("DEBUG", "False").lower() == "true",
        pool_size=20,
        max_overflow=0
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info(" Database tables created/verified")
        
    # Create session factory
    async_session = async_sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    # Redis setup
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = await redis.from_url(redis_url, decode_responses=True)
    logger.info(" Redis connected")
    
    # Stripe setup
    stripe_secret = os.getenv("STRIPE_SECRET_KEY")
    # Clean the API key - remove any whitespace/newlines
    if stripe_secret:
        stripe_secret = stripe_secret.strip().replace('\n', '').replace('\r', '').replace(' ', '').replace('\t', '')
        logger.info(f"Stripe key cleaned - length: {len(stripe_secret)}, ends with: ...{stripe_secret[-10:]}")
    
    stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    if stripe_webhook_secret:
        stripe_webhook_secret = stripe_webhook_secret.strip()
    
    if not stripe_secret:
        logger.warning("�  Stripe not configured - payment processing will not work")
        logger.warning("   Set STRIPE_SECRET_KEY in .env file")
        stripe_handler = None
    else:
        stripe_handler = StripeHandler(stripe_secret, stripe_webhook_secret)
        logger.info(" Stripe configured - ready to accept payments!")
    
    # Store in app state
    app.state.db_engine = engine
    app.state.db_session = async_session
    app.state.redis = redis_client
    app.state.stripe = stripe_handler
    
    logger.info(" Application startup complete - READY TO MAKE MONEY! =�")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Municipal Records Processing API")
    await redis_client.close()
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title="Municipal Records Processing LLC",
    description="Automated processing of public records requests. Turn 18-month waits into 48-hour turnarounds.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Include routers
app.include_router(api_router)
app.include_router(webhook_router)
app.include_router(pricing_router)


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    """Add database session to request state."""
    async with app.state.db_session() as session:
        request.state.db = session
        request.state.redis = app.state.redis
        request.state.stripe = app.state.stripe
        response = await call_next(request)
        return response


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please try again later.",
            "type": "internal_server_error"
        }
    )


@app.get("/")
async def root():
    """Root endpoint with revenue-focused information."""
    return {
        "service": "Municipal Records Processing LLC",
        "version": "1.0.0",
        "tagline": "Turn 18-month waits into 48-hour turnarounds",
        "value_proposition": {
            "problem": "Phoenix PD has 18+ month backlog for records",
            "solution": "Automated submission in 60 seconds",
            "price": "$49-99 per request",
            "savings": "$2,441 per insurance claim"
        },
        "endpoints": {
            "submit_request": "/api/v1/submit-request",
            "check_status": "/api/v1/status/{request_id}",
            "health": "/api/v1/health",
            "documentation": "/docs"
        },
        "contact": "enterprise@municipalrecords.com"
    }


@app.get("/robots.txt", include_in_schema=False)
async def robots():
    """Robots.txt to prevent indexing."""
    return Response(
        content="User-agent: *\nDisallow: /\n",
        media_type="text/plain"
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info("=% Starting server - Let's get that first $49!")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )