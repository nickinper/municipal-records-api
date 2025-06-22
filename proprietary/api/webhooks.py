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

from ..database.models import Customer, Request as DBRequest, RequestEvent, RequestStatus, CreditPurchase
from ..billing.stripe_handler import StripeHandler
from core.scrapers.phoenix_pd import PhoenixPDScraper
from ..integrations.stripe_tools import update_volume_pricing, apply_retroactive_discount


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
            select(DBRequest).where(DBRequest.request_id == request_id)
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
        log_entry = RequestEvent(
            request_id=request.id,
            event_type="immediate_processing_started",
            event_data={"details": "Processing immediately after payment confirmation"},
            triggered_by="webhook"
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
                log_entry = RequestEvent(
                    request_id=request.id,
                    event_type="submitted_to_phoenix",
                    event_data={
                        "details": f"Confirmation: {result.get('confirmation_number')}",
                        "screenshot_path": str(result.get("evidence_screenshots", [""])[0]),
                        "confirmation_number": result.get('confirmation_number')
                    },
                    triggered_by="webhook"
                )
                db.add(log_entry)
                
                logger.info(f"Successfully submitted request {request_id} to Phoenix PD")
                
                # TODO: Send success email to customer
                
            else:
                # Failed - but don't refund yet, will retry
                request.status = RequestStatus.PAYMENT_RECEIVED
                request.retry_count = 1
                
                log_entry = RequestEvent(
                    request_id=request.id,
                    event_type="submission_failed",
                    event_data={
                        "details": "Initial submission failed, will retry",
                        "error": True
                    },
                    triggered_by="webhook"
                )
                db.add(log_entry)
                
                logger.warning(f"Failed to submit request {request_id}, will retry")
                
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error processing request {request_id}: {str(e)}")
        
        # Log error
        try:
            log_entry = RequestEvent(
                request_id=request.id,
                event_type="processing_error",
                event_data={
                    "details": str(e),
                    "error": True,
                    "error_message": str(e)
                },
                triggered_by="webhook"
            )
            db.add(log_entry)
            await db.commit()
        except:
            pass


async def handle_credit_purchase(payment_data: dict, db: AsyncSession):
    """Handle prepaid credit package purchases."""
    try:
        customer_email = payment_data.get("customer_email")
        metadata = payment_data.get("metadata", {})
        package_type = metadata.get("package_type")
        credits = int(metadata.get("credits", 0))
        amount = payment_data.get("amount", 0) / 100  # Convert from cents
        
        # Find or create customer
        customer_result = await db.execute(
            select(Customer).where(Customer.email == customer_email)
        )
        customer = customer_result.scalar_one_or_none()
        
        if not customer:
            # Create new customer
            from ..billing.stripe_handler import StripeHandler
            stripe_handler = StripeHandler(os.getenv("STRIPE_SECRET_KEY"), "")
            
            customer = Customer(
                email=customer_email,
                api_key=stripe_handler.generate_api_key(),
                api_key_created_at=datetime.utcnow(),
                credits_balance=0
            )
            db.add(customer)
            await db.flush()
        
        # Add credits to customer
        customer.credits_balance += credits
        customer.credits_purchased += credits
        
        # Record the purchase
        purchase = CreditPurchase(
            customer_id=customer.id,
            credits_amount=credits,
            total_cost=amount,
            cost_per_credit=amount / credits if credits > 0 else 0,
            discount_percent=metadata.get("discount_percent", 0),
            stripe_payment_intent_id=payment_data.get("payment_intent"),
            paid_at=datetime.utcnow(),
            status="completed"
        )
        db.add(purchase)
        
        await db.commit()
        
        logger.info(f"Successfully processed credit purchase: {credits} credits for ${amount}")
        
        # TODO: Send confirmation email
        
    except Exception as e:
        logger.error(f"Error handling credit purchase: {str(e)}")


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
                    select(DBRequest).where(DBRequest.request_id == request_id)
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
                    log_entry = RequestEvent(
                        request_id=record_request.id,
                        event_type="payment_received",
                        event_data={
                            "details": f"Payment of ${record_request.payment_amount} received via Stripe",
                            "amount": float(record_request.payment_amount)
                        },
                        triggered_by="webhook"
                    )
                    db.add(log_entry)
                    await db.commit()
                    
                    # Check for volume discount eligibility
                    if customer:
                        # Count total requests this month
                        from sqlalchemy import func
                        monthly_count = await db.execute(
                            select(func.count(Request.id))
                            .where(Request.customer_id == customer.id)
                            .where(Request.created_at >= func.now() - func.cast('30 days', func.interval))
                        )
                        usage_count = monthly_count.scalar() or 0
                        
                        # Update pricing tier if needed
                        pricing_result = update_volume_pricing(
                            customer_id=customer.stripe_customer_id,
                            usage_count=usage_count
                        )
                        
                        if pricing_result.get("success"):
                            logger.info(f"Updated customer to {pricing_result['tier_name']} tier")
                            
                            # Check for retroactive discount
                            if usage_count in [11, 51, 100]:
                                credit_result = apply_retroactive_discount(
                                    customer_id=customer.stripe_customer_id,
                                    order_count=usage_count
                                )
                                if credit_result.get("success"):
                                    logger.info(f"Applied retroactive credit: ${credit_result['credit_amount']}")
                    
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
                    select(DBRequest).where(DBRequest.request_id == request_id)
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
                # First get the request to get its integer ID
                result = await db.execute(
                    select(DBRequest).where(DBRequest.request_id == request_id)
                )
                record_request = result.scalar_one_or_none()
                
                if record_request:
                    log_entry = RequestEvent(
                        request_id=record_request.id,
                        event_type="payment_failed",
                        event_data={
                            "details": f"Payment failed: {payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')}",
                            "error": True
                        },
                        triggered_by="webhook"
                    )
                    db.add(log_entry)
                    await db.commit()
                
                logger.warning(f"Payment failed for request {request_id}")
                
        elif event_type == "payment_link.payment_completed":
            # Credit package purchase
            metadata = event_data.get("metadata", {})
            if metadata.get("type") == "prepaid_credits":
                await handle_credit_purchase(event_data, db)
                
        # Return success to Stripe
        return JSONResponse(content={"status": "success"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {str(e)}")
        # Still return 200 to prevent Stripe retries on our errors
        return JSONResponse(content={"status": "error", "message": str(e)})