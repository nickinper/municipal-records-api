#!/usr/bin/env python3
"""Test and clean Stripe API key."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def clean_api_key(key):
    """Remove any whitespace and newlines from API key."""
    if not key:
        return None
    # Remove all whitespace characters including newlines, tabs, spaces
    cleaned = key.strip().replace('\n', '').replace('\r', '').replace(' ', '').replace('\t', '')
    return cleaned

# Get the key from environment
raw_key = os.getenv("STRIPE_SECRET_KEY")

if not raw_key:
    print("❌ No STRIPE_SECRET_KEY found in environment")
    sys.exit(1)

# Show the raw key details
print(f"Raw key length: {len(raw_key)}")
print(f"Raw key starts with: {raw_key[:20]}...")
print(f"Raw key ends with: ...{raw_key[-20:]}")
print(f"Contains newline: {repr(raw_key[-5:])}")

# Clean the key
cleaned_key = clean_api_key(raw_key)

print("\n" + "="*50 + "\n")
print(f"Cleaned key length: {len(cleaned_key)}")
print(f"Cleaned key: {cleaned_key}")
print("\n" + "="*50 + "\n")

# Test the key with Stripe
try:
    import stripe
    stripe.api_key = cleaned_key
    
    # Make a simple API call to test
    print("Testing Stripe API connection...")
    account = stripe.Account.retrieve()
    print(f"✅ Stripe connection successful! Account: {account.id}")
    
except Exception as e:
    print(f"❌ Stripe error: {e}")
    
print("\n📋 Copy this cleaned key to Render:")
print(cleaned_key)