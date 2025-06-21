#!/usr/bin/env python3
"""
Stripe Setup Script for Municipal Records Processing.

This script helps configure Stripe keys and webhook endpoints.
"""

import os
import sys
import subprocess
import json
import re
from pathlib import Path
import requests
from typing import Optional, Dict
import getpass


class StripeSetup:
    """Handle Stripe configuration setup."""
    
    def __init__(self):
        self.env_path = Path(__file__).parent.parent / ".env"
        self.stripe_cli_available = self.check_stripe_cli()
        
    def check_stripe_cli(self) -> bool:
        """Check if Stripe CLI is installed."""
        try:
            subprocess.run(["stripe", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def install_stripe_cli(self):
        """Provide instructions to install Stripe CLI."""
        print("\n🔧 Stripe CLI not found. To install:")
        print("\nMacOS:")
        print("  brew install stripe/stripe-cli/stripe")
        print("\nLinux:")
        print("  # Download from https://github.com/stripe/stripe-cli/releases")
        print("  curl -L https://github.com/stripe/stripe-cli/releases/download/v1.19.1/stripe_1.19.1_linux_x86_64.tar.gz | tar xz")
        print("\nWindows:")
        print("  # Download from https://github.com/stripe/stripe-cli/releases")
        print("\nOr use scoop: scoop install stripe")
        
    def validate_stripe_key(self, key: str, key_type: str) -> bool:
        """Validate Stripe key format."""
        patterns = {
            "secret": r"^(sk|rk)_(test|live)_[a-zA-Z0-9]{24,}$",  # Added rk_ for restricted keys
            "publishable": r"^pk_(test|live)_[a-zA-Z0-9]{24,}$",
            "webhook": r"^whsec_[a-zA-Z0-9]{24,}$"
        }
        
        pattern = patterns.get(key_type)
        if not pattern:
            return False
            
        return bool(re.match(pattern, key))
    
    def read_env_file(self) -> Dict[str, str]:
        """Read current .env file."""
        env_vars = {}
        if self.env_path.exists():
            with open(self.env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        return env_vars
    
    def write_env_file(self, env_vars: Dict[str, str]):
        """Write updated .env file."""
        # Read the current file to preserve structure and comments
        lines = []
        if self.env_path.exists():
            with open(self.env_path, 'r') as f:
                lines = f.readlines()
        
        # Update the values
        with open(self.env_path, 'w') as f:
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and '=' in stripped:
                    key = stripped.split('=', 1)[0].strip()
                    if key in env_vars:
                        f.write(f"{key}={env_vars[key]}\n")
                    else:
                        f.write(line)
                else:
                    f.write(line)
    
    def setup_webhook_with_cli(self) -> Optional[str]:
        """Set up webhook using Stripe CLI for local testing."""
        print("\n🔄 Setting up local webhook forwarding with Stripe CLI...")
        
        try:
            # Check if logged in
            result = subprocess.run(
                ["stripe", "config", "--list"], 
                capture_output=True, 
                text=True
            )
            
            if "No configured accounts found" in result.stdout:
                print("📝 Please log in to Stripe CLI:")
                subprocess.run(["stripe", "login"])
            
            print("\n🚀 Starting webhook forwarding...")
            print("Keep this running in a separate terminal:")
            print("\n  stripe listen --forward-to localhost:8000/webhooks/stripe\n")
            
            # Get the webhook secret from user
            print("Run the command above and paste the webhook signing secret here:")
            webhook_secret = input("Webhook secret (whsec_...): ").strip()
            
            if self.validate_stripe_key(webhook_secret, "webhook"):
                return webhook_secret
            else:
                print("❌ Invalid webhook secret format")
                return None
                
        except Exception as e:
            print(f"❌ Error setting up webhook: {e}")
            return None
    
    def get_production_webhook_instructions(self):
        """Provide instructions for production webhook setup."""
        print("\n📋 To set up production webhook:")
        print("\n1. Go to https://dashboard.stripe.com/webhooks")
        print("2. Click 'Add endpoint'")
        print("3. Enter your webhook URL:")
        print("   https://yourdomain.com/webhooks/stripe")
        print("\n4. Select these events:")
        print("   ✓ payment_intent.succeeded")
        print("   ✓ payment_intent.payment_failed")
        print("   ✓ checkout.session.completed")
        print("   ✓ customer.created")
        print("   ✓ customer.updated")
        print("\n5. Click 'Add endpoint'")
        print("6. Copy the 'Signing secret' (click Reveal)")
        
    def run(self):
        """Run the setup process."""
        print("🚀 Municipal Records Processing - Stripe Setup")
        print("=" * 50)
        
        # Check for existing configuration
        env_vars = self.read_env_file()
        
        # Check if already configured
        if env_vars.get("STRIPE_SECRET_KEY", "").startswith("sk_live_"):
            print("\n✅ Stripe appears to be already configured with live keys.")
            update = input("Do you want to update the configuration? (y/n): ").lower()
            if update != 'y':
                print("Setup cancelled.")
                return
        
        print("\n🔑 Let's configure your Stripe keys...")
        print("\nYou can find these at: https://dashboard.stripe.com/apikeys")
        
        # Get keys from user
        while True:
            secret_key = getpass.getpass("\nStripe Secret Key (sk_live_... or rk_live_... for restricted): ").strip()
            if self.validate_stripe_key(secret_key, "secret"):
                break
            print("❌ Invalid secret key format. Should start with sk_live_, sk_test_, rk_live_, or rk_test_")
        
        while True:
            publishable_key = input("Stripe Publishable Key (pk_live_...): ").strip()
            if self.validate_stripe_key(publishable_key, "publishable"):
                break
            print("❌ Invalid publishable key format. Should start with pk_live_ or pk_test_")
        
        # Determine if test or live mode
        is_test_mode = secret_key.startswith("sk_test_") or secret_key.startswith("rk_test_")
        is_restricted = secret_key.startswith("rk_")
        mode = "TEST" if is_test_mode else "LIVE"
        key_type = "RESTRICTED" if is_restricted else "STANDARD"
        print(f"\n🔍 Detected {mode} mode with {key_type} key")
        
        # Webhook setup
        print("\n🔗 Webhook Configuration")
        print("Choose webhook setup method:")
        print("1. Local testing with Stripe CLI (recommended for development)")
        print("2. Production webhook (requires public URL)")
        print("3. Skip for now")
        
        choice = input("\nChoice (1-3): ").strip()
        
        webhook_secret = None
        if choice == "1":
            if self.stripe_cli_available:
                webhook_secret = self.setup_webhook_with_cli()
            else:
                self.install_stripe_cli()
                print("\nInstall Stripe CLI and run setup again for local webhook testing.")
        elif choice == "2":
            self.get_production_webhook_instructions()
            webhook_secret = input("\nPaste your webhook signing secret (whsec_...): ").strip()
            if not self.validate_stripe_key(webhook_secret, "webhook"):
                print("❌ Invalid webhook secret format")
                webhook_secret = None
        
        # Update environment variables
        env_vars["STRIPE_SECRET_KEY"] = secret_key
        env_vars["STRIPE_PUBLISHABLE_KEY"] = publishable_key
        if webhook_secret:
            env_vars["STRIPE_WEBHOOK_SECRET"] = webhook_secret
        
        # Write updated .env file
        self.write_env_file(env_vars)
        
        print("\n✅ Stripe configuration updated successfully!")
        
        # Test the configuration
        print("\n🧪 Testing configuration...")
        test_import = f"""
import os
import stripe
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

try:
    # Test API key by fetching account info
    account = stripe.Account.retrieve()
    print(f"✅ Connected to Stripe account: {{account.get('email', 'Unknown')}}")
    print(f"   Mode: {mode}")
except stripe.error.AuthenticationError:
    print("❌ Invalid API key")
except Exception as e:
    print(f"❌ Error: {{e}}")
"""
        
        # Save and run test
        test_file = Path(__file__).parent / "test_stripe_config.py"
        with open(test_file, 'w') as f:
            f.write(test_import)
        
        try:
            result = subprocess.run(
                [sys.executable, str(test_file)], 
                capture_output=True, 
                text=True
            )
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        finally:
            # Clean up test file
            test_file.unlink(missing_ok=True)
        
        print("\n📝 Next steps:")
        print("1. Restart your server to load the new configuration")
        print("2. Test a payment flow")
        if not webhook_secret:
            print("3. Set up webhook endpoint for automated processing")
        
        if is_test_mode:
            print("\n⚠️  WARNING: You're using TEST keys. Switch to LIVE keys for production.")
        else:
            print("\n🎉 You're using LIVE keys. Ready for production!")
        
        print("\n💡 Tip: For local webhook testing, run in another terminal:")
        print("  stripe listen --forward-to localhost:8000/webhooks/stripe")


if __name__ == "__main__":
    setup = StripeSetup()
    try:
        setup.run()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)