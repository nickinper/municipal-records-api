#!/usr/bin/env python3
"""
Test the Phoenix PD scraper to ensure it works.

Run this to verify the scraper can navigate and detect forms.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.scrapers.phoenix_pd import PhoenixPDScraper


async def test_phoenix_scraper():
    """Test the Phoenix PD scraper functionality."""
    print("🧪 Testing Phoenix PD Scraper")
    print("=" * 50)
    
    # Test case number (use a real one for actual testing)
    test_case = "2024-TEST-001"
    test_email = "test@municipalrecords.com"
    
    print(f"\n📋 Test Details:")
    print(f"  Case Number: {test_case}")
    print(f"  Email: {test_email}")
    print(f"  Mode: Headless browser")
    
    try:
        # Initialize scraper
        async with PhoenixPDScraper(
            screenshot_dir="evidence",
            headless=True  # Set to False to watch it work!
        ) as scraper:
            
            print("\n🌐 Navigating to Phoenix PD portal...")
            success = await scraper.navigate_to_portal()
            
            if success:
                print("✅ Successfully loaded portal")
                
                print("\n🔍 Looking for request form...")
                form_found = await scraper.find_request_form()
                
                if form_found:
                    print("✅ Found request form/link")
                    
                    # Check what's on the page
                    page_title = await scraper.page.title()
                    page_url = scraper.page.url
                    
                    print(f"\n📄 Current Page:")
                    print(f"  Title: {page_title}")
                    print(f"  URL: {page_url}")
                    
                    # Count forms and inputs
                    forms = await scraper.page.query_selector_all("form")
                    inputs = await scraper.page.query_selector_all("input")
                    buttons = await scraper.page.query_selector_all("button")
                    
                    print(f"\n📊 Page Analysis:")
                    print(f"  Forms found: {len(forms)}")
                    print(f"  Input fields: {len(inputs)}")
                    print(f"  Buttons: {len(buttons)}")
                    
                    # Look for specific indicators
                    print("\n🔎 Looking for key elements...")
                    
                    # Check for case number input
                    case_inputs = await scraper.page.query_selector_all(
                        "input[name*='case'], input[placeholder*='case'], input[id*='case']"
                    )
                    print(f"  Case number inputs: {len(case_inputs)}")
                    
                    # Check for email input
                    email_inputs = await scraper.page.query_selector_all(
                        "input[type='email'], input[name*='email']"
                    )
                    print(f"  Email inputs: {len(email_inputs)}")
                    
                    # Check for submit buttons
                    submit_buttons = await scraper.page.query_selector_all(
                        "button[type='submit'], input[type='submit'], button:has-text('Submit')"
                    )
                    print(f"  Submit buttons: {len(submit_buttons)}")
                    
                    print("\n📸 Screenshots saved in 'evidence' directory")
                    
                else:
                    print("❌ Could not find request form")
                    print("   The portal structure may have changed")
                    
            else:
                print("❌ Failed to load portal")
                print("   Check internet connection and proxy settings")
                
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n" + "=" * 50)
    print("Test complete! Check 'evidence' directory for screenshots.")


async def test_full_submission():
    """Test full form submission (BE CAREFUL - this submits a real request!)."""
    print("\n⚠️  WARNING: This will submit a REAL request to Phoenix PD!")
    response = input("Are you sure you want to continue? (type 'yes' to proceed): ")
    
    if response.lower() != 'yes':
        print("Test cancelled.")
        return
        
    # Use a real case number for testing
    case_number = input("Enter a REAL case number to test with: ")
    email = input("Enter email for confirmation: ")
    
    requestor_info = {
        "email": email,
        "first_name": "Test",
        "last_name": "User"
    }
    
    try:
        async with PhoenixPDScraper(headless=False) as scraper:
            result = await scraper.submit_report_request(
                case_number=case_number,
                requestor_info=requestor_info
            )
            
            if result and result.get("status") == "submitted":
                print(f"\n✅ SUCCESS! Request submitted")
                print(f"Confirmation: {result.get('confirmation_number')}")
            else:
                print(f"\n❌ Submission failed")
                print(f"Result: {result}")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    print("""
    🚀 PHOENIX PD SCRAPER TEST
    
    This will test the scraper's ability to:
    1. Navigate to the Phoenix PD portal
    2. Find the request form
    3. Analyze the page structure
    
    No real requests will be submitted in basic test.
    """)
    
    asyncio.run(test_phoenix_scraper())
    
    print("\n" + "=" * 50)
    print("💡 To test full submission (REAL request), run:")
    print("   python scripts/test_scraper.py --full")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        asyncio.run(test_full_submission())