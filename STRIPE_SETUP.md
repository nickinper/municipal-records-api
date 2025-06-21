# Stripe Configuration Guide

## Finding Your Stripe Keys

### 1. Secret and Publishable Keys
1. Log in to your Stripe Dashboard: https://dashboard.stripe.com
2. Navigate to **Developers** → **API keys**
3. You'll see:
   - **Publishable key**: `pk_live_...` (safe to expose in frontend)
   - **Secret key**: `sk_live_...` (keep this secure, never commit to git!)

### 2. Webhook Endpoint Secret

The webhook secret is created when you set up your webhook endpoint:

1. In Stripe Dashboard, go to **Developers** → **Webhooks**
2. Click **"Add endpoint"**
3. Enter your webhook URL:
   - For local testing: Use ngrok or similar tunnel service
   - For production: `https://yourdomain.com/webhooks/stripe`
4. Select events to listen for:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `checkout.session.completed`
   - `customer.created`
   - `customer.updated`
5. Click **"Add endpoint"**
6. After creation, click on your webhook endpoint
7. Click **"Reveal"** under "Signing secret"
8. Copy the secret: `whsec_...`

### 3. Local Testing with Stripe CLI

For local development, you can use Stripe CLI:

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login to Stripe
stripe login

# Forward webhooks to your local server
stripe listen --forward-to localhost:8000/webhooks/stripe

# The CLI will display your webhook secret:
# Ready! Your webhook signing secret is whsec_test_...
```

### 4. Update Your .env File

Replace the placeholder values in `.env`:

```bash
STRIPE_SECRET_KEY=sk_live_51ABC...xyz
STRIPE_PUBLISHABLE_KEY=pk_live_51ABC...xyz
STRIPE_WEBHOOK_SECRET=whsec_1234567890abcdef
```

### 5. Important Security Notes

- **NEVER** commit real API keys to Git
- Add `.env` to `.gitignore` (already done)
- Use environment variables in production
- Rotate keys regularly
- Use restricted keys when possible

### 6. Testing Your Configuration

After updating keys, test with:

```bash
# Restart the server
# Then test a submission
curl -X POST http://localhost:8000/api/v1/submit-request \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "incident",
    "case_number": "TEST-001",
    "requestor_email": "test@yourdomain.com",
    "requestor_first_name": "Test",
    "requestor_last_name": "User"
  }'
```

The response should include a real Stripe payment URL if configured correctly.