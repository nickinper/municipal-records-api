"""
Database models for Municipal Records Processing.

Handles requests, pricing, and tracking for multiple report types.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, 
    ForeignKey, Text, Numeric, Index, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ReportType(str, Enum):
    """Types of reports available from Phoenix PD."""
    INCIDENT = "incident"
    TRAFFIC_CRASH = "traffic_crash"
    BODY_CAMERA = "body_camera"
    SURVEILLANCE = "surveillance"
    RECORDINGS_911 = "recordings_911"
    CALLS_FOR_SERVICE = "calls_for_service"
    CRIME_STATISTICS = "crime_statistics"
    

class RequestStatus(str, Enum):
    """Status of a document request."""
    PENDING_PAYMENT = "pending_payment"
    PAYMENT_PROCESSING = "payment_processing"
    PAID = "paid"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    READY = "ready"
    DELIVERED = "delivered"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PricingTier(str, Enum):
    """Pricing tiers based on volume."""
    STANDARD = "standard"  # 1-10 reports: $49 each
    BULK = "bulk"         # 11-50 reports: 20% off ($39.20 each)
    VOLUME = "volume"     # 51+ reports: 40% off ($29.40 each)


class Customer(Base):
    """Customer information and billing."""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Contact info
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    company_name = Column(String(255))
    phone = Column(String(50))
    
    # Customer type
    tier = Column(SQLEnum(PricingTier), default=PricingTier.STANDARD)
    is_api_enabled = Column(Boolean, default=False)
    api_key = Column(String(64), unique=True, index=True)
    
    # Stripe info
    stripe_customer_id = Column(String(100), unique=True, index=True)
    
    # Credits
    credits_balance = Column(Integer, default=0)
    credits_purchased = Column(Integer, default=0)
    credits_used = Column(Integer, default=0)
    
    # Stats
    total_requests = Column(Integer, default=0)
    total_spent = Column(Numeric(10, 2), default=0)
    
    # Relationships
    requests = relationship("Request", back_populates="customer")
    credit_purchases = relationship("CreditPurchase", back_populates="customer")
    

class CreditPurchase(Base):
    """Track credit purchases by customers."""
    __tablename__ = "credit_purchases"
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Customer
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer = relationship("Customer", back_populates="credit_purchases")
    
    # Purchase details
    credits_amount = Column(Integer, nullable=False)
    total_cost = Column(Numeric(10, 2), nullable=False)
    cost_per_credit = Column(Numeric(6, 2), nullable=False)
    discount_percent = Column(Integer, default=0)
    
    # Payment info
    stripe_payment_intent_id = Column(String(100), index=True)
    stripe_checkout_session_id = Column(String(100), index=True)
    paid_at = Column(DateTime)
    
    # Status
    status = Column(String(50), default="pending")  # pending, completed, failed, refunded
    

class ReportPricing(Base):
    """Pricing for different report types."""
    __tablename__ = "report_pricing"
    
    id = Column(Integer, primary_key=True)
    report_type = Column(SQLEnum(ReportType), nullable=False, unique=True)
    
    # Phoenix PD fees
    base_fee = Column(Numeric(6, 2), nullable=False)
    
    # Our service fee (before any discounts)
    service_fee = Column(Numeric(6, 2), nullable=False, default=49.00)
    
    # Metadata
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    average_processing_hours = Column(Integer, default=48)
    max_processing_days = Column(Integer, default=7)
    
    # Special rules
    restrictions = Column(JSON)  # e.g., {"max_age_days": 190} for 911 recordings
    

class Request(Base):
    """Individual document request."""
    __tablename__ = "requests"
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String(50), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Customer
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer = relationship("Customer", back_populates="requests")
    
    # Request details
    report_type = Column(SQLEnum(ReportType), nullable=False)
    case_number = Column(String(100), nullable=False, index=True)
    incident_date = Column(DateTime)
    
    # Additional requestor info (if different from customer)
    requestor_first_name = Column(String(100))
    requestor_last_name = Column(String(100))
    requestor_email = Column(String(255))
    requestor_phone = Column(String(50))
    
    # Location info (for some report types)
    incident_location = Column(Text)
    
    # Status tracking
    status = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING_PAYMENT, index=True)
    
    # Submission details
    submitted_at = Column(DateTime)
    submission_confirmation = Column(String(100))
    submission_evidence = Column(JSON)  # screenshot paths
    
    # Phoenix PD response
    pd_status = Column(String(50))
    pd_updated_at = Column(DateTime)
    ready_at = Column(DateTime)
    document_urls = Column(JSON)
    
    # Payment info
    stripe_payment_intent_id = Column(String(100), index=True)
    stripe_checkout_session_id = Column(String(100), index=True)
    amount_charged = Column(Numeric(6, 2))
    base_fee_amount = Column(Numeric(6, 2))
    service_fee_amount = Column(Numeric(6, 2))
    paid_at = Column(DateTime)
    
    # Error tracking
    error_count = Column(Integer, default=0)
    last_error = Column(Text)
    last_error_at = Column(DateTime)
    
    # Metadata
    notes = Column(Text)
    internal_notes = Column(Text)
    source = Column(String(50))  # 'api', 'web', 'manual'
    
    # Indexes
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_customer_status', 'customer_id', 'status'),
        Index('idx_case_customer', 'case_number', 'customer_id'),
    )
    

class RequestEvent(Base):
    """Audit trail of all request events."""
    __tablename__ = "request_events"
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False)
    request = relationship("Request")
    
    event_type = Column(String(50), nullable=False)  # 'payment_received', 'submitted', etc
    event_data = Column(JSON)
    
    # Who triggered it
    triggered_by = Column(String(50))  # 'system', 'webhook', 'admin', 'customer'
    
    __table_args__ = (
        Index('idx_request_created', 'request_id', 'created_at'),
    )
    

class SystemMetric(Base):
    """Track system performance and revenue metrics."""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    metric_type = Column(String(50), nullable=False)  # 'daily_revenue', 'submission_time', etc
    metric_value = Column(Numeric(10, 2))
    metric_data = Column(JSON)
    
    report_type = Column(SQLEnum(ReportType))
    date = Column(DateTime, nullable=False)
    
    __table_args__ = (
        Index('idx_metric_date', 'metric_type', 'date'),
    )


def get_volume_discount(quantity: int) -> tuple[int, float]:
    """
    Get discount percentage and price per credit based on quantity.
    
    Returns:
        Tuple of (discount_percent, price_per_credit)
    """
    if quantity >= 51:
        return 40, 29.40  # 40% off
    elif quantity >= 11:
        return 20, 39.20  # 20% off
    else:
        return 0, 49.00   # No discount


def calculate_credit_package(quantity: int) -> dict:
    """Calculate pricing for a credit package."""
    discount_percent, price_per_credit = get_volume_discount(quantity)
    total_cost = quantity * price_per_credit
    savings = (quantity * 49.00) - total_cost
    
    return {
        "quantity": quantity,
        "price_per_credit": price_per_credit,
        "discount_percent": discount_percent,
        "total_cost": total_cost,
        "savings": savings
    }


def initialize_pricing():
    """Initialize default pricing for all report types."""
    # All reports now use the same $49 service fee
    # Discounts are applied at purchase time based on volume
    return [
        ReportPricing(
            report_type=ReportType.INCIDENT,
            base_fee=5.00,
            service_fee=49.00,
            display_name="Incident Report",
            description="Police incident reports for insurance claims, legal cases, and investigations",
            average_processing_hours=48
        ),
        ReportPricing(
            report_type=ReportType.TRAFFIC_CRASH,
            base_fee=5.00,
            service_fee=49.00,
            display_name="Traffic Crash Report",
            description="Official traffic accident reports required for insurance claims",
            average_processing_hours=48
        ),
        ReportPricing(
            report_type=ReportType.BODY_CAMERA,
            base_fee=4.00,
            service_fee=49.00,
            display_name="Body Camera Footage",
            description="Officer body-worn camera recordings from specific incidents",
            average_processing_hours=72,
            max_processing_days=14
        ),
        ReportPricing(
            report_type=ReportType.SURVEILLANCE,
            base_fee=4.00,
            service_fee=49.00,
            display_name="Surveillance Video",
            description="Security camera footage from police investigations",
            average_processing_hours=72,
            max_processing_days=14
        ),
        ReportPricing(
            report_type=ReportType.RECORDINGS_911,
            base_fee=16.50,
            service_fee=49.00,
            display_name="911 Call Recording",
            description="Audio recordings of 911 emergency calls",
            average_processing_hours=24,
            restrictions={"max_age_days": 190}
        ),
        ReportPricing(
            report_type=ReportType.CALLS_FOR_SERVICE,
            base_fee=0.00,
            service_fee=49.00,
            display_name="Calls for Service",
            description="List of all police calls to a specific address",
            average_processing_hours=24
        ),
        ReportPricing(
            report_type=ReportType.CRIME_STATISTICS,
            base_fee=0.00,
            service_fee=49.00,
            display_name="Crime Statistics",
            description="Crime data for specific areas or time periods",
            average_processing_hours=24
        ),
    ]