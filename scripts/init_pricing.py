#!/usr/bin/env python3
"""
Initialize report pricing in the database.

This script sets up the pricing structure for all Phoenix PD report types.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from proprietary.database.models import Base, ReportPricing, initialize_pricing
from proprietary.config import Settings

# Load settings
settings = Settings()


async def init_pricing_data():
    """Initialize the pricing data in the database."""
    # Create async engine
    engine = create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    
    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with engine.begin() as conn:
        print("Creating tables if they don't exist...")
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        # Check if pricing already exists
        from sqlalchemy import select
        result = await session.execute(select(ReportPricing))
        existing = result.scalars().all()
        
        if existing:
            print(f"Found {len(existing)} existing pricing records.")
            print("Skipping initialization to avoid duplicates.")
            return
        
        print("Initializing pricing data...")
        
        # Get default pricing
        pricing_records = initialize_pricing()
        
        # Add all pricing records
        for record in pricing_records:
            session.add(record)
            print(f"Added pricing for {record.display_name}: "
                  f"${record.base_fee} base + ${record.standard_fee} service")
        
        await session.commit()
        print(f"Successfully initialized {len(pricing_records)} pricing records!")
        
        # Display pricing summary
        print("\n" + "="*60)
        print("PRICING SUMMARY - SIMPLE VOLUME-BASED PRICING")
        print("="*60)
        print(f"{'Report Type':<30} {'PD Fee':<10} {'Our Fee':<10} {'Total':<10}")
        print("-"*60)
        
        for record in pricing_records:
            total = record.base_fee + record.service_fee
            print(f"{record.display_name:<30} ${record.base_fee:<9.2f} ${record.service_fee:<9.2f} ${total:<9.2f}")
        
        print("="*60)
        print("\nAUTOMATIC VOLUME DISCOUNTS:")
        print("  1-10 reports:  $49 each (no discount)")
        print("  11-50 reports: $39.20 each (20% off)")
        print("  51+ reports:   $29.40 each (40% off)")
        print("\nNo contracts. No monthly fees. Discounts apply automatically.")
        print("="*60)
    
    await engine.dispose()


if __name__ == "__main__":
    print("Municipal Records Processing - Pricing Initialization")
    print("="*50)
    
    asyncio.run(init_pricing_data())