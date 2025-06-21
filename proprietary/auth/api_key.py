"""
API key authentication utilities.
"""

from fastapi import HTTPException, Header
from typing import Optional


async def verify_api_key(
    api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """
    Verify API key from request header.
    
    Args:
        api_key: API key from X-API-Key header
        
    Returns:
        The verified API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Include X-API-Key header."
        )
    
    # Additional validation can be added here
    # For now, just ensure it's not empty
    if not api_key.strip():
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
        
    return api_key