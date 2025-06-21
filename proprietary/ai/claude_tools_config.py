"""
Claude AI tool configurations for pricing automation.

Defines the tools available to Claude for managing customer pricing.
"""

STRIPE_PRICING_TOOLS = [
    {
        "name": "update_volume_pricing",
        "description": "Apply automatic volume discounts based on customer usage. Updates the customer's pricing tier in Stripe.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Stripe customer ID (starts with cus_)"
                },
                "usage_count": {
                    "type": "integer",
                    "description": "Total number of requests/reports this month"
                }
            },
            "required": ["customer_id", "usage_count"]
        }
    },
    {
        "name": "create_prepaid_package",
        "description": "Create a prepaid credit package with bulk discount. Returns a payment link.",
        "input_schema": {
            "type": "object",
            "properties": {
                "package_type": {
                    "type": "string",
                    "enum": ["starter", "professional", "enterprise"],
                    "description": "Type of prepaid package: starter (12 credits/$500), professional (60 credits/$2000), enterprise (200 credits/$5000)"
                },
                "customer_email": {
                    "type": "string",
                    "description": "Optional customer email to pre-fill in checkout"
                }
            },
            "required": ["package_type"]
        }
    },
    {
        "name": "calculate_savings",
        "description": "Calculate how much a customer could save with volume discounts or prepaid packages",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Stripe customer ID"
                },
                "monthly_usage": {
                    "type": "integer",
                    "description": "Average or expected monthly usage"
                }
            },
            "required": ["customer_id", "monthly_usage"]
        }
    },
    {
        "name": "apply_retroactive_credit",
        "description": "Apply retroactive discount credit when customer reaches a new volume tier",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Stripe customer ID"
                },
                "order_count": {
                    "type": "integer",
                    "description": "Current number of orders this billing period"
                }
            },
            "required": ["customer_id", "order_count"]
        }
    }
]

# System prompts for different contexts
PRICING_AGENT_SYSTEM_PROMPT = """
You are a helpful pricing specialist for Municipal Records Processing LLC.

Our automated pricing model:
- Base price: $49/request
- 11-50 requests: $39.20/request (20% off automatically)
- 51-100 requests: $29.40/request (40% off automatically)
- 100+ requests: $19.60/request (60% off automatically)

Prepaid credit packages (credits never expire):
- Starter: 12 credits for $500 (save $88)
- Professional: 60 credits for $2,000 (save $940)
- Enterprise: 200 credits for $5,000 (save $4,800)

Key points to emphasize:
1. Discounts apply automatically - no action needed
2. No contracts or monthly fees
3. Credits never expire
4. Retroactive credits when reaching new tiers
5. Phoenix PD fees ($5) are separate and passed through at cost

Always be helpful, friendly, and focus on value/savings. When customers ask about pricing, check their current usage and suggest the most cost-effective option.
"""

SALES_AGENT_SYSTEM_PROMPT = """
You are a sales specialist for Municipal Records Processing LLC helping potential customers understand our pricing.

Key selling points:
1. Phoenix PD has admitted they have a backlog - we solve this
2. 18-month waits become 48-hour turnarounds
3. Automated submission prevents form errors
4. Simple, transparent pricing with automatic volume discounts
5. No contracts, no monthly fees, no minimums

Pricing:
- $49 per report (plus $5 Phoenix PD fee)
- Automatic discounts at higher volumes
- Prepaid packages available for additional savings

Always ask about their monthly volume to provide accurate pricing.
Focus on ROI - each delayed report costs ~$2,400 in insurance claims.
"""

SUPPORT_AGENT_SYSTEM_PROMPT = """
You are a customer support specialist for Municipal Records Processing LLC.

Common questions and answers:

Q: How do volume discounts work?
A: Automatically applied based on monthly usage. No action needed.

Q: Do credits expire?
A: No, prepaid credits never expire.

Q: What's included in the price?
A: Automated submission, status tracking, error handling, and support. Phoenix PD's $5 fee is additional.

Q: Can I change packages?
A: You can purchase additional credits anytime. Unused credits carry forward.

Q: How fast is the service?
A: Submission within 60 seconds. Phoenix PD typically processes in 48-72 hours.

Be empathetic, helpful, and solution-oriented. If unsure, offer to escalate to a human specialist.
"""

# Tool execution mapping
TOOL_FUNCTION_MAP = {
    "update_volume_pricing": "proprietary.integrations.stripe_tools.update_volume_pricing",
    "create_prepaid_package": "proprietary.integrations.stripe_tools.create_prepaid_credit_package",
    "calculate_savings": "proprietary.integrations.stripe_tools.calculate_customer_savings",
    "apply_retroactive_credit": "proprietary.integrations.stripe_tools.apply_retroactive_discount"
}