#!/usr/bin/env python3
"""Update webhook secret in .env file"""

import re

# Get the webhook secret from user
secret = input("Paste your webhook secret (whsec_...): ").strip()

if not secret.startswith("whsec_"):
    print("❌ Invalid webhook secret format")
    exit(1)

# Read current .env
with open('.env', 'r') as f:
    lines = f.readlines()

# Update the webhook secret
updated = False
new_lines = []
for line in lines:
    if line.startswith('STRIPE_WEBHOOK_SECRET='):
        new_lines.append(f'STRIPE_WEBHOOK_SECRET={secret}\n')
        updated = True
    else:
        new_lines.append(line)

# Write back
with open('.env', 'w') as f:
    f.writelines(new_lines)

print("✅ Webhook secret updated in .env!")
print("🔄 Restart your API server to use the new webhook secret")
print("\nRun: make restart")