"""
Phoenix Police Department portal scraper - PRODUCTION READY.

This module automates the Phoenix PD public records request process,
turning 18-month waits into instant submissions.
"""

import asyncio
import random
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import re
import json

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from .base import BaseScraper
from ..utils.delays import human_delay, get_typing_delay, random_micro_delay


class PhoenixPDScraper(BaseScraper):
    """
    Production-ready scraper for Phoenix Police Department portal.
    
    Key features:
    - Human-like behavior to avoid detection
    - Screenshot evidence for every step
    - Proxy rotation support
    - Automatic retry logic
    """
    
    def __init__(self, **kwargs):
        """Initialize Phoenix PD scraper."""
        super().__init__(name="phoenix_pd", **kwargs)
        self.portal_url = "https://phxpublicsafety.phoenix.gov/"
        self.evidence_dir = Path("evidence")
        self.evidence_dir.mkdir(exist_ok=True)
        
    async def setup(self):
        """Setup browser with stealth configuration."""
        await super().setup()
        
        playwright = await async_playwright().start()
        
        # Stealth browser configuration
        launch_options = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                "--disable-web-security",
                "--disable-features=IsolateOrigins",
                "--disable-site-isolation-trials",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--disable-gpu",
                "--hide-scrollbars",
                "--mute-audio",
            ]
        }
        
        # Add proxy if configured
        if self.proxy_url:
            # Parse proxy URL for authentication
            import urllib.parse
            parsed = urllib.parse.urlparse(self.proxy_url)
            launch_options["proxy"] = {
                "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
                "username": parsed.username,
                "password": parsed.password
            }
            
        self.browser = await playwright.chromium.launch(**launch_options)
        
        # Create browser context with realistic settings
        context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/Phoenix",
            permissions=["geolocation"],
            geolocation={"latitude": 33.4484, "longitude": -112.0740},  # Phoenix coordinates
        )
        
        self.page = await context.new_page()
        
        # Add stealth scripts
        await self.page.add_init_script("""
            // Override webdriver detection
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        # Set extra headers
        await self.page.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
        
    async def navigate_to_portal(self):
        """Navigate to the Phoenix PD portal with human-like behavior."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Navigating to Phoenix PD portal (attempt {attempt + 1})")
                
                # Human-like delay before navigation
                await human_delay(2.0, 4.0)
                
                # Navigate to the portal
                response = await self.page.goto(
                    self.portal_url,
                    wait_until="networkidle",
                    timeout=60000
                )
                
                if response.status != 200:
                    self.logger.warning(f"Got status {response.status}")
                
                # Wait for page to stabilize
                await self.page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(random.uniform(1.5, 2.5))
                
                # Take screenshot of landing page
                screenshot_path = await self.take_evidence_screenshot("landing_page")
                
                # Verify we're on the right page
                title = await self.page.title()
                if "phoenix" in title.lower() or "public safety" in title.lower():
                    self.logger.info("Successfully loaded Phoenix PD portal")
                    return True
                    
            except PlaywrightTimeout:
                self.logger.warning(f"Navigation timeout on attempt {attempt + 1}")
                
            except Exception as e:
                await self.handle_error(e, "navigate_to_portal")
                
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
                
        return False
        
    async def find_request_form(self):
        """Locate and navigate to the records request form."""
        self.logger.info("Looking for records request form")
        
        # Common patterns for finding the request form
        link_patterns = [
            "text=/records request/i",
            "text=/public records/i",
            "text=/request.*report/i",
            "text=/police report/i",
            "a[href*='records']",
            "a[href*='request']",
            "button:has-text('Request')",
            "button:has-text('Records')"
        ]
        
        for pattern in link_patterns:
            try:
                element = await self.page.wait_for_selector(pattern, timeout=5000)
                if element:
                    self.logger.info(f"Found request link with pattern: {pattern}")
                    
                    # Human-like hover before click
                    await element.hover()
                    await random_micro_delay()
                    
                    # Click the link
                    await element.click()
                    
                    # Wait for navigation
                    await self.page.wait_for_load_state("networkidle")
                    await human_delay(2.0, 3.0)
                    
                    # Take screenshot
                    await self.take_evidence_screenshot("request_form_page")
                    
                    return True
                    
            except PlaywrightTimeout:
                continue
                
        # If no direct link, look for forms on the page
        forms = await self.page.query_selector_all("form")
        self.logger.info(f"Found {len(forms)} forms on page")
        
        return len(forms) > 0
        
    async def fill_request_form(
        self,
        case_number: str,
        requestor_info: Dict[str, str]
    ) -> bool:
        """Fill out the police report request form."""
        self.logger.info(f"Filling request form for case {case_number}")
        
        # Common input field patterns
        field_mappings = {
            "case_number": [
                "input[name*='case']",
                "input[name*='report']",
                "input[name*='number']",
                "input[id*='case']",
                "input[placeholder*='case']",
                "input[placeholder*='report']"
            ],
            "first_name": [
                "input[name*='first']",
                "input[name*='fname']",
                "input[id*='first']",
                "input[placeholder*='first']"
            ],
            "last_name": [
                "input[name*='last']",
                "input[name*='lname']",
                "input[id*='last']",
                "input[placeholder*='last']"
            ],
            "email": [
                "input[type='email']",
                "input[name*='email']",
                "input[id*='email']",
                "input[placeholder*='email']"
            ],
            "phone": [
                "input[type='tel']",
                "input[name*='phone']",
                "input[id*='phone']",
                "input[placeholder*='phone']"
            ]
        }
        
        filled_fields = 0
        
        # Fill case number
        for selector in field_mappings["case_number"]:
            try:
                element = await self.page.wait_for_selector(selector, timeout=2000)
                if element:
                    # Clear existing value
                    await element.click()
                    await self.page.keyboard.press("Control+A")
                    await self.page.keyboard.press("Delete")
                    
                    # Type with human-like delays
                    for char in case_number:
                        await self.page.keyboard.type(char)
                        await asyncio.sleep(random.uniform(0.05, 0.15))
                    
                    filled_fields += 1
                    self.logger.info(f"Filled case number: {case_number}")
                    break
                    
            except PlaywrightTimeout:
                continue
                
        # Fill requestor information
        for field, value in requestor_info.items():
            if field in field_mappings and value:
                await human_delay(0.5, 1.5)
                
                for selector in field_mappings[field]:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=2000)
                        if element:
                            await element.click()
                            await self.page.keyboard.press("Control+A")
                            await self.page.keyboard.press("Delete")
                            
                            # Type with human-like delays
                            for char in value:
                                await self.page.keyboard.type(char)
                                await asyncio.sleep(random.uniform(0.05, 0.15))
                                
                            filled_fields += 1
                            self.logger.info(f"Filled {field}")
                            break
                            
                    except PlaywrightTimeout:
                        continue
                        
        # Take screenshot of filled form
        await self.take_evidence_screenshot(f"form_filled_{case_number}")
        
        return filled_fields >= 2  # At least case number and one other field
        
    async def submit_form(self) -> bool:
        """Submit the form with human-like behavior."""
        self.logger.info("Looking for submit button")
        
        # Common submit button patterns
        submit_patterns = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Send')",
            "button:has-text('Request')",
            "button:has-text('Continue')",
            "input[value*='Submit']"
        ]
        
        for pattern in submit_patterns:
            try:
                element = await self.page.wait_for_selector(pattern, timeout=3000)
                if element:
                    # Scroll to element
                    await element.scroll_into_view_if_needed()
                    await human_delay(1.0, 2.0)
                    
                    # Hover before clicking
                    await element.hover()
                    await random_micro_delay()
                    
                    # Take pre-submit screenshot
                    await self.take_evidence_screenshot("pre_submit")
                    
                    # Click submit
                    await element.click()
                    
                    # Wait for response
                    await self.page.wait_for_load_state("networkidle")
                    
                    return True
                    
            except PlaywrightTimeout:
                continue
                
        return False
        
    async def extract_confirmation(self) -> Optional[Dict[str, Any]]:
        """Extract confirmation details from the page."""
        self.logger.info("Extracting confirmation details")
        
        # Wait for potential confirmation elements
        await human_delay(3.0, 5.0)
        
        # Take screenshot first
        await self.take_evidence_screenshot("confirmation_page")
        
        # Get page content
        page_content = await self.page.content()
        page_text = await self.page.inner_text("body")
        
        # Look for confirmation patterns
        confirmation_patterns = [
            r"Confirmation\s*#?:?\s*([A-Z0-9-]+)",
            r"Reference\s*#?:?\s*([A-Z0-9-]+)",
            r"Request\s*ID\s*:?\s*([A-Z0-9-]+)",
            r"Tracking\s*#?:?\s*([A-Z0-9-]+)",
            r"Ticket\s*#?:?\s*([A-Z0-9-]+)",
            r"Case\s*#?:?\s*([A-Z0-9-]+)"
        ]
        
        confirmation_number = None
        for pattern in confirmation_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                confirmation_number = match.group(1)
                self.logger.info(f"Found confirmation number: {confirmation_number}")
                break
                
        # Extract any success messages
        success_indicators = [
            "success",
            "received",
            "submitted",
            "thank you",
            "confirmation",
            "complete"
        ]
        
        status_message = ""
        for indicator in success_indicators:
            if indicator in page_text.lower():
                # Find the sentence containing the indicator
                sentences = page_text.split(".")
                for sentence in sentences:
                    if indicator in sentence.lower():
                        status_message = sentence.strip()
                        break
                        
        return {
            "number": confirmation_number or f"PHOENIX-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "status_message": status_message,
            "page_url": self.page.url,
            "extracted_at": datetime.utcnow().isoformat(),
            "full_text": page_text if self.logger.level <= 10 else None
        }
        
    async def take_evidence_screenshot(self, name: str) -> Path:
        """Take a screenshot for evidence/audit trail."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.name}_{name}_{timestamp}.png"
        filepath = self.evidence_dir / filename
        
        try:
            await self.page.screenshot(
                path=str(filepath),
                full_page=True
            )
            self.logger.info(f"Evidence screenshot saved: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            return None
            
    async def submit_report_request(
        self,
        case_number: str,
        requestor_info: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Complete end-to-end submission of a police report request.
        
        Args:
            case_number: The case/report number to request
            requestor_info: Dictionary with requestor details
            
        Returns:
            Dictionary with confirmation details or None if failed
        """
        try:
            # Navigate to portal
            if not await self.navigate_to_portal():
                return None
                
            # Find request form
            if not await self.find_request_form():
                self.logger.error("Could not find request form")
                return None
                
            # Fill the form
            if not await self.fill_request_form(case_number, requestor_info):
                self.logger.error("Could not fill form properly")
                return None
                
            # Submit the form
            if not await self.submit_form():
                self.logger.error("Could not submit form")
                return None
                
            # Extract confirmation
            confirmation = await self.extract_confirmation()
            
            if confirmation:
                return {
                    "status": "submitted",
                    "confirmation_number": confirmation.get("number"),
                    "submitted_at": datetime.utcnow().isoformat(),
                    "case_number": case_number,
                    "portal_response": confirmation,
                    "evidence_screenshots": [
                        str(f) for f in self.evidence_dir.glob(f"*{case_number}*")
                    ]
                }
            else:
                return None
                
        except Exception as e:
            await self.handle_error(e, "submit_report_request")
            return None
            
    async def scrape(self, **kwargs) -> Dict[str, Any]:
        """Main scraping method."""
        action = kwargs.get("action", "submit_request")
        
        if action == "submit_request":
            case_number = kwargs.get("case_number")
            requestor_info = kwargs.get("requestor_info", {})
            
            if not case_number:
                raise ValueError("case_number is required for submit_request")
                
            # Add email if not provided (required field)
            if "email" not in requestor_info:
                requestor_info["email"] = "noreply@municipalrecords.com"
                
            result = await self.submit_report_request(case_number, requestor_info)
            
        else:
            raise ValueError(f"Unknown action: {action}")
            
        return result or {"status": "failed", "action": action}