#!/usr/bin/env python3
"""
Test the full payment flow end-to-end.

This creates a test request and generates a payment link.
"""

import asyncio
import httpx
import json
from datetime import datetime


async def test_payment_flow():
    """Test the complete payment flow."""
    print("💰 Testing Municipal Records Payment Flow")
    print("=" * 50)
    
    # API endpoint
    base_url = "http://localhost:8000"
    
    # Test data
    test_request = {
        "case_number": f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "requestor_email": "test@municipalrecords.com",
        "requestor_first_name": "Test",
        "requestor_last_name": "Customer"
    }
    
    print(f"\n📋 Test Request:")
    print(f"  Case Number: {test_request['case_number']}")
    print(f"  Email: {test_request['requestor_email']}")
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. Submit request
            print("\n1️⃣ Submitting request...")
            response = await client.post(
                f"{base_url}/api/v1/submit-request",
                json=test_request
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Request submitted successfully!")
                print(f"\n📝 Response:")
                print(f"  Request ID: {result['request_id']}")
                print(f"  Status: {result['status']}")
                print(f"  Amount: ${result['amount']}")
                print(f"\n💳 Payment Link:")
                print(f"  {result['payment_link']}")
                
                print("\n🎯 Next Steps:")
                print("1. Click the payment link above")
                print("2. Use Stripe test card: 4242 4242 4242 4242")
                print("3. Any future expiry, any CVC")
                print("4. Complete payment")
                print("\n5. The webhook will automatically process your request!")
                
                # Save request ID for status checking
                request_id = result['request_id']
                
                print(f"\n📊 To check status later:")
                print(f"curl -X GET {base_url}/api/v1/status/{request_id} \\")
                print('  -H "X-API-Key: your-api-key"')
                
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                
        except httpx.ConnectError:
            print("❌ Could not connect to API")
            print("   Make sure the server is running: python main.py")
            
        except Exception as e:
            print(f"❌ Error: {e}")


async def check_stripe_config():
    """Check if Stripe is properly configured."""
    print("\n🔧 Checking Stripe Configuration...")
    
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    if not stripe_key:
        print("❌ STRIPE_SECRET_KEY not set in .env")
        print("   Get your key from: https://dashboard.stripe.com/test/apikeys")
    else:
        print("✅ Stripe secret key configured")
        
    if not webhook_secret:
        print("⚠️  STRIPE_WEBHOOK_SECRET not set")
        print("   This is needed for webhook verification")
    else:
        print("✅ Webhook secret configured")
        
    print("\n💡 Stripe Test Cards:")
    print("  Success: 4242 4242 4242 4242")
    print("  Decline: 4000 0000 0000 0002")
    print("  3D Secure: 4000 0025 0000 3155")


if __name__ == "__main__":
    print("""
    🚀 MUNICIPAL RECORDS PAYMENT TEST
    
    This will:
    1. Submit a test request
    2. Generate a Stripe payment link
    3. Show you how to complete payment
    
    Make sure the API is running: python main.py
    """)
    
    # Check Stripe config first
    asyncio.run(check_stripe_config())
    
    # Test payment flow
    asyncio.run(test_payment_flow())