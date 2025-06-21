"""
Base scraper class for web scraping operations.

Provides common functionality for all scrapers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for web scrapers."""
    
    def __init__(
        self,
        screenshot_dir: Optional[str] = None,
        proxy_url: Optional[str] = None,
        headless: bool = True,
        timeout: int = 30000
    ):
        """
        Initialize base scraper.
        
        Args:
            screenshot_dir: Directory to save screenshots
            proxy_url: Optional proxy URL
            headless: Run browser in headless mode
            timeout: Default timeout in milliseconds
        """
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else None
        self.proxy_url = proxy_url
        self.headless = headless
        self.timeout = timeout
        self.browser = None
        self.page = None
        
        # Create screenshot directory if specified
        if self.screenshot_dir:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    async def __aenter__(self):
        """Async context manager entry."""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
    
    @abstractmethod
    async def submit_request(self, *args, **kwargs) -> Dict[str, Any]:
        """Submit a request to the portal."""
        pass
    
    async def take_screenshot(self, name: str) -> Optional[str]:
        """
        Take a screenshot and save it.
        
        Args:
            name: Screenshot filename (without extension)
            
        Returns:
            Path to saved screenshot or None
        """
        if not self.page or not self.screenshot_dir:
            return None
            
        try:
            screenshot_path = self.screenshot_dir / f"{name}.png"
            await self.page.screenshot(path=str(screenshot_path))
            logger.info(f"Saved screenshot: {screenshot_path}")
            return str(screenshot_path)
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None
    
    def sanitize_filename(self, text: str) -> str:
        """
        Sanitize text for use in filenames.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized filename
        """
        # Replace problematic characters
        replacements = {
            '/': '-',
            '\\': '-',
            ':': '-',
            '*': '-',
            '?': '-',
            '"': '',
            '<': '',
            '>': '',
            '|': '-',
            ' ': '_'
        }
        
        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)
            
        # Limit length
        return result[:100]