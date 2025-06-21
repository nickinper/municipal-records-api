"""
Stripe pricing automation tools for volume discounts.

Automatically applies tiered pricing based on customer usage.
"""

import stripe
from typing import Dict, List, Optional
import os
from datetime import datetime
from decimal import Decimal

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')


def update_volume_pricing(customer_id: str, usage_count: int) -> Dict:
    """
    Automatically apply volume discounts based on usage.
    
    Pricing tiers:
    - 1-10: $49/request
    - 11-50: $39.20/request (20% off)
    - 51-100: $29.40/request (40% off)
    - 100+: $19.60/request (60% off)
    
    Args:
        customer_id: Stripe customer ID
        usage_count: Total number of requests this month
        
    Returns:
        Dictionary with pricing update details
    """
    
    # Determine price tier
    if usage_count <= 10:
        price_per_unit = 4900  # $49.00
        discount = 0
        tier_name = "standard"
    elif usage_count <= 50:
        price_per_unit = 3920  # $39.20
        discount = 20
        tier_name = "bulk"
    elif usage_count <= 100:
        price_per_unit = 2940  # $29.40
        discount = 40
        tier_name = "volume"
    else:
        price_per_unit = 1960  # $19.60
        discount = 60
        tier_name = "enterprise"
    
    try:
        # Update customer metadata
        stripe.Customer.modify(
            customer_id,
            metadata={
                'current_price_tier': tier_name,
                'price_per_request': price_per_unit,
                'volume_discount': discount,
                'total_requests': usage_count,
                'tier_updated_at': datetime.utcnow().isoformat()
            }
        )
        
        return {
            'success': True,
            'customer_id': customer_id,
            'tier_name': tier_name,
            'new_price': price_per_unit / 100,
            'discount_percent': discount,
            'total_requests': usage_count,
            'monthly_savings': (4900 - price_per_unit) * usage_count / 100
        }
        
    except stripe.error.StripeError as e:
        return {
            'success': False,
            'error': str(e),
            'customer_id': customer_id
        }


def create_prepaid_credit_package(package_type: str, customer_email: Optional[str] = None) -> Dict:
    """
    Create prepaid credit packages with bulk discounts.
    
    Args:
        package_type: One of 'starter', 'professional', 'enterprise'
        customer_email: Optional email for the payment link
        
    Returns:
        Dictionary with package details and payment link
    """
    
    packages = {
        'starter': {
            'amount': 50000,  # $500
            'credits': 12,
            'savings': 88,
            'description': '12 credits for $500 (save $88)'
        },
        'professional': {
            'amount': 200000,  # $2,000
            'credits': 60,
            'savings': 940,
            'description': '60 credits for $2,000 (save $940)'
        },
        'enterprise': {
            'amount': 500000,  # $5,000
            'credits': 200,
            'savings': 4800,
            'description': '200 credits for $5,000 (save $4,800)'
        }
    }
    
    package = packages.get(package_type)
    if not package:
        return {'success': False, 'error': 'Invalid package type'}
    
    try:
        # Create Stripe product for credits
        product = stripe.Product.create(
            name=f"Prepaid Credits - {package_type.title()} Package",
            description=package['description'],
            metadata={
                'credits': package['credits'],
                'type': 'prepaid_package',
                'package_type': package_type
            }
        )
        
        # Create one-time price
        price = stripe.Price.create(
            product=product.id,
            unit_amount=package['amount'],
            currency='usd',
            metadata={
                'credits': package['credits'],
                'package_type': package_type
            }
        )
        
        # Create payment link
        payment_link = create_payment_link(
            price_id=price.id,
            customer_email=customer_email,
            package_type=package_type
        )
        
        return {
            'success': True,
            'package_type': package_type,
            'price_id': price.id,
            'payment_link': payment_link,
            'credits': package['credits'],
            'total_cost': package['amount'] / 100,
            'savings': package['savings'],
            'cost_per_credit': package['amount'] / package['credits'] / 100
        }
        
    except stripe.error.StripeError as e:
        return {
            'success': False,
            'error': str(e),
            'package_type': package_type
        }


def create_payment_link(price_id: str, customer_email: Optional[str] = None, package_type: str = None) -> str:
    """
    Create a Stripe payment link for the given price.
    
    Args:
        price_id: Stripe price ID
        customer_email: Pre-fill customer email
        package_type: Type of package for metadata
        
    Returns:
        Payment link URL
    """
    try:
        link_params = {
            'line_items': [{
                'price': price_id,
                'quantity': 1
            }],
            'after_completion': {
                'type': 'redirect',
                'redirect': {
                    'url': os.getenv('BASE_URL', 'https://municipalrecordsprocessing.com') + '/credits-purchased'
                }
            },
            'metadata': {
                'type': 'prepaid_credits',
                'package_type': package_type or 'custom'
            }
        }
        
        if customer_email:
            link_params['customer_email'] = customer_email
            
        payment_link = stripe.PaymentLink.create(**link_params)
        return payment_link.url
        
    except stripe.error.StripeError:
        # Fallback to checkout session
        return create_checkout_session(price_id, customer_email, package_type)


