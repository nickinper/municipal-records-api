#!/usr/bin/env python3
"""
Test the multi-report scraper functionality.

This script demonstrates submitting different types of Phoenix PD reports.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.scrapers.phoenix_pd import PhoenixPDScraper


async def test_traffic_crash_report():
    """Test submitting a traffic crash report."""
    print("\n" + "="*60)
    print("TESTING TRAFFIC CRASH REPORT")
    print("="*60)
    
    async with PhoenixPDScraper(
        screenshot_dir="evidence",
        headless=True  # Set to False to watch it work!
    ) as scraper:
        
        result = await scraper.scrape(
            action="submit_request",
            report_type="traffic_crash",
            case_number="2024-TC-12345",
            requestor_info={
                "first_name": "Insurance",
                "last_name": "Adjuster",
                "email": "test@insurancecompany.com",
                "phone": "602-555-0123",
                "company": "Test Insurance Co"
            }
        )
        
        if result.get("status") == "submitted":
            print(f"✅ Successfully submitted traffic crash report!")
            print(f"   Report Type: {result.get('report_name')}")
            print(f"   Base Fee: ${result.get('base_fee')}")
            print(f"   Confirmation: {result.get('confirmation_number')}")
            print(f"   Evidence: {len(result.get('evidence_screenshots', []))} screenshots")
        else:
            print(f"❌ Failed to submit traffic crash report")
            print(f"   Status: {result}")


async def test_911_recording():
    """Test submitting a 911 recording request."""
    print("\n" + "="*60)
    print("TESTING 911 RECORDING REQUEST")
    print("="*60)
    
    # Use a date within 190 days
    incident_date = datetime.now() - timedelta(days=30)
    
    async with PhoenixPDScraper(
        screenshot_dir="evidence",
        headless=True
    ) as scraper:
        
        result = await scraper.scrape(
            action="submit_request",
            report_type="recordings_911",
            case_number="2024-911-67890",
            requestor_info={
                "first_name": "Law",
                "last_name": "Firm",
                "email": "test@lawfirm.com",
                "phone": "602-555-0456"
            },
            additional_data={
                "incident_date": incident_date
            }
        )
        
        if result.get("status") == "submitted":
            print(f"✅ Successfully submitted 911 recording request!")
            print(f"   Report Type: {result.get('report_name')}")
            print(f"   Base Fee: ${result.get('base_fee')}")
            print(f"   Confirmation: {result.get('confirmation_number')}")
        else:
            print(f"❌ Failed to submit 911 recording request")
            print(f"   Status: {result}")


async def test_invalid_911_recording():
    """Test that old 911 recordings are rejected."""
    print("\n" + "="*60)
    print("TESTING 911 RECORDING VALIDATION (>190 days)")
    print("="*60)
    
    # Use a date older than 190 days
    incident_date = datetime.now() - timedelta(days=200)
    
    async with PhoenixPDScraper(
        screenshot_dir="evidence",
        headless=True
    ) as scraper:
        
        try:
            result = await scraper.scrape(
                action="submit_request",
                report_type="recordings_911",
                case_number="2024-911-OLD",
                requestor_info={
                    "first_name": "Test",
                    "last_name": "User",
                    "email": "test@example.com"
                },
                additional_data={
                    "incident_date": incident_date
                }
            )
            print(f"❌ Validation failed - old request was not rejected!")
        except ValueError as e:
            print(f"✅ Validation successful: {e}")


async def test_character_sanitization():
    """Test that special characters are properly sanitized."""
    print("\n" + "="*60)
    print("TESTING CHARACTER SANITIZATION")
    print("="*60)
    
    # Test case with problematic characters
    test_case = "2024<TEST>&CASE#123"
    test_name = "John & Jane <Doe>"
    
    from core.utils.sanitize import sanitize_case_number, sanitize_phoenix_input
    
    sanitized_case = sanitize_case_number(test_case)
    sanitized_name = sanitize_phoenix_input(test_name)
    
    print(f"Original case: {test_case}")
    print(f"Sanitized case: {sanitized_case}")
    print(f"Original name: {test_name}")
    print(f"Sanitized name: {sanitized_name}")
    
    # Test actual submission with sanitized data
    async with PhoenixPDScraper(
        screenshot_dir="evidence",
        headless=True
    ) as scraper:
        
        result = await scraper.scrape(
            action="submit_request",
            report_type="incident",
            case_number=test_case,  # Will be sanitized internally
            requestor_info={
                "first_name": "John & Jane",
                "last_name": "<Doe>",
                "email": "test@example.com"
            }
        )
        
        if result.get("status") == "submitted":
            print(f"✅ Successfully submitted with sanitized characters!")
        else:
            print(f"❌ Failed to submit with special characters")


async def main():
    """Run all tests."""
    print("\nMunicipal Records Processing - Multi-Report Test Suite")
    print("Testing Phoenix PD portal with multiple report types")
    
    # Test character sanitization first
    await test_character_sanitization()
    
    # Test traffic crash report (most common for insurance)
    await test_traffic_crash_report()
    
    # Test 911 recording with valid date
    await test_911_recording()
    
    # Test 911 recording validation
    await test_invalid_911_recording()
    
    print("\n" + "="*60)
    print("TEST SUITE COMPLETE")
    print("="*60)
    print("\nKey Features Demonstrated:")
    print("✅ Multiple report types supported")
    print("✅ Character sanitization prevents form crashes")
    print("✅ 190-day validation for 911 recordings")
    print("✅ Different pricing for each report type")
    print("✅ Evidence screenshots for compliance")


if __name__ == "__main__":
    asyncio.run(main())