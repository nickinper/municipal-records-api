#!/usr/bin/env python3
"""
Manual order processing script.
Run this periodically to check for paid orders and process them.
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
import stripe
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Load environment
load_dotenv()
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Import your models
from proprietary.database.models import Request, RequestStatus, Customer
from core.scrapers.phoenix_pd import PhoenixPDScraper

async def check_paid_orders():
    """Check Stripe for paid orders and update database."""
    
    # Database connection
    engine = create_async_engine(os.getenv('DATABASE_URL'))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get all pending payment requests
        result = await session.execute(
            select(Request).where(Request.status == RequestStatus.PENDING_PAYMENT)
        )
        pending_requests = result.scalars().all()
        
        print(f"\n📋 Found {len(pending_requests)} pending orders")
        
        for request in pending_requests:
            if not request.stripe_checkout_session_id:
                continue
                
            print(f"\n🔍 Checking order {request.request_id}...")
            
            try:
                # Check payment status in Stripe
                checkout_session = stripe.checkout.Session.retrieve(
                    request.stripe_checkout_session_id
                )
                
                if checkout_session.payment_status == 'paid':
                    print(f"✅ Payment confirmed for {request.request_id}")
                    
                    # Update request status
                    request.status = RequestStatus.PAID
                    request.paid_at = datetime.utcnow()
                    request.stripe_payment_intent_id = checkout_session.payment_intent
                    
                    # Update customer credits if using credit system
                    if request.customer:
                        request.customer.credits_used += 1
                        request.customer.total_spent += float(checkout_session.amount_total / 100)
                    
                    await session.commit()
                    print(f"📦 Order {request.request_id} ready for processing!")
                    
                    # Optionally trigger scraper here
                    # await process_request(request)
                    
                else:
                    print(f"⏳ Payment still pending for {request.request_id}")
                    
            except stripe.error.StripeError as e:
                print(f"❌ Stripe error for {request.request_id}: {e}")
            except Exception as e:
                print(f"❌ Error processing {request.request_id}: {e}")

async def process_request(request: Request):
    """Process a paid request by running the scraper."""
    print(f"\n🤖 Processing request {request.request_id}...")
    
    try:
        scraper = PhoenixPDScraper(
            screenshot_dir=f"evidence/{request.request_id}"
        )
        
        # Run the scraper
        success, confirmation = await scraper.submit_request(
            case_number=request.case_number,
            requestor_first_name=request.requestor_first_name,
            requestor_last_name=request.requestor_last_name,
            requestor_email=request.requestor_email,
            report_type=request.report_type.value.lower()
        )
        
        if success:
            print(f"✅ Successfully submitted to police department!")
            print(f"📋 Confirmation: {confirmation}")
            # Update request with confirmation
            # Send email to customer
        else:
            print(f"❌ Failed to submit to police department")
            
    except Exception as e:
        print(f"❌ Error running scraper: {e}")

async def main():
    """Main function."""
    print("🚀 Municipal Records - Manual Order Processor")
    print("=" * 50)
    
    while True:
        print("\n1. Check for paid orders")
        print("2. Process specific order")
        print("3. View all pending orders")
        print("4. Exit")
        
        choice = input("\nChoice (1-4): ").strip()
        
        if choice == "1":
            await check_paid_orders()
        elif choice == "2":
            request_id = input("Enter request ID: ").strip()
            # Implementation for processing specific order
            print(f"Processing {request_id}...")
        elif choice == "3":
            # Show pending orders
            print("Showing pending orders...")
        elif choice == "4":
            print("Goodbye! 👋")
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    asyncio.run(main())