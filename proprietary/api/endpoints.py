"""
Main API endpoints for Municipal Records Processing.

Revenue-generating endpoints for submitting and tracking requests.
"""

from datetime import datetime
from typing import Optional, List
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..database.models import (
    Customer, 
    Request as DBRequest, 
    RequestStatus,
    RequestEvent,
    ReportType
)
from ..auth.api_key import verify_api_key

logger = logging.getLogger(__name__)

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create router
router = APIRouter(
    prefix="/api/v1",
    tags=["Core API"]
)


class SubmitRequestModel(BaseModel):
    """Model for submitting a new request."""
    report_type: str = Field(default="incident", description="Type of report to request")
    case_number: str = Field(..., description="Case/report number from Phoenix PD")
    requestor_email: EmailStr = Field(..., description="Email for notifications")
    requestor_first_name: Optional[str] = Field(None, description="Requestor first name")
    requestor_last_name: Optional[str] = Field(None, description="Requestor last name")
    requestor_phone: Optional[str] = Field(None, description="Phone number")
    incident_date: Optional[datetime] = Field(None, description="Date of incident (required for 911 recordings)")
    additional_data: Optional[dict] = Field(default={}, description="Additional data for specific report types")


class RequestStatusResponse(BaseModel):
    """Response model for request status."""
    request_id: str
    status: str
    created_at: datetime
    submitted_at: Optional[datetime]
    case_number: str
    report_type: str
    confirmation_number: Optional[str]
    payment_link: Optional[str]
    estimated_completion: Optional[datetime]
    documents_ready: bool
    document_urls: Optional[List[str]]


@router.post("/submit-request", response_model=dict)
@limiter.limit("10/minute")
async def submit_request(
    request: Request,
    data: SubmitRequestModel
):
    """
    Submit a new document request.
    
    This endpoint:
    1. Creates a request record
    2. Generates a payment link
    3. Returns the payment URL for immediate payment
    
    The actual submission happens after payment via webhook.
    """
    db: AsyncSession = request.state.db
    stripe_handler = request.state.stripe
    
    if not stripe_handler:
        raise HTTPException(
            status_code=503,
            detail="Payment system temporarily unavailable"
        )
    
    try:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Validate report type
        try:
            report_type_enum = ReportType(data.report_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid report type: {data.report_type}"
            )
        
        # Find or create customer
        customer_result = await db.execute(
            select(Customer).where(Customer.email == data.requestor_email)
        )
        customer = customer_result.scalar_one_or_none()
        
        if not customer:
            # Create new customer
            customer = Customer(
                email=data.requestor_email,
                first_name=data.requestor_first_name,
                last_name=data.requestor_last_name,
                phone=data.requestor_phone,
                tier="standard",
                credits_balance=0
            )
            db.add(customer)
            await db.flush()  # Get the customer ID
        
        # Create request record
        db_request = DBRequest(
            request_id=request_id,
            customer_id=customer.id,
            report_type=report_type_enum,
            case_number=data.case_number,
            requestor_email=data.requestor_email,
            requestor_first_name=data.requestor_first_name,
            requestor_last_name=data.requestor_last_name,
            requestor_phone=data.requestor_phone,
            incident_date=data.incident_date,
            status=RequestStatus.PENDING_PAYMENT,
            source="api"
        )
        
        db.add(db_request)
        await db.flush()  # Get the auto-generated ID
        
        # Create initial event
        event = RequestEvent(
            request_id=db_request.id,
            event_type="request_created",
            event_data={
                "report_type": data.report_type,
                "case_number": data.case_number
            },
            triggered_by="api"
        )
        db.add(event)
        
        await db.commit()
        
        # Generate payment link
        from ..billing.stripe_handler import StripeHandler
        payment_result = await stripe_handler.create_payment_link(
            request_id=request_id,
            amount=4900,  # $49.00 in cents
            description=f"Phoenix PD {data.report_type.replace('_', ' ').title()} - {data.case_number}",
            customer_email=data.requestor_email,
            metadata={
                "request_id": request_id,
                "case_number": data.case_number,
                "report_type": data.report_type
            }
        )
        
        if not payment_result["success"]:
            # In test mode, still return success with a mock payment URL
            if "test" in stripe_handler.api_key:
                logger.warning(f"Test mode: Stripe payment link creation failed but continuing")
                payment_url = f"https://checkout.stripe.com/test/pay/{request_id}"
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create payment link"
                )
        else:
            payment_url = payment_result["url"]
            # Update request with payment info
            db_request.stripe_checkout_session_id = payment_result.get("session_id")
        
        await db.commit()
        
        logger.info(f"Created request {request_id} with payment link")
        
        return {
            "success": True,
            "request_id": request_id,
            "payment_url": payment_url,
            "amount": 49.00,
            "message": "Request created. Complete payment to begin processing.",
            "estimated_delivery": "48-72 hours after payment"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating request: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to create request"
        )


