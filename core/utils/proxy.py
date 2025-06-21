"""
Proxy rotation utilities for anonymity.

Supports multiple proxy providers and automatic rotation.
"""

import random
from typing import Optional, List, Dict
from urllib.parse import urlparse, urlunparse
import os


class ProxyRotator:
    """Manage proxy rotation for anonymous requests."""
    
    def __init__(self):
        """Initialize proxy rotator with configured proxies."""
        self.proxies = self._load_proxies()
        self.current_index = 0
        
    def _load_proxies(self) -> List[str]:
        """Load proxy configuration from environment."""
        proxies = []
        
        # Primary proxy from env
        primary_proxy = os.getenv("PROXY_URL")
        if primary_proxy:
            proxies.append(primary_proxy)
            
        # Load additional proxies if configured
        # Format: PROXY_URL_1, PROXY_URL_2, etc.
        for i in range(1, 10):
            proxy = os.getenv(f"PROXY_URL_{i}")
            if proxy:
                proxies.append(proxy)
                
        # Popular proxy providers configuration
        # BrightData (formerly Luminati)
        brightdata_user = os.getenv("BRIGHTDATA_USER")
        if brightdata_user:
            brightdata_pass = os.getenv("BRIGHTDATA_PASS")
            zones = ["residential", "datacenter", "mobile"]
            for zone in zones:
                proxy_url = f"http://{brightdata_user}-zone-{zone}:{brightdata_pass}@zproxy.lum-superproxy.io:22225"
                proxies.append(proxy_url)
                
        # Smartproxy
        smartproxy_user = os.getenv("SMARTPROXY_USER")
        if smartproxy_user:
            smartproxy_pass = os.getenv("SMARTPROXY_PASS")
            proxy_url = f"http://{smartproxy_user}:{smartproxy_pass}@gate.smartproxy.com:7000"
            proxies.append(proxy_url)
            
        # Oxylabs
        oxylabs_user = os.getenv("OXYLABS_USER")
        if oxylabs_user:
            oxylabs_pass = os.getenv("OXYLABS_PASS")
            proxy_url = f"http://{oxylabs_user}:{oxylabs_pass}@pr.oxylabs.io:7777"
            proxies.append(proxy_url)
            
        return proxies
        
    def get_proxy(self, strategy: str = "round_robin") -> Optional[str]:
        """
        Get next proxy based on strategy.
        
        Args:
            strategy: Rotation strategy ("round_robin", "random", "sticky")
            
        Returns:
            Proxy URL or None if no proxies configured
        """
        if not self.proxies:
            return None
            
        if strategy == "random":
            return random.choice(self.proxies)
            
        elif strategy == "round_robin":
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            return proxy
            
        elif strategy == "sticky":
            # Use same proxy for session
            return self.proxies[0]
            
        else:
            return self.proxies[0]
            
    def get_proxy_with_location(self, country: str = "US") -> Optional[str]:
        """
        Get proxy with specific country location.
        
        Args:
            country: Two-letter country code
            
        Returns:
            Proxy URL with country parameter
        """
        base_proxy = self.get_proxy()
        if not base_proxy:
            return None
            
        # Parse proxy URL
        parsed = urlparse(base_proxy)
        
        # Add country to username for providers that support it
        if "brightdata" in parsed.hostname or "luminati" in parsed.hostname:
            username = parsed.username
            if "-country-" not in username:
                username = f"{username}-country-{country.lower()}"
                
            # Reconstruct URL
            netloc = f"{username}:{parsed.password}@{parsed.hostname}:{parsed.port}"
            return urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            
        return base_proxy
        
    def get_residential_proxy(self) -> Optional[str]:
        """Get residential proxy for maximum anonymity."""
        # Prefer residential proxies
        for proxy in self.proxies:
            if "residential" in proxy or "resi" in proxy:
                return proxy
                
        # Fallback to any proxy
        return self.get_proxy()
        
    def validate_proxy(self, proxy_url: str) -> bool:
        """
        Validate proxy URL format.
        
        Args:
            proxy_url: Proxy URL to validate
            
        Returns:
            True if valid format
        """
        try:
            parsed = urlparse(proxy_url)
            return all([
                parsed.scheme in ["http", "https", "socks5"],
                parsed.hostname,
                parsed.port or parsed.scheme == "http",
                parsed.username,  # Most paid proxies require auth
                parsed.password
            ])
        except:
            return False
            
    def get_proxy_config(self) -> Dict[str, str]:
        """
        Get proxy configuration for requests/playwright.
        
        Returns:
            Dictionary with proxy configuration
        """
        proxy_url = self.get_proxy()
        if not proxy_url:
            return {}
            
        parsed = urlparse(proxy_url)
        
        return {
            "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
            "username": parsed.username,
            "password": parsed.password
        }


# Global proxy rotator instance
proxy_rotator = ProxyRotator()


def get_rotating_proxy() -> Optional[str]:
    """Get next proxy from rotation."""
    return proxy_rotator.get_proxy()


def get_us_proxy() -> Optional[str]:
    """Get US-based proxy."""
    return proxy_rotator.get_proxy_with_location("US")