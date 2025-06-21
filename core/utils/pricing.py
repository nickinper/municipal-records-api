"""
Pricing utilities for volume-based discounts.

Implements the automatic discount structure:
- 1-10 reports: $49 each (0% discount)
- 11-50 reports: $39.20 each (20% discount)
- 51+ reports: $29.40 each (40% discount)
"""

from typing import Dict, Tuple, List
from decimal import Decimal, ROUND_HALF_UP


def get_volume_discount(quantity: int) -> Tuple[int, Decimal]:
    """
    Get discount percentage and price per credit based on quantity.
    
    Args:
        quantity: Number of reports/credits being purchased
        
    Returns:
        Tuple of (discount_percent, price_per_credit)
    """
    base_price = Decimal("49.00")
    
    if quantity >= 51:
        discount = 40
        price = base_price * Decimal("0.60")  # 60% of original price
    elif quantity >= 11:
        discount = 20
        price = base_price * Decimal("0.80")  # 80% of original price
    else:
        discount = 0
        price = base_price
        
    # Round to 2 decimal places
    price = price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    return discount, price


def calculate_order_total(quantity: int, include_pd_fee: bool = False, pd_fee: Decimal = Decimal("5.00")) -> Dict[str, Decimal]:
    """
    Calculate the total cost for an order with automatic discounts.
    
    Args:
        quantity: Number of reports
        include_pd_fee: Whether to include Phoenix PD fees in calculation
        pd_fee: Phoenix PD fee per report (default $5)
        
    Returns:
        Dictionary with pricing breakdown
    """
    discount_percent, price_per_credit = get_volume_discount(quantity)
    
    subtotal = price_per_credit * quantity
    pd_fees_total = pd_fee * quantity if include_pd_fee else Decimal("0")
    total = subtotal + pd_fees_total
    
    # Calculate savings
    full_price = Decimal("49.00") * quantity
    savings = full_price - subtotal
    
    return {
        "quantity": quantity,
        "price_per_credit": price_per_credit,
        "discount_percent": discount_percent,
        "subtotal": subtotal.quantize(Decimal("0.01")),
        "pd_fees": pd_fees_total.quantize(Decimal("0.01")),
        "total": total.quantize(Decimal("0.01")),
        "savings": savings.quantize(Decimal("0.01")),
        "full_price": full_price.quantize(Decimal("0.01"))
    }


def get_credit_packages() -> List[Dict[str, any]]:
    """
    Get predefined credit packages with their pricing.
    
    Returns:
        List of credit package options
    """
    packages = []
    
    # Define standard packages
    package_sizes = [
        (12, "Starter"),      # 20% discount tier
        (60, "Professional"), # 40% discount tier  
        (200, "Enterprise")   # 40% discount tier
    ]
    
    for quantity, name in package_sizes:
        package = calculate_order_total(quantity)
        package["name"] = name
        packages.append(package)
        
    return packages


def calculate_monthly_savings(reports_per_month: int, months: int = 12) -> Dict[str, Decimal]:
    """
    Calculate annual savings for a given monthly volume.
    
    Args:
        reports_per_month: Average reports per month
        months: Number of months (default 12)
        
    Returns:
        Dictionary with savings calculations
    """
    # Calculate with and without discounts
    monthly_total = calculate_order_total(reports_per_month)
    annual_quantity = reports_per_month * months
    annual_total = calculate_order_total(annual_quantity)
    
    # Monthly savings
    monthly_savings = monthly_total["savings"]
    
    # Annual savings (buying in bulk)
    annual_savings = annual_total["savings"]
    
    return {
        "reports_per_month": reports_per_month,
        "monthly_cost_no_discount": monthly_total["full_price"],
        "monthly_cost_with_discount": monthly_total["subtotal"],
        "monthly_savings": monthly_savings,
        "annual_reports": annual_quantity,
        "annual_cost_no_discount": annual_total["full_price"],
        "annual_cost_with_discount": annual_total["subtotal"],
        "annual_savings": annual_savings
    }


def format_price_message(quantity: int, include_examples: bool = True) -> str:
    """
    Format a pricing message for the given quantity.
    
    Args:
        quantity: Number of reports
        include_examples: Whether to include example calculations
        
    Returns:
        Formatted pricing message
    """
    pricing = calculate_order_total(quantity, include_pd_fee=True)
    
    message = f"Pricing for {quantity} reports:\n"
    
    if pricing["discount_percent"] > 0:
        message += f"- Service fee: ${pricing['price_per_credit']} each ({pricing['discount_percent']}% discount)\n"
    else:
        message += f"- Service fee: ${pricing['price_per_credit']} each\n"
        
    message += f"- Phoenix PD fee: $5.00 each\n"
    message += f"- Total per report: ${pricing['price_per_credit'] + Decimal('5.00')}\n"
    
    if include_examples and quantity > 1:
        message += f"\nTotal cost: ${pricing['total']}"
        if pricing["savings"] > 0:
            message += f" (You save ${pricing['savings']}!)"
            
    return message


def get_best_package_for_quantity(quantity: int) -> Dict[str, any]:
    """
    Recommend the best credit package for a given quantity need.
    
    Args:
        quantity: Expected number of reports needed
        
    Returns:
        Best package recommendation
    """
    packages = get_credit_packages()
    
    # Find the smallest package that covers the need
    for package in sorted(packages, key=lambda x: x["quantity"]):
        if package["quantity"] >= quantity:
            return package
            
    # If no package is large enough, calculate custom
    return calculate_order_total(quantity)


# Example usage and pricing table generator
if __name__ == "__main__":
    print("Municipal Records Processing - Volume Pricing Calculator")
    print("=" * 60)
    
    # Show pricing tiers
    print("\nPRICING TIERS:")
    for qty in [1, 11, 51]:
        discount, price = get_volume_discount(qty)
        print(f"{qty}+ reports: ${price} each ({discount}% off)")
        
    # Show example calculations
    print("\n\nEXAMPLE CALCULATIONS:")
    for qty in [10, 20, 50, 100]:
        pricing = calculate_order_total(qty, include_pd_fee=True)
        print(f"\n{qty} reports:")
        print(f"  Service: ${pricing['subtotal']}")
        print(f"  PD fees: ${pricing['pd_fees']}")
        print(f"  Total: ${pricing['total']}")
        if pricing['savings'] > 0:
            print(f"  Savings: ${pricing['savings']}")
            
    # Show credit packages
    print("\n\nCREDIT PACKAGES:")
    for package in get_credit_packages():
        print(f"\n{package['name']} Package ({package['quantity']} credits):")
        print(f"  Price: ${package['total']}")
        print(f"  Per credit: ${package['price_per_credit']}")
        print(f"  Savings: ${package['savings']}")