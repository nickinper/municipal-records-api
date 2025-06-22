"""
API endpoints for the Claude-powered pricing assistant.

Provides AI-driven pricing support and automated discounts.
"""

from fastapi import APIRouter, HTTPException, Header, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
import logging
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai.claude_pricing_agent import PricingAgent, ConversationManager
from ..database.models import Customer, Request as DBRequest
from ..auth.api_key import verify_api_key

logger = logging.getLogger(__name__)

# Initialize conversation manager
conversation_manager = ConversationManager()

# Create router
router = APIRouter(
    prefix="/api/v1/pricing",
    tags=["Pricing Assistant"]
)


class PricingQuery(BaseModel):
    """Pricing assistant query model."""
    query: str = Field(..., description="Customer's pricing question or request")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    agent_type: Optional[str] = Field("pricing", description="Type of agent: pricing, sales, or support")


class PricingResponse(BaseModel):
    """Pricing assistant response model."""
    success: bool
    response: str
    session_id: str
    actions: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


async def get_customer_data(
    api_key: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """Get customer data from API key."""
    # Find customer by API key
    result = await db.execute(
        select(Customer).where(Customer.api_key == api_key)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Get usage data
    monthly_usage = await db.execute(
        select(func.count(DBRequest.id))
        .where(DBRequest.customer_id == customer.id)
        .where(DBRequest.created_at >= func.now() - func.cast('30 days', func.interval))
    )
    monthly_count = monthly_usage.scalar() or 0
    
    # Get total usage
    total_usage = await db.execute(
        select(func.count(DBRequest.id))
        .where(DBRequest.customer_id == customer.id)
    )
    total_count = total_usage.scalar() or 0
    
    return {
        "stripe_id": customer.stripe_customer_id,
        "email": customer.email,
        "monthly_usage": monthly_count,
        "total_requests": total_count,
        "account_type": customer.tier.value if customer.tier else "standard",
        "current_tier": customer.tier.value if customer.tier else "standard",
        "credits_balance": customer.credits_balance or 0,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "company_name": customer.company_name
    }


@router.post("/assistant", response_model=PricingResponse)
async def pricing_assistant(
    query: PricingQuery,
    request: Request,
    api_key: str = Header(None, alias="X-API-Key")
):
    """
    AI-powered pricing assistant endpoint.
    
    Handles pricing questions, applies discounts, and creates payment links.
    """
    db = request.state.db
    
    # Verify API key and get customer data
    try:
        customer_data = await get_customer_data(api_key, db)
    except HTTPException as e:
        # For public pricing queries, use anonymous data
        if query.agent_type == "sales":
            customer_data = {
                "stripe_id": None,
                "email": None,
                "monthly_usage": 0,
                "total_requests": 0,
                "account_type": "prospect",
                "current_tier": "standard",
                "credits_balance": 0
            }
        else:
            raise e
    
    # Generate or use session ID
    session_id = query.session_id or str(uuid.uuid4())
    
    # Get conversation history
    conversation_history = conversation_manager.get_conversation(session_id)
    
    # Initialize Claude agent
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        raise HTTPException(
            status_code=500,
            detail="AI assistant not configured"
        )
    
    agent = PricingAgent(anthropic_key, agent_type=query.agent_type)
    
    try:
        # Process the query
        result = await agent.handle_pricing_request(
            customer_query=query.query,
            customer_data=customer_data,
            conversation_history=conversation_history
        )
        
        # Update conversation history
        conversation_manager.add_message(session_id, "user", query.query)
        conversation_manager.add_message(session_id, "assistant", result["response"])
        
        # Log the interaction
        logger.info(f"Pricing assistant query from {customer_data.get('email', 'anonymous')}: {query.query[:50]}...")
        
        return PricingResponse(
            success=result["success"],
            response=result["response"],
            session_id=session_id,
            actions=result.get("actions"),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error in pricing assistant: {str(e)}")
        return PricingResponse(
            success=False,
            response="I apologize, but I encountered an error. Please try again or contact support@municipalrecordsprocessing.com",
            session_id=session_id,
            error=str(e)
        )


@router.get("/check-discount-eligibility")
async def check_discount_eligibility(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """
    Check if customer is eligible for automatic volume discounts.
    
    Returns current pricing tier and potential savings.
    """
    db = request.state.db
    customer_data = await get_customer_data(api_key, db)
    
    # Import pricing utilities
    from ..integrations.stripe_tools import calculate_customer_savings
    
    # Calculate savings
    savings_analysis = calculate_customer_savings(
        customer_id=customer_data["stripe_id"],
        monthly_usage=customer_data["monthly_usage"]
    )
    
    # Check if eligible for tier upgrade
    current_usage = customer_data["monthly_usage"]
    current_tier = customer_data["current_tier"]
    
    next_tier = None
    reports_to_next = 0
    
    if current_usage < 11:
        next_tier = "bulk"
        reports_to_next = 11 - current_usage
    elif current_usage < 51:
        next_tier = "volume"
        reports_to_next = 51 - current_usage
    elif current_usage < 100:
        next_tier = "enterprise"
        reports_to_next = 100 - current_usage
    
    return {
        "current_tier": current_tier,
        "current_usage": current_usage,
        "next_tier": next_tier,
        "reports_to_next_tier": reports_to_next,
        "savings_analysis": savings_analysis,
        "message": f"You're currently on the {current_tier} tier. " + 
                  (f"Order {reports_to_next} more reports this month to reach {next_tier} tier!" if next_tier else "You're already on our best tier!")
    }


@router.post("/clear-conversation")
async def clear_conversation(
    session_id: str,
    api_key: str = Header(None, alias="X-API-Key")
):
    """Clear conversation history for a session."""
    conversation_manager.clear_conversation(session_id)
    return {"success": True, "message": "Conversation cleared"}


@router.get("/prepaid-packages")
async def get_prepaid_packages():
    """Get available prepaid credit packages."""
    return {
        "packages": [
            {
                "name": "Starter",
                "credits": 12,
                "price": 500,
                "savings": 88,
                "price_per_credit": 41.67
            },
            {
                "name": "Professional",
                "credits": 60,
                "price": 2000,
                "savings": 940,
                "price_per_credit": 33.33
            },
            {
                "name": "Enterprise",
                "credits": 200,
                "price": 5000,
                "savings": 4800,
                "price_per_credit": 25.00
            }
        ],
        "benefits": [
            "Credits never expire",
            "Use anytime, no monthly commitment",
            "Automatic best pricing",
            "Priority support included"
        ]
    }


# Example conversations for testing
EXAMPLE_QUERIES = [
    {
        "query": "We're doing about 75 requests per month now. What's our best option?",
        "expected_actions": ["calculate_savings", "create_prepaid_package"]
    },
    {
        "query": "How do volume discounts work?",
        "expected_actions": []
    },
    {
        "query": "I want to buy the professional package",
        "expected_actions": ["create_prepaid_package"]
    },
    {
        "query": "We just hit 51 orders this month. Do we get a discount?",
        "expected_actions": ["update_volume_pricing", "apply_retroactive_credit"]
    }
]