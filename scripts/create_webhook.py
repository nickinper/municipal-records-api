#!/usr/bin/env python3
"""
Create production webhook for Municipal Records Processing.

Usage:
    python create_webhook.py <production_url>
    
Example:
    python create_webhook.py https://api.municipalrecordsprocessing.com
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import stripe

# Load environment variables
load_dotenv()

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    prod_url = sys.argv[1]
    
    # Initialize Stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    if not stripe.api_key:
        print("❌ No Stripe API key found in .env")
        return
    
    # Determine if we're in live mode
    is_live = not stripe.api_key.startswith("sk_test_")
    mode = "LIVE" if is_live else "TEST"
    
    print(f"🚀 Creating {mode} mode webhook")
    
    # Ensure it's HTTPS
    if not prod_url.startswith("https://"):
        print("⚠️  Production webhook must use HTTPS")
        if prod_url.startswith("http://"):
            prod_url = prod_url.replace("http://", "https://")
            print(f"   Updated to: {prod_url}")
    
    # Build webhook URL
    webhook_url = f"{prod_url}/webhooks/stripe"
    if webhook_url.endswith("//webhooks/stripe"):
        webhook_url = webhook_url.replace("//webhooks/stripe", "/webhooks/stripe")
    
    print(f"📍 Webhook URL: {webhook_url}")
    
    # Events to listen for
    events = [
        "checkout.session.completed",
        "payment_intent.succeeded",
        "payment_intent.payment_failed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted"
    ]
    
    print(f"📋 Events: {', '.join(events[:3])}...")
    
    try:
        # Create the webhook
        endpoint = stripe.WebhookEndpoint.create(
            url=webhook_url,
            enabled_events=events,
            description="Municipal Records Processing - Production"
        )
        
        print(f"\n✅ Webhook created successfully!")
        print(f"   ID: {endpoint.id}")
        print(f"   Status: {endpoint.status}")
        print(f"\n🔐 WEBHOOK SECRET: {endpoint.secret}")
        print("\n⚠️  SAVE THIS SECRET! Add to your production environment:")
        print(f"   STRIPE_WEBHOOK_SECRET={endpoint.secret}")
        
        # Save to file
        with open(".env.production", "w") as f:
            f.write(f"# Production webhook configuration\n")
            f.write(f"STRIPE_WEBHOOK_SECRET={endpoint.secret}\n")
            f.write(f"WEBHOOK_ENDPOINT_ID={endpoint.id}\n")
            f.write(f"PRODUCTION_API_URL={prod_url}\n")
        
        print(f"\n📄 Saved to .env.production")
        
    except stripe.error.StripeError as e:
        print(f"\n❌ Error: {str(e)}")
        
        if "permission" in str(e).lower() or "restricted" in str(e).lower():
            print("\n💡 Your API key doesn't have permission to create webhooks.")
            print("   Options:")
            print("   1. Go to: https://dashboard.stripe.com/webhooks")
            print("   2. Click 'Add endpoint'")
            print(f"   3. Enter URL: {webhook_url}")
            print("   4. Select events: checkout.session.completed, payment_intent.succeeded")
            print("   5. Save and copy the signing secret")

if __name__ == "__main__":
    main()