"""
Stripe webhook handler for automated request processing.

When payment is received, immediately submit to Phoenix PD.
"""

import os
import logging
from datetime import datetime
import asyncio
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import stripe

from ..database.models import Customer, Request, RequestLog, RequestStatus
from ..billing.stripe_handler import StripeHandler
from core.scrapers.phoenix_pd import PhoenixPDScraper


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def process_request_immediately(
    request_id: str,
    db: AsyncSession
):
    """
    Process a request immediately after payment.
    
    This runs in the webhook handler for instant processing.
    """
    try:
        # Get request from database
        result = await db.execute(
            select(Request).where(Request.id == request_id)
        )
        request = result.scalar_one_or_none()
        
        if not request:
            logger.error(f"Request {request_id} not found")
            return
            
        logger.info(f"Processing request {request_id} immediately after payment")
        
        # Update status
        request.status = RequestStatus.SUBMITTED
        request.submitted_to_portal_at = datetime.utcnow()
        
        # Log the start
        log_entry = RequestLog(
            request_id=request.id,
            action="immediate_processing_started",
            details="Processing immediately after payment confirmation"
        )
        db.add(log_entry)
        await db.commit()
        
        # Initialize scraper
        proxy_url = os.getenv("PROXY_URL")
        
        async with PhoenixPDScraper(
            screenshot_dir="evidence",
            proxy_url=proxy_url,
            headless=True
        ) as scraper:
            # Prepare requestor info
            requestor_info = {
                "email": request.requestor_email,
                "first_name": request.requestor_first_name or "",
                "last_name": request.requestor_last_name or "",
                "phone": request.requestor_phone or ""
            }
            
            # Submit to Phoenix PD
            result = await scraper.submit_report_request(
                case_number=request.case_number,
                requestor_info=requestor_info
            )
            
            if result and result.get("status") == "submitted":
                # Success!
                request.status = RequestStatus.PROCESSING
                request.phoenix_confirmation = result.get("confirmation_number")
                
                # Log success with evidence
                log_entry = RequestLog(
                    request_id=request.id,
                    action="submitted_to_phoenix",
                    details=f"Confirmation: {result.get('confirmation_number')}",
                    screenshot_path=str(result.get("evidence_screenshots", [""])[0])
                )
                db.add(log_entry)
                
                logger.info(f"Successfully submitted request {request_id} to Phoenix PD")
                
                # TODO: Send success email to customer
                
            else:
                # Failed - but don't refund yet, will retry
                request.status = RequestStatus.PAYMENT_RECEIVED
                request.retry_count = 1
                
                log_entry = RequestLog(
                    request_id=request.id,
                    action="submission_failed",
                    details="Initial submission failed, will retry",
                    is_error=True
                )
                db.add(log_entry)
                
                logger.warning(f"Failed to submit request {request_id}, will retry")
                
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error processing request {request_id}: {str(e)}")
        
        # Log error
        try:
            log_entry = RequestLog(
                request_id=request_id,
                action="processing_error",
                details=str(e),
                is_error=True,
                error_message=str(e)
            )
            db.add(log_entry)
            await db.commit()
        except:
            pass


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    stripe_signature: str = Header(None)
):
    """
    Handle Stripe webhook events for immediate processing.
    
    Key events:
    - payment_intent.succeeded: Process request immediately
    - payment_link.payment_completed: Alternative payment confirmation
    """
    try:
        # Get raw body
        body = await request.body()
        
        # Get Stripe handler from app state
        stripe_handler: StripeHandler = request.app.state.stripe
        if not stripe_handler:
            logger.error("Stripe not configured")
            raise HTTPException(status_code=500, detail="Payment system not configured")
            
        # Verify webhook signature
        event = await stripe_handler.verify_webhook(body, stripe_signature)
        if not event:
            raise HTTPException(status_code=400, detail="Invalid signature")
            
        # Get database session
        db: AsyncSession = request.state.db
        
        # Handle different event types
        event_type = event["type"]
        event_data = event["data"]["object"]
        
        logger.info(f"Processing Stripe webhook: {event_type}")
        
        if event_type == "payment_intent.succeeded":
            # Payment successful - process immediately!
            payment_intent = event_data
            request_id = payment_intent.get("metadata", {}).get("request_id")
            
            if request_id:
                # Update request in database
                result = await db.execute(
                    select(Request).where(Request.id == request_id)
                )
                record_request = result.scalar_one_or_none()
                
                if record_request:
                    # Update payment info
                    record_request.status = RequestStatus.PAYMENT_RECEIVED
                    record_request.stripe_payment_intent_id = payment_intent["id"]
                    record_request.payment_received_at = datetime.utcnow()
                    record_request.payment_amount = payment_intent["amount"] / 100
                    
                    # Generate API key for new customers
                    if not record_request.customer_id:
                        email = record_request.requestor_email
                        
                        # Check if customer exists
                        customer_result = await db.execute(
                            select(Customer).where(Customer.email == email)
                        )
                        customer = customer_result.scalar_one_or_none()
                        
                        if not customer:
                            # Create new customer with API key
                            customer = Customer(
                                email=email,
                                stripe_customer_id=payment_intent.get("customer"),
                                api_key=stripe_handler.generate_api_key(),
                                api_key_created_at=datetime.utcnow()
                            )
                            db.add(customer)
                            
                        record_request.customer_id = customer.id
                        
                    # Log payment received
                    log_entry = RequestLog(
                        request_id=record_request.id,
                        action="payment_received",
                        details=f"Payment of ${record_request.payment_amount} received via Stripe"
                    )
                    db.add(log_entry)
                    await db.commit()
                    
                    # PROCESS IMMEDIATELY IN BACKGROUND
                    background_tasks.add_task(
                        process_request_immediately,
                        request_id,
                        db
                    )
                    
                    logger.info(f"Payment received for request {request_id}, processing immediately")
                    
        elif event_type == "checkout.session.completed":
            # Alternative payment confirmation
            session = event_data
            request_id = session.get("metadata", {}).get("request_id")
            
            if request_id and session.get("payment_status") == "paid":
                # Process similar to payment_intent.succeeded
                result = await db.execute(
                    select(Request).where(Request.id == request_id)
                )
                record_request = result.scalar_one_or_none()
                
                if record_request and record_request.status == RequestStatus.PENDING_PAYMENT:
                    record_request.status = RequestStatus.PAYMENT_RECEIVED
                    record_request.payment_received_at = datetime.utcnow()
                    
                    await db.commit()
                    
                    # Process immediately
                    background_tasks.add_task(
                        process_request_immediately,
                        request_id,
                        db
                    )
                    
        elif event_type == "payment_intent.payment_failed":
            # Payment failed
            payment_intent = event_data
            request_id = payment_intent.get("metadata", {}).get("request_id")
            
            if request_id:
                # Log the failure
                log_entry = RequestLog(
                    request_id=request_id,
                    action="payment_failed",
                    details=f"Payment failed: {payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')}",
                    is_error=True
                )
                db.add(log_entry)
                await db.commit()
                
                logger.warning(f"Payment failed for request {request_id}")
                
        # Return success to Stripe
        return JSONResponse(content={"status": "success"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {str(e)}")
        # Still return 200 to prevent Stripe retries on our errors
        return JSONResponse(content={"status": "error", "message": str(e)})