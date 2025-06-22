#!/usr/bin/env python3
"""
Webhook Setup Script for Municipal Records Processing.

This script helps configure Stripe webhooks for automated order processing.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
import requests
from typing import Optional, Dict
import stripe
from dotenv import load_dotenv


class WebhookSetup:
    """Handle webhook configuration setup."""
    
    def __init__(self):
        self.env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(self.env_path)
        
        # Initialize Stripe
        self.stripe_key = os.getenv('STRIPE_SECRET_KEY')
        if not self.stripe_key:
            print("❌ No Stripe secret key found in .env")
            sys.exit(1)
            
        stripe.api_key = self.stripe_key
        self.is_live = self.stripe_key.startswith(('sk_live', 'rk_live'))
        
    def check_stripe_cli(self) -> bool:
        """Check if Stripe CLI is installed."""
        try:
            subprocess.run(["stripe", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def setup_local_webhook(self):
        """Set up local webhook forwarding with Stripe CLI."""
        print("\n🔧 Setting up local webhook forwarding...")
        print("\nPlease run this command in a SEPARATE terminal window:")
        print("\n  stripe listen --forward-to localhost:8000/webhooks/stripe\n")
        print("Keep that terminal open while testing!")
        
        webhook_secret = input("\nPaste the webhook signing secret (whsec_...): ").strip()
        
        if webhook_secret.startswith("whsec_"):
            self.update_env_file({"STRIPE_WEBHOOK_SECRET": webhook_secret})
            print("✅ Local webhook configured!")
            return True
        else:
            print("❌ Invalid webhook secret format")
            return False
    
    def create_production_webhook(self):
        """Create a production webhook endpoint."""
        print("\n🌐 Creating production webhook...")
        
        webhook_url = input("Enter your public webhook URL (e.g., https://api.yourdomain.com/webhooks/stripe): ").strip()
        
        if not webhook_url.startswith("https://"):
            print("❌ Webhook URL must use HTTPS for security")
            return False
        
        try:
            # Create webhook endpoint
            endpoint = stripe.WebhookEndpoint.create(
                url=webhook_url,
                enabled_events=[
                    "payment_intent.succeeded",
                    "payment_intent.payment_failed",
                    "checkout.session.completed",
                    "customer.created",
                    "customer.updated",
                    "customer.subscription.created",
                    "customer.subscription.updated",
                    "customer.subscription.deleted"
                ]
            )
            
            print(f"\n✅ Webhook created successfully!")
            print(f"   ID: {endpoint.id}")
            print(f"   URL: {endpoint.url}")
            print(f"\n🔑 Your webhook secret: {endpoint.secret}")
            
            # Update .env file
            self.update_env_file({"STRIPE_WEBHOOK_SECRET": endpoint.secret})
            
            return True
            
        except stripe.error.StripeError as e:
            print(f"❌ Error creating webhook: {e}")
            return False
    
    def list_existing_webhooks(self):
        """List existing webhook endpoints."""
        try:
            endpoints = stripe.WebhookEndpoint.list(limit=10)
            
            if not endpoints.data:
                print("\n📋 No webhooks configured yet.")
                return
            
            print(f"\n📋 Existing webhooks ({len(endpoints.data)}):")
            for endpoint in endpoints.data:
                status = "✅" if endpoint.status == "enabled" else "❌"
                print(f"\n{status} {endpoint.url}")
                print(f"   ID: {endpoint.id}")
                print(f"   Events: {', '.join(endpoint.enabled_events[:3])}...")
                
        except stripe.error.StripeError as e:
            print(f"❌ Error listing webhooks: {e}")
    
    def test_webhook(self):
        """Test webhook configuration."""
        print("\n🧪 Testing webhook configuration...")
        
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        if not webhook_secret:
            print("❌ No webhook secret found in .env")
            return
        
        print("✅ Webhook secret is configured")
        
        # Test creating a checkout session
        print("\n🔄 Creating test checkout session...")
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'TEST - Police Report Request',
                        },
                        'unit_amount': 100,  # $1.00 test
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url='http://localhost:8000/success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='http://localhost:8000/cancel',
            )
            
            print(f"✅ Test session created: {session.id}")
            print(f"\n🔗 Test payment URL:\n{session.url}")
            print("\n💡 Complete this test payment to verify webhook processing")
            
        except stripe.error.StripeError as e:
            print(f"❌ Error creating test session: {e}")
    
    def update_env_file(self, updates: Dict[str, str]):
        """Update .env file with new values."""
        # Read current file
        lines = []
        if self.env_path.exists():
            with open(self.env_path, 'r') as f:
                lines = f.readlines()
        
        # Update or add values
        updated = set()
        new_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in stripped:
                key = stripped.split('=', 1)[0].strip()
                if key in updates:
                    new_lines.append(f"{key}={updates[key]}\n")
                    updated.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        # Add any missing keys
        for key, value in updates.items():
            if key not in updated:
                new_lines.append(f"{key}={value}\n")
        
        # Write back
        with open(self.env_path, 'w') as f:
            f.writelines(new_lines)
    
    def run(self):
        """Run the webhook setup process."""
        print("🚀 Municipal Records Processing - Webhook Setup")
        print("=" * 50)
        
        mode = "LIVE" if self.is_live else "TEST"
        print(f"\n🔍 Detected {mode} mode")
        
        # Show menu
        while True:
            print("\n📋 Webhook Setup Options:")
            print("1. Set up local testing webhook (Stripe CLI)")
            print("2. Create production webhook")
            print("3. List existing webhooks")
            print("4. Test webhook configuration")
            print("5. Exit")
            
            choice = input("\nChoice (1-5): ").strip()
            
            if choice == "1":
                if self.check_stripe_cli():
                    self.setup_local_webhook()
                else:
                    print("\n❌ Stripe CLI not found!")
                    print("Install from: https://stripe.com/docs/stripe-cli")
                    
            elif choice == "2":
                self.create_production_webhook()
                
            elif choice == "3":
                self.list_existing_webhooks()
                
            elif choice == "4":
                self.test_webhook()
                
            elif choice == "5":
                print("\nGoodbye! 👋")
                break
                
            else:
                print("❌ Invalid choice")
        
        print("\n✅ Webhook setup complete!")
        print("\n📝 Next steps:")
        print("1. Restart your API server to load the webhook secret")
        print("2. Test a payment to verify webhook processing")
        print("3. Check logs for webhook events")


if __name__ == "__main__":
    setup = WebhookSetup()
    try:
        setup.run()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)