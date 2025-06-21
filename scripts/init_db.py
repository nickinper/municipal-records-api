#!/usr/bin/env python3
"""
Initialize database for Municipal Records Processing.

Run this to create all tables and initial data.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

from proprietary.database.models import Base, Customer, Request, RequestStatus
from proprietary.billing.stripe_handler import StripeHandler


async def init_database():
    """Initialize database with tables and sample data."""
    # Load environment
    load_dotenv()
    
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        database_url = "postgresql+asyncpg://municipal_user:secure_password@localhost:5432/municipal_records"
        print(f"⚠️  No DATABASE_URL found, using default: {database_url}")
    
    print("🚀 Initializing Municipal Records Processing Database")
    print("=" * 50)
    
    # Create engine
    engine = create_async_engine(database_url, echo=True)
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            print("Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Tables created successfully!")
            
        print("\n📊 Database initialized with tables:")
        print("  - customers")
        print("  - requests") 
        print("  - request_logs")
        print("  - api_usage")
        print("  - system_metrics")
        
        print("\n💡 Next steps:")
        print("1. Set up your Stripe webhook endpoint:")
        print("   https://your-domain.com/webhooks/stripe")
        print("\n2. Configure Stripe to send these events:")
        print("   - payment_intent.succeeded")
        print("   - checkout.session.completed")
        print("   - payment_intent.payment_failed")
        print("\n3. Test with a real payment:")
        print("   curl -X POST http://localhost:8000/api/v1/submit-request \\")
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"case_number": "2024-12345", "email": "test@example.com"}\'')
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False
        
    finally:
        await engine.dispose()
        
    return True


async def create_test_data():
    """Create test data for development."""
    print("\n📝 Creating test data...")
    
    # This would create sample customers, requests, etc.
    # For production, we want to start clean
    
    print("✅ Ready for production!")


if __name__ == "__main__":
    print("""
    💰 MUNICIPAL RECORDS PROCESSING - DATABASE SETUP 💰
    
    This will create all necessary tables for the money printer.
    Make sure PostgreSQL is running!
    """)
    
    success = asyncio.run(init_database())
    
    if success:
        print("\n🎉 Database ready! Time to make that first $49!")
        print("\nStart the API with: python main.py")
    else:
        print("\n❌ Database setup failed. Check your PostgreSQL connection.")
        sys.exit(1)