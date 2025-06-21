#!/usr/bin/env python3
"""
Test the Claude-powered pricing assistant.

This script demonstrates the AI pricing agent handling various customer queries.
"""

import asyncio
import os
import sys
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up test environment
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "test-key")

from proprietary.ai.claude_pricing_agent import PricingAgent


async def test_pricing_queries():
    """Test various pricing queries."""
    
    # Initialize agent
    agent = PricingAgent(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        agent_type="pricing"
    )
    
    # Test customer data
    customer_data = {
        "stripe_id": "cus_test123",
        "email": "insurance@testcompany.com",
        "monthly_usage": 75,
        "total_requests": 450,
        "account_type": "bulk",
        "current_tier": "bulk",
        "credits_balance": 15,
        "company_name": "Test Insurance Co"
    }
    
    # Test queries
    test_queries = [
        "We're doing about 75 requests per month now. What's our best option?",
        "How do volume discounts work?",
        "Can you show me how much we'd save with prepaid credits?",
        "We just hit 51 orders this month. Do we get a discount?",
        "What's the difference between monthly billing and prepaid credits?",
        "I want to buy the professional package",
    ]
    
    print("Municipal Records Processing - AI Pricing Assistant Test")
    print("=" * 60)
    print(f"Customer: {customer_data['email']}")
    print(f"Current usage: {customer_data['monthly_usage']} reports/month")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n👤 Customer: {query}")
        
        try:
            # Get AI response
            result = await agent.handle_pricing_request(
                customer_query=query,
                customer_data=customer_data,
                conversation_history=[]
            )
            
            print(f"\n🤖 Assistant: {result['response']}")
            
            if result.get("actions"):
                print("\n📋 Actions taken:")
                for action in result["actions"]:
                    print(f"  - {action['tool']}: {action.get('input', {})}")
                    if action.get("result", {}).get("success"):
                        print(f"    ✅ Success")
                    else:
                        print(f"    ❌ Failed: {action.get('result', {}).get('error')}")
                        
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            
        print("\n" + "-" * 60)
        
        # Small delay between queries
        await asyncio.sleep(1)


async def test_conversation_flow():
    """Test a multi-turn conversation."""
    print("\n\nTESTING MULTI-TURN CONVERSATION")
    print("=" * 60)
    
    agent = PricingAgent(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        agent_type="sales"
    )
    
    # Prospect data
    customer_data = {
        "stripe_id": None,
        "email": None,
        "monthly_usage": 0,
        "total_requests": 0,
        "account_type": "prospect",
        "current_tier": "standard",
        "credits_balance": 0
    }
    
    conversation = [
        "Hi, I heard you can get Phoenix police reports faster?",
        "We're an insurance company processing about 200 claims per month in Phoenix",
        "How much would that cost us?",
        "Can we test it with one report first?"
    ]
    
    conversation_history = []
    
    for query in conversation:
        print(f"\n👤 Prospect: {query}")
        
        result = await agent.handle_pricing_request(
            customer_query=query,
            customer_data=customer_data,
            conversation_history=conversation_history
        )
        
        print(f"\n🤖 Sales Agent: {result['response']}")
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": query})
        conversation_history.append({"role": "assistant", "content": result['response']})
        
        await asyncio.sleep(1)


async def test_support_queries():
    """Test support agent responses."""
    print("\n\nTESTING SUPPORT AGENT")
    print("=" * 60)
    
    agent = PricingAgent(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        agent_type="support"
    )
    
    support_queries = [
        "Do my credits expire?",
        "How fast do you submit to Phoenix PD?",
        "What happens if Phoenix PD rejects my request?",
        "Can I get a refund on unused credits?"
    ]
    
    customer_data = {
        "stripe_id": "cus_support123",
        "email": "support@customer.com",
        "monthly_usage": 25,
        "total_requests": 100,
        "account_type": "standard",
        "current_tier": "bulk",
        "credits_balance": 8
    }
    
    for query in support_queries:
        print(f"\n👤 Customer: {query}")
        
        result = await agent.handle_pricing_request(
            customer_query=query,
            customer_data=customer_data
        )
        
        print(f"\n🤖 Support: {result['response']}")
        
        await asyncio.sleep(1)


async def main():
    """Run all tests."""
    # Check if API key is set
    if not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") == "test-key":
        print("⚠️  WARNING: ANTHROPIC_API_KEY not set")
        print("This test requires a valid Anthropic API key to function")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        print("\nSkipping actual API calls, showing test structure only...")
        return
    
    # Run tests
    await test_pricing_queries()
    await test_conversation_flow()
    await test_support_queries()
    
    print("\n\n✅ All tests completed!")
    print("\nKey capabilities demonstrated:")
    print("- Automatic volume discount calculations")
    print("- Prepaid package recommendations")
    print("- Multi-turn conversations")
    print("- Different agent personalities (pricing, sales, support)")
    print("- Tool execution for Stripe operations")


if __name__ == "__main__":
    asyncio.run(main())