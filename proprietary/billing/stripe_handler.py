"""
Stripe payment handler for Municipal Records Processing.

Handles payment links, webhooks, and API key generation.
"""

import stripe
import secrets
import string
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class StripeHandler:
    """Handle Stripe payments and webhooks."""
    
    def __init__(self, api_key: str, webhook_secret: str):
        """
        Initialize Stripe handler.
        
        Args:
            api_key: Stripe secret key
            webhook_secret: Webhook endpoint secret
        """
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        stripe.api_key = api_key
        
    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a secure API key for customers.
        
        Format: mpr_live_<32 random characters>
        """
        # Generate 32 character random string
        alphabet = string.ascii_letters + string.digits
        random_part = ''.join(secrets.choice(alphabet) for _ in range(32))
        
        # Use mpr prefix (Municipal Processing Records)
        return f"mpr_live_{random_part}"
        
    async def create_payment_link(
        self,
        request_id: str,
        amount: int,
        description: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe payment link for a request.
        
        Args:
            request_id: Unique request ID
            amount: Amount in cents
            description: Payment description
            customer_email: Pre-fill customer email
            metadata: Additional metadata
            
        Returns:
            Dictionary with success, url, and session_id
        """
        try:
            # Create checkout session
            session_params = {
                "payment_method_types": ["card"],
                "mode": "payment",
                "line_items": [{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "Phoenix PD Records Request",
                            "description": description,
                        },
                        "unit_amount": amount,
                    },
                    "quantity": 1,
                }],
                # Use localhost for development/testing
                "success_url": f"http://localhost:8001/order.html?success=true&request_id={request_id}",
                "cancel_url": "http://localhost:8001/order.html?canceled=true",
                "metadata": metadata or {},
                "payment_intent_data": {
                    "metadata": metadata or {}
                }
            }
            
            if customer_email:
                session_params["customer_email"] = customer_email
                
            session = stripe.checkout.Session.create(**session_params)
            
            logger.info(f"Created payment session {session.id} for request {request_id}")
            
            return {
                "success": True,
                "url": session.url,
                "session_id": session.id
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment link: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def verify_webhook(
        self, 
        payload: bytes, 
        signature: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify and parse a Stripe webhook.
        
        Args:
            payload: Raw request body
            signature: Stripe-Signature header
            
        Returns:
            Parsed event object or None if invalid
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            logger.info(f"Verified webhook event: {event['type']}")
            return event
            
        except ValueError:
            logger.error("Invalid webhook payload")
            return None
            
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid webhook signature")
            return None
            
    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create a Stripe customer.
        
        Args:
            email: Customer email
            name: Customer name
            metadata: Additional metadata
            
        Returns:
            Stripe customer ID or None
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            
            logger.info(f"Created Stripe customer {customer.id} for {email}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating customer: {str(e)}")
            return None
            
    async def retrieve_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a checkout session.
        
        Args:
            session_id: Stripe session ID
            
        Returns:
            Session object or None
        """
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return session
            
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving session: {str(e)}")
            return None