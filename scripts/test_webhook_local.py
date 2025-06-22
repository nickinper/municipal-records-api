#!/usr/bin/env python3
"""
Simple webhook tester for local development.
This simulates what Stripe would send to your webhook endpoint.
"""

import requests
import json
import time
import hashlib
import hmac
from datetime import datetime

# Configuration
WEBHOOK_URL = "http://localhost:8000/webhooks/stripe"
WEBHOOK_SECRET = "whsec_test_secret"  # You'll need to update this

def generate_stripe_signature(payload: str, secret: str, timestamp: int) -> str:
    """Generate a Stripe webhook signature."""
    signed_payload = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"

def send_test_webhook(event_type: str, data: dict):
    """Send a test webhook to your local endpoint."""
    timestamp = int(time.time())
    
    event = {
        "id": f"evt_test_{int(time.time())}",
        "object": "event",
        "api_version": "2023-10-16",
        "created": timestamp,
        "data": {
            "object": data
        },
        "livemode": True,
        "pending_webhooks": 1,
        "request": {
            "id": None,
            "idempotency_key": None
        },
        "type": event_type
    }
    
    payload = json.dumps(event)
    signature = generate_stripe_signature(payload, WEBHOOK_SECRET, timestamp)
    
    headers = {
        "Content-Type": "application/json",
        "Stripe-Signature": signature
    }
    
    print(f"\n📤 Sending {event_type} webhook...")
    
    try:
        response = requests.post(WEBHOOK_URL, data=payload, headers=headers)
        print(f"📥 Response: {response.status_code}")
        if response.text:
            print(f"📄 Body: {response.text}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to webhook endpoint. Is your server running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_payment_success():
    """Test a successful payment webhook."""
    checkout_session = {
        "id": "cs_test_a1b2c3d4",
        "object": "checkout.session",
        "payment_status": "paid",
        "metadata": {
            "request_id": "test-request-123"
        },
        "customer_details": {
            "email": "test@example.com"
        },
        "amount_total": 4900,  # $49.00
        "currency": "usd"
    }
    
    return send_test_webhook("checkout.session.completed", checkout_session)

def main():
    print("🧪 Municipal Records Webhook Tester")
    print("=" * 40)
    
    print("\n⚠️  Note: This is for testing only!")
    print("For production, use Stripe CLI or real webhooks.")
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/api/v1/health")
        if response.status_code != 200:
            print("\n❌ API server not responding. Start it with: make start")
            return
    except:
        print("\n❌ API server not running. Start it with: make start")
        return
    
    print("\n✅ API server is running")
    
    # Get webhook secret from user
    print("\n🔑 Enter your webhook secret from .env")
    print("(or press Enter to use test secret)")
    secret = input("Webhook secret: ").strip()
    
    if secret and secret.startswith("whsec_"):
        global WEBHOOK_SECRET
        WEBHOOK_SECRET = secret
    
    # Test webhook
    print("\n🚀 Sending test payment webhook...")
    if test_payment_success():
        print("\n✅ Webhook test successful!")
        print("Check your server logs to see the processing.")
    else:
        print("\n❌ Webhook test failed.")
        print("Check your server logs for errors.")

if __name__ == "__main__":
    main()