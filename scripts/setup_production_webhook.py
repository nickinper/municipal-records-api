#!/usr/bin/env python3
"""
Set up production webhook for Municipal Records Processing.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import stripe

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    # Initialize Stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    if not stripe.api_key:
        print("❌ No Stripe API key found in .env")
        return
    
    # Determine if we're in live mode
    is_live = not stripe.api_key.startswith("sk_test_")
    mode = "LIVE" if is_live else "TEST"
    
    print(f"🚀 Setting up {mode} mode webhook")
    print()
    
    # Get production URL
    prod_url = input("Enter your production API URL (e.g., https://api.municipalrecordsprocessing.com): ").strip()
    if not prod_url:
        print("❌ Production URL is required")
        return
    
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
    
    print(f"\n📍 Webhook URL: {webhook_url}")
    
    # Events to listen for
    events = [
        "checkout.session.completed",
        "payment_intent.succeeded",
        "payment_intent.payment_failed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted"
    ]
    
    print(f"\n📋 Events to monitor:")
    for event in events:
        print(f"   • {event}")
    
    confirm = input("\n✅ Create this webhook? (y/n): ").lower()
    if confirm != 'y':
        print("❌ Cancelled")
        return
    
    try:
        # Create the webhook
        endpoint = stripe.WebhookEndpoint.create(
            url=webhook_url,
            enabled_events=events,
            description="Municipal Records Processing - Production Webhook"
        )
        
        print(f"\n✅ Webhook created successfully!")
        print(f"   ID: {endpoint.id}")
        print(f"   Status: {endpoint.status}")
        print(f"\n🔐 Webhook signing secret: {endpoint.secret}")
        print("\n⚠️  IMPORTANT: Save this secret in your production environment as STRIPE_WEBHOOK_SECRET")
        print("   You won't be able to see this secret again!")
        
        # Update .env.production file
        env_file = Path(".env.production")
        update_env = input("\n📝 Create/update .env.production file? (y/n): ").lower()
        
        if update_env == 'y':
            env_content = f"""# Production environment variables
STRIPE_WEBHOOK_SECRET={endpoint.secret}
WEBHOOK_ENDPOINT_ID={endpoint.id}
PRODUCTION_API_URL={prod_url}
"""
            
            if env_file.exists():
                # Read existing content
                existing = env_file.read_text()
                
                # Update or append
                lines = existing.split('\n')
                updated_lines = []
                keys_updated = set()
                
                for line in lines:
                    if '=' in line and not line.strip().startswith('#'):
                        key = line.split('=')[0].strip()
                        if key in ['STRIPE_WEBHOOK_SECRET', 'WEBHOOK_ENDPOINT_ID', 'PRODUCTION_API_URL']:
                            if key == 'STRIPE_WEBHOOK_SECRET':
                                updated_lines.append(f"STRIPE_WEBHOOK_SECRET={endpoint.secret}")
                            elif key == 'WEBHOOK_ENDPOINT_ID':
                                updated_lines.append(f"WEBHOOK_ENDPOINT_ID={endpoint.id}")
                            elif key == 'PRODUCTION_API_URL':
                                updated_lines.append(f"PRODUCTION_API_URL={prod_url}")
                            keys_updated.add(key)
                        else:
                            updated_lines.append(line)
                    else:
                        updated_lines.append(line)
                
                # Add new keys if not updated
                if 'STRIPE_WEBHOOK_SECRET' not in keys_updated:
                    updated_lines.append(f"STRIPE_WEBHOOK_SECRET={endpoint.secret}")
                if 'WEBHOOK_ENDPOINT_ID' not in keys_updated:
                    updated_lines.append(f"WEBHOOK_ENDPOINT_ID={endpoint.id}")
                if 'PRODUCTION_API_URL' not in keys_updated:
                    updated_lines.append(f"PRODUCTION_API_URL={prod_url}")
                
                env_file.write_text('\n'.join(updated_lines))
            else:
                env_file.write_text(env_content)
            
            print(f"✅ Created {env_file}")
            print("\n📋 Next steps:")
            print("   1. Deploy your API to production")
            print("   2. Set STRIPE_WEBHOOK_SECRET environment variable")
            print("   3. Test with: stripe trigger checkout.session.completed")
        
    except stripe.error.StripeError as e:
        print(f"\n❌ Error creating webhook: {str(e)}")
        
        # Check if we need different permissions
        if "permission" in str(e).lower():
            print("\n💡 This might be due to restricted API key permissions.")
            print("   You may need to:")
            print("   1. Use your main secret key (not restricted)")
            print("   2. Or add 'Webhook Endpoints' write permission to your restricted key")
    
    # List existing webhooks
    print("\n📋 Checking existing webhooks...")
    try:
        webhooks = stripe.WebhookEndpoint.list(limit=10)
        if webhooks.data:
            print(f"\nFound {len(webhooks.data)} webhook(s):")
            for wh in webhooks.data:
                print(f"\n   • {wh.url}")
                print(f"     ID: {wh.id}")
                print(f"     Status: {wh.status}")
                print(f"     Events: {', '.join(wh.enabled_events[:3])}...")
        else:
            print("   No webhooks found")
    except Exception as e:
        print(f"   Could not list webhooks: {str(e)}")

if __name__ == "__main__":
    main()