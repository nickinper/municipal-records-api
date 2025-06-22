#!/usr/bin/env python3
"""
Manually process a payment for testing when webhooks aren't working.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from proprietary.database.models import Request, RequestStatus, RequestEvent, Customer
from proprietary.billing.stripe_handler import StripeHandler
from core.scrapers.phoenix_pd import PhoenixPDScraper

async def process_payment(request_id: str):
    """Manually process a payment."""
    # Database connection
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://municipal_user:municipal_pass@localhost:5432/municipal_records")
    engine = create_async_engine(database_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Get the request
        result = await db.execute(
            select(Request).where(Request.request_id == request_id)
        )
        request = result.scalar_one_or_none()
        
        if not request:
            print(f"❌ Request {request_id} not found")
            return
            
        print(f"📋 Found request: {request.case_number}")
        print(f"   Status: {request.status.value}")
        print(f"   Email: {request.requestor_email}")
        
        if request.status != RequestStatus.PENDING_PAYMENT:
            print(f"⚠️  Request is not pending payment (status: {request.status.value})")
            return
            
        # Initialize Stripe
        stripe_key = os.getenv("STRIPE_SECRET_KEY")
        stripe_handler = StripeHandler(stripe_key, "")
        
        # Verify the checkout session
        if request.stripe_checkout_session_id:
            print(f"\n🔍 Checking Stripe session: {request.stripe_checkout_session_id}")
            session = await stripe_handler.retrieve_session(request.stripe_checkout_session_id)
            
            if session and session.get("payment_status") == "paid":
                print("✅ Payment confirmed!")
                
                # Update request status
                request.status = RequestStatus.PAID
                request.paid_at = datetime.utcnow()
                request.stripe_payment_intent_id = session.get("payment_intent")
                request.amount_charged = session.get("amount_total", 0) / 100
                
                # Log event
                event = RequestEvent(
                    request_id=request.id,
                    event_type="payment_processed",
                    event_data={
                        "amount": float(request.amount_charged),
                        "payment_method": "stripe_checkout",
                        "processed_manually": True
                    },
                    triggered_by="manual_script"
                )
                db.add(event)
                
                await db.commit()
                print(f"💰 Payment of ${request.amount_charged} recorded")
                
                # Submit to Phoenix PD
                print("\n📤 Submitting to Phoenix PD...")
                scraper = PhoenixPDScraper()
                
                try:
                    # Initialize scraper
                    print("   Initializing scraper...")
                    await scraper.initialize()
                    
                    # Submit request
                    print(f"   Submitting case {request.case_number}...")
                    submission_result = await scraper.submit_request(
                        case_number=request.case_number,
                        report_type=request.report_type.value,
                        requestor_name=f"{request.requestor_first_name} {request.requestor_last_name}",
                        requestor_email=request.requestor_email,
                        incident_date=request.incident_date
                    )
                    
                    if submission_result.get("success"):
                        request.status = RequestStatus.SUBMITTED
                        request.submitted_at = datetime.utcnow()
                        request.submission_confirmation = submission_result.get("confirmation_number")
                        
                        # Log submission
                        event = RequestEvent(
                            request_id=request.id,
                            event_type="submitted_to_pd",
                            event_data={
                                "confirmation_number": request.submission_confirmation,
                                "details": "Successfully submitted to Phoenix PD"
                            },
                            triggered_by="manual_script"
                        )
                        db.add(event)
                        
                        await db.commit()
                        print(f"✅ Submitted! Confirmation: {request.submission_confirmation}")
                        
                        # Send confirmation email would go here
                        print("\n📧 Email notification would be sent to customer")
                        
                    else:
                        print(f"❌ Submission failed: {submission_result.get('error')}")
                        
                except Exception as e:
                    print(f"❌ Error submitting: {str(e)}")
                    
                finally:
                    await scraper.cleanup()
                    
            else:
                print("❌ Payment not confirmed in Stripe")
                if session:
                    print(f"   Payment status: {session.get('payment_status')}")
        else:
            print("❌ No Stripe session ID found")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python process_payment_manually.py <request_id>")
        print("\nExample:")
        print("  python process_payment_manually.py d2d776bc-1953-4cdf-9bba-965ee91646d9")
        return
        
    request_id = sys.argv[1]
    await process_payment(request_id)

if __name__ == "__main__":
    asyncio.run(main())