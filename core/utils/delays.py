"""
Human-like delay utilities for web scraping.

Provides realistic delays to avoid detection.
"""

import asyncio
import random
from typing import Union


async def human_delay(min_seconds: float = 0.5, max_seconds: float = 2.0) -> None:
    """
    Add a human-like delay between actions.
    
    Args:
        min_seconds: Minimum delay in seconds
        max_seconds: Maximum delay in seconds
    """
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)


def get_typing_delay(text: str, wpm: int = 40) -> float:
    """
    Calculate realistic typing delay based on text length.
    
    Args:
        text: Text to be typed
        wpm: Words per minute typing speed
        
    Returns:
        Delay in milliseconds per character
    """
    # Average word length is ~5 characters
    chars_per_minute = wpm * 5
    chars_per_second = chars_per_minute / 60
    ms_per_char = 1000 / chars_per_second
    
    # Add some randomness
    return ms_per_char + random.uniform(-20, 50)


async def random_micro_delay() -> None:
    """Add a small random delay between 50-150ms."""
    delay = random.uniform(0.05, 0.15)
    await asyncio.sleep(delay)


async def page_load_delay() -> None:
    """Add a delay for page loading (1-3 seconds)."""
    delay = random.uniform(1.0, 3.0)
    await asyncio.sleep(delay)


async def form_submit_delay() -> None:
    """Add a delay before form submission (0.5-1.5 seconds)."""
    delay = random.uniform(0.5, 1.5)
    await asyncio.sleep(delay)


def random_mouse_position() -> tuple[int, int]:
    """
    Generate random mouse position for more natural movement.
    
    Returns:
        Tuple of (x, y) coordinates
    """
    # Random position within typical screen bounds
    x = random.randint(100, 1200)
    y = random.randint(100, 800)
    return x, y