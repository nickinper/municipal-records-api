"""
Claude-powered pricing agent for automated customer support.

Handles pricing inquiries, applies discounts, and creates payment links.
"""

import anthropic
from typing import Dict, List, Optional, Any
import json
import logging
from datetime import datetime
import importlib

from .claude_tools_config import (
    STRIPE_PRICING_TOOLS,
    PRICING_AGENT_SYSTEM_PROMPT,
    SALES_AGENT_SYSTEM_PROMPT,
    SUPPORT_AGENT_SYSTEM_PROMPT,
    TOOL_FUNCTION_MAP
)

logger = logging.getLogger(__name__)


class PricingAgent:
    """AI-powered pricing assistant using Claude."""
    
    def __init__(self, api_key: str, agent_type: str = "pricing"):
        """
        Initialize the pricing agent.
        
        Args:
            api_key: Anthropic API key
            agent_type: Type of agent ('pricing', 'sales', 'support')
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.agent_type = agent_type
        self.system_prompt = self._get_system_prompt(agent_type)
        
    def _get_system_prompt(self, agent_type: str) -> str:
        """Get the appropriate system prompt based on agent type."""
        prompts = {
            "pricing": PRICING_AGENT_SYSTEM_PROMPT,
            "sales": SALES_AGENT_SYSTEM_PROMPT,
            "support": SUPPORT_AGENT_SYSTEM_PROMPT
        }
        return prompts.get(agent_type, PRICING_AGENT_SYSTEM_PROMPT)
        
    async def handle_pricing_request(
        self, 
        customer_query: str, 
        customer_data: Dict[str, Any],
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Process customer pricing requests with Claude.
        
        Args:
            customer_query: The customer's question or request
            customer_data: Customer information including usage data
            conversation_history: Previous messages in the conversation
            
        Returns:
            Dictionary with response and any actions taken
        """
        
        # Build message context
        messages = conversation_history or []
        
        # Add customer context
        context_message = {
            "role": "user",
            "content": f"""
Customer query: {customer_query}

Customer data:
- Customer ID: {customer_data.get('stripe_id', 'Not available')}
- Email: {customer_data.get('email', 'Not provided')}
- Current month usage: {customer_data.get('monthly_usage', 0)} reports
- Total lifetime requests: {customer_data.get('total_requests', 0)}
- Account type: {customer_data.get('account_type', 'standard')}
- Current pricing tier: {customer_data.get('current_tier', 'standard')}
- Credits balance: {customer_data.get('credits_balance', 0)}

Current date: {datetime.now().strftime('%Y-%m-%d')}
"""
        }
        
        messages.append(context_message)
        
        try:
            # Get Claude's response
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                temperature=0,
                system=self.system_prompt,
                messages=messages,
                tools=STRIPE_PRICING_TOOLS
            )
            
            # Process the response
            result = {
                "success": True,
                "response": "",
                "actions": [],
                "tool_results": []
            }
            
            # Handle tool use
            if response.stop_reason == "tool_use":
                for content in response.content:
                    if content.type == "tool_use":
                        tool_result = await self._execute_tool(
                            tool_name=content.name,
                            tool_input=content.input,
                            customer_data=customer_data
                        )
                        result["tool_results"].append(tool_result)
                        result["actions"].append({
                            "tool": content.name,
                            "input": content.input,
                            "result": tool_result
                        })
                        
                # Get Claude's final response after tool execution
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # Add tool results
                for tool_result in result["tool_results"]:
                    messages.append({
                        "role": "user",
                        "content": f"Tool result: {json.dumps(tool_result)}"
                    })
                
                # Get final response
                final_response = self.client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    temperature=0,
                    system=self.system_prompt,
                    messages=messages
                )
                
                result["response"] = final_response.content[0].text
                
            else:
                # Direct response without tool use
                result["response"] = response.content[0].text
                
            return result
            
        except Exception as e:
            logger.error(f"Error in pricing agent: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": "I apologize, but I encountered an error processing your request. Please try again or contact support@municipalrecordsprocessing.com for assistance."
            }
            
    async def _execute_tool(
        self, 
        tool_name: str, 
        tool_input: Dict[str, Any],
        customer_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool function based on Claude's request.
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool
            customer_data: Customer context data
            
        Returns:
            Tool execution result
        """
        try:
            # Get the function path
            function_path = TOOL_FUNCTION_MAP.get(tool_name)
            if not function_path:
                return {"error": f"Unknown tool: {tool_name}"}
                
            # Import and execute the function
            module_path, function_name = function_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            function = getattr(module, function_name)
            
            # Add customer email if available and not provided
            if tool_name == "create_prepaid_package" and "customer_email" not in tool_input:
                tool_input["customer_email"] = customer_data.get("email")
                
            # Execute the function
            result = function(**tool_input)
            
            # Log the action
            logger.info(f"Executed tool {tool_name} for customer {customer_data.get('stripe_id', 'unknown')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {"error": str(e)}
            
    def format_pricing_update(self, result: Dict[str, Any]) -> str:
        """Format a pricing update result for customer display."""
        if not result.get("success"):
            return "I encountered an error updating your pricing. Please contact support for assistance."
            
        return f"""
Great news! Your pricing has been automatically updated based on your usage:

📊 **New Pricing Tier: {result['tier_name'].title()}**
- Price per report: ${result['new_price']:.2f} (was $49.00)
- Discount: {result['discount_percent']}% off
- Monthly savings: ${result.get('monthly_savings', 0):.2f}

This pricing applies automatically to all future orders. No action needed on your part!
"""
        
    def format_package_offer(self, result: Dict[str, Any]) -> str:
        """Format a package offer for customer display."""
        if not result.get("success"):
            return "I encountered an error creating your package. Please try again or contact support."
            
        return f"""
🎯 **{result['package_type'].title()} Package Created!**

- Credits: {result['credits']}
- Total cost: ${result['total_cost']:.2f}
- Savings: ${result['savings']:.2f}
- Price per credit: ${result['cost_per_credit']:.2f}

**Ready to purchase?** [Click here to buy now]({result['payment_link']})

Credits never expire and can be used anytime. This package will save you ${result['savings']:.2f} compared to standard pricing!
"""

    def format_savings_analysis(self, result: Dict[str, Any]) -> str:
        """Format a savings analysis for customer display."""
        return f"""
💰 **Savings Analysis for {result['monthly_usage']} reports/month:**

**Annual Usage:** {result['annual_usage']} reports

**Current Cost:** ${result['current_annual_cost']:,.2f}/year

**Potential Savings:**
- With volume discounts: ${result['potential_savings']['with_volume_discount']:,.2f}/year
- With prepaid packages: ${result['potential_savings']['with_best_package']:,.2f}/year

**Recommended:** {result['recommended_tier'].title()} tier

Would you like me to help you set up a prepaid package to maximize your savings?
"""


class ConversationManager:
    """Manages conversation state for multi-turn interactions."""
    
    def __init__(self):
        self.conversations = {}
        
    def get_conversation(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session."""
        return self.conversations.get(session_id, [])
        
    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the conversation history."""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
            
        self.conversations[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last 10 messages to manage context window
        if len(self.conversations[session_id]) > 10:
            self.conversations[session_id] = self.conversations[session_id][-10:]
            
    def clear_conversation(self, session_id: str):
        """Clear conversation history for a session."""
        if session_id in self.conversations:
            del self.conversations[session_id]