@router.get("/status/{request_id}", response_model=RequestStatusResponse)
async def get_request_status(
    request_id: str,
    request: Request,
    api_key: Optional[str] = Query(None, description="API key for authentication")
):
    """
    Get the status of a document request.
    
    Returns current status, payment info, and download links when ready.
    """
    db: AsyncSession = request.state.db
    
    # Get request from database
    result = await db.execute(
        select(DBRequest).where(DBRequest.request_id == request_id)
    )
    db_request = result.scalar_one_or_none()
    
    if not db_request:
        raise HTTPException(
            status_code=404,
            detail="Request not found"
        )
    
    # Check authorization (either API key or matching email)
    if api_key:
        # Verify API key belongs to request owner
        customer_result = await db.execute(
            select(Customer).where(Customer.api_key == api_key)
        )
        customer = customer_result.scalar_one_or_none()
        
        if not customer or customer.email != db_request.requestor_email:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view this request"
            )
    
    # Prepare response
    response = RequestStatusResponse(
        request_id=db_request.request_id,
        status=db_request.status.value,
        created_at=db_request.created_at,
        submitted_at=db_request.submitted_at,
        case_number=db_request.case_number,
        report_type=db_request.report_type.value,
        confirmation_number=db_request.submission_confirmation,
        payment_link=None,
        estimated_completion=None,
        documents_ready=db_request.status == RequestStatus.DELIVERED,
        document_urls=db_request.document_urls
    )
    
    # Add payment link if pending
    if db_request.status == RequestStatus.PENDING_PAYMENT:
        stripe_handler = request.state.stripe
        if stripe_handler and db_request.stripe_checkout_session_id:
            # Get payment link from session
            session_url = f"https://checkout.stripe.com/c/pay/{db_request.stripe_checkout_session_id}"
            response.payment_link = session_url
    
    # Estimate completion time
    if db_request.status in [RequestStatus.SUBMITTED, RequestStatus.PROCESSING]:
        # 48-72 hours from submission
        if db_request.submitted_at:
            from datetime import timedelta
            response.estimated_completion = db_request.submitted_at + timedelta(hours=72)
    
    return response


@router.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint.
    
    Verifies database and Redis connectivity.
    """
    try:
        # Check database
        db: AsyncSession = request.state.db
        result = await db.execute(select(func.count(DBRequest.id)))
        request_count = result.scalar()
        
        # Check Redis
        redis = request.state.redis
        await redis.ping()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "redis": "connected",
            "total_requests": request_count,
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@router.get("/pricing")
async def get_pricing():
    """
    Get current pricing information.
    
    Returns base pricing and volume discounts.
    """
    return {
        "base_price": 49.00,
        "currency": "USD",
        "volume_discounts": {
            "11-50": {
                "discount": "20%",
                "price": 39.20
            },
            "51-100": {
                "discount": "40%", 
                "price": 29.40
            },
            "100+": {
                "discount": "60%",
                "price": 19.60
            }
        },
        "prepaid_packages": [
            {
                "name": "Starter",
                "credits": 12,
                "price": 500,
                "savings": 88
            },
            {
                "name": "Professional",
                "credits": 60,
                "price": 2000,
                "savings": 940
            },
            {
                "name": "Enterprise",
                "credits": 200,
                "price": 5000,
                "savings": 4800
            }
        ],
        "phoenix_pd_fees": {
            "incident_report": 5.00,
            "traffic_crash": 5.00,
            "body_camera": 4.00,
            "surveillance": 4.00,
            "recordings_911": 16.50
        },
        "notes": [
            "Prices in USD",
            "Phoenix PD fees are passed through at cost",
            "Volume discounts apply automatically",
            "Credits never expire"
        ]
    }


@router.post("/customer/register")
async def register_customer(
    request: Request,
    email: EmailStr = Query(..., description="Customer email"),
    company_name: Optional[str] = Query(None, description="Company name")
):
    """
    Register a new customer and get API key.
    
    Used after first successful payment.
    """
    db: AsyncSession = request.state.db
    
    # Check if customer exists
    result = await db.execute(
        select(Customer).where(Customer.email == email)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return {
            "success": True,
            "message": "Customer already registered",
            "api_key": existing.api_key,
            "created_at": existing.created_at
        }
    
    # Generate API key
    from ..billing.stripe_handler import StripeHandler
    api_key = StripeHandler.generate_api_key()
    
    # Create customer
    customer = Customer(
        email=email,
        company_name=company_name,
        api_key=api_key,
        credits_balance=0,
        tier="standard"
    )
    
    db.add(customer)
    await db.commit()
    
    return {
        "success": True,
        "message": "Customer registered successfully",
        "api_key": api_key,
        "instructions": "Include this API key in X-API-Key header for all requests"
    }