def create_checkout_session(price_id: str, customer_email: Optional[str] = None, package_type: str = None) -> str:
    """
    Create a checkout session as fallback.
    """
    session_params = {
        'mode': 'payment',
        'line_items': [{
            'price': price_id,
            'quantity': 1
        }],
        'success_url': os.getenv('BASE_URL', 'https://municipalrecordsprocessing.com') + '/credits-purchased?session_id={CHECKOUT_SESSION_ID}',
        'cancel_url': os.getenv('BASE_URL', 'https://municipalrecordsprocessing.com') + '/pricing',
        'metadata': {
            'type': 'prepaid_credits',
            'package_type': package_type or 'custom'
        }
    }
    
    if customer_email:
        session_params['customer_email'] = customer_email
        
    session = stripe.checkout.Session.create(**session_params)
    return session.url


def calculate_customer_savings(customer_id: str, monthly_usage: int) -> Dict:
    """
    Calculate how much a customer could save with different packages.
    
    Args:
        customer_id: Stripe customer ID
        monthly_usage: Average monthly usage
        
    Returns:
        Dictionary with savings analysis
    """
    annual_usage = monthly_usage * 12
    
    # Calculate costs at different tiers
    standard_annual_cost = annual_usage * 49
    
    # Bulk tier (20% off)
    if annual_usage >= 11 * 12:
        bulk_annual_cost = annual_usage * 39.20
    else:
        bulk_annual_cost = standard_annual_cost
        
    # Volume tier (40% off)
    if annual_usage >= 51 * 12:
        volume_annual_cost = annual_usage * 29.40
    else:
        volume_annual_cost = bulk_annual_cost
        
    # Enterprise tier (60% off)
    if annual_usage >= 100 * 12:
        enterprise_annual_cost = annual_usage * 19.60
    else:
        enterprise_annual_cost = volume_annual_cost
    
    # Calculate prepaid package savings
    packages_analysis = []
    
    # Starter package
    if annual_usage >= 12:
        starter_cost = (annual_usage / 12) * 500
        starter_savings = standard_annual_cost - starter_cost
        packages_analysis.append({
            'package': 'starter',
            'annual_cost': starter_cost,
            'savings': starter_savings,
            'break_even_months': 12 / (monthly_usage or 1)
        })
    
    # Professional package
    if annual_usage >= 60:
        pro_packages_needed = annual_usage / 60
        pro_cost = pro_packages_needed * 2000
        pro_savings = standard_annual_cost - pro_cost
        packages_analysis.append({
            'package': 'professional',
            'annual_cost': pro_cost,
            'savings': pro_savings,
            'packages_needed': int(pro_packages_needed + 0.99)
        })
    
    # Enterprise package
    if annual_usage >= 200:
        ent_packages_needed = annual_usage / 200
        ent_cost = ent_packages_needed * 5000
        ent_savings = standard_annual_cost - ent_cost
        packages_analysis.append({
            'package': 'enterprise',
            'annual_cost': ent_cost,
            'savings': ent_savings,
            'packages_needed': int(ent_packages_needed + 0.99)
        })
    
    return {
        'customer_id': customer_id,
        'monthly_usage': monthly_usage,
        'annual_usage': annual_usage,
        'current_annual_cost': standard_annual_cost,
        'potential_savings': {
            'with_volume_discount': standard_annual_cost - min(enterprise_annual_cost, volume_annual_cost, bulk_annual_cost),
            'with_best_package': max([p['savings'] for p in packages_analysis]) if packages_analysis else 0
        },
        'recommended_tier': 'enterprise' if annual_usage >= 1200 else 'volume' if annual_usage >= 612 else 'bulk' if annual_usage >= 132 else 'standard',
        'package_analysis': packages_analysis
    }


def apply_retroactive_discount(customer_id: str, order_count: int) -> Dict:
    """
    Apply retroactive discount when customer hits a new tier threshold.
    
    Args:
        customer_id: Stripe customer ID
        order_count: Number of orders in current period
        
    Returns:
        Credit details if applicable
    """
    # Check if customer just crossed a threshold
    thresholds = [
        (11, 20, "bulk"),
        (51, 40, "volume"),
        (100, 60, "enterprise")
    ]
    
    for threshold, discount_percent, tier_name in thresholds:
        if order_count == threshold:
            # Calculate retroactive credit
            orders_to_credit = threshold
            original_cost = orders_to_credit * 49
            discounted_cost = orders_to_credit * (49 * (100 - discount_percent) / 100)
            credit_amount = int((original_cost - discounted_cost) * 100)  # In cents
            
            try:
                # Create credit note
                credit_note = stripe.CreditNote.create(
                    customer=customer_id,
                    amount=credit_amount,
                    memo=f"Retroactive {tier_name} tier discount applied",
                    metadata={
                        'type': 'volume_discount',
                        'tier': tier_name,
                        'order_count': order_count
                    }
                )
                
                return {
                    'success': True,
                    'credit_note_id': credit_note.id,
                    'credit_amount': credit_amount / 100,
                    'tier_reached': tier_name,
                    'message': f"Congratulations! You've reached {tier_name} tier and received ${credit_amount/100:.2f} credit!"
                }
                
            except stripe.error.StripeError as e:
                return {
                    'success': False,
                    'error': str(e)
                }
    
    return {
        'success': False,
        'message': 'No threshold reached'
    }