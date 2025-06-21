"""
Background worker for processing police record requests.

This worker handles the automated submission of requests to Phoenix PD
after payment confirmation.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import redis.asyncio as redis
from dotenv import load_dotenv
import os

from proprietary.database.models import Request, RequestLog, RequestStatus, Customer
from core.scrapers.phoenix_pd import PhoenixPDScraper
from core.utils.delays import human_delay


# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RequestProcessor:
    """Process pending requests by submitting them to Phoenix PD."""
    
    def __init__(self):
        """Initialize the processor."""
        self.engine = None
        self.async_session = None
        self.redis_client = None
        self.running = False
        
    async def setup(self):
        """Set up database and Redis connections."""
        # Database
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
            
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = await redis.from_url(redis_url, decode_responses=True)
        
        logger.info("Request processor initialized")
        
    async def cleanup(self):
        """Clean up connections."""
        if self.redis_client:
            await self.redis_client.close()
        if self.engine:
            await self.engine.dispose()
            
    async def process_request(self, request: Request, session: AsyncSession):
        """
        Process a single request by submitting it to Phoenix PD.
        
        Args:
            request: The request to process
            session: Database session
        """
        try:
            logger.info(f"Processing request {request.id} for case {request.case_number}")
            
            # Create scraper instance
            screenshot_dir = os.getenv("SCREENSHOT_DIR", "./screenshots")
            proxy_url = os.getenv("PROXY_URL")
            
            async with PhoenixPDScraper(
                screenshot_dir=screenshot_dir,
                proxy_url=proxy_url,
                headless=True
            ) as scraper:
                # Prepare requestor info
                requestor_info = {
                    "email": request.requestor_email,
                }
                
                if request.requestor_first_name:
                    requestor_info["first_name"] = request.requestor_first_name
                if request.requestor_last_name:
                    requestor_info["last_name"] = request.requestor_last_name
                if request.requestor_phone:
                    requestor_info["phone"] = request.requestor_phone
                    
                # Submit the request
                result = await scraper.submit_report_request(
                    case_number=request.case_number,
                    requestor_info=requestor_info
                )
                
                if result and result.get("status") == "submitted":
                    # Update request status
                    request.status = RequestStatus.SUBMITTED
                    request.phoenix_confirmation = result.get("confirmation_number")
                    request.submitted_to_portal_at = datetime.utcnow()
                    
                    # Log success
                    log_entry = RequestLog(
                        request_id=request.id,
                        action="submitted_to_phoenix",
                        details=f"Confirmation: {result.get('confirmation_number')}",
                        screenshot_path=str(result.get("screenshot_path", ""))
                    )
                    session.add(log_entry)
                    
                    logger.info(f"Successfully submitted request {request.id}")
                    
                    # Send notification email (TODO: implement email service)
                    # await send_submission_notification(request)
                    
                else:
                    # Submission failed
                    request.retry_count += 1
                    request.last_retry_at = datetime.utcnow()
                    
                    if request.retry_count >= 3:
                        request.status = RequestStatus.FAILED
                        request.failed_at = datetime.utcnow()
                        request.failure_reason = "Failed after 3 attempts"
                        
                        # Log failure
                        log_entry = RequestLog(
                            request_id=request.id,
                            action="submission_failed",
                            details="Max retries exceeded",
                            is_error=True
                        )
                        session.add(log_entry)
                        
                        # TODO: Trigger refund process
                        logger.error(f"Request {request.id} failed after max retries")
                    else:
                        # Will retry
                        log_entry = RequestLog(
                            request_id=request.id,
                            action="submission_retry",
                            details=f"Retry {request.retry_count} of 3",
                            is_error=True
                        )
                        session.add(log_entry)
                        
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error processing request {request.id}: {str(e)}")
            
            # Log error
            log_entry = RequestLog(
                request_id=request.id,
                action="processing_error",
                details=str(e),
                is_error=True,
                error_message=str(e)
            )
            session.add(log_entry)
            
            # Update retry count
            request.retry_count += 1
            request.last_retry_at = datetime.utcnow()
            
            if request.retry_count >= 3:
                request.status = RequestStatus.FAILED
                request.failed_at = datetime.utcnow()
                request.failure_reason = f"Processing error: {str(e)}"
                
            await session.commit()
            
    async def check_request_status(self, request: Request, session: AsyncSession):
        """
        Check the status of a submitted request.
        
        Args:
            request: The request to check
            session: Database session
        """
        if not request.phoenix_confirmation:
            logger.warning(f"Request {request.id} has no confirmation number")
            return
            
        try:
            async with PhoenixPDScraper(headless=True) as scraper:
                result = await scraper.check_request_status(
                    confirmation_number=request.phoenix_confirmation
                )
                
                if result:
                    status = result.get("status", "unknown")
                    
                    if status == "completed":
                        request.status = RequestStatus.COMPLETED
                        request.completed_at = datetime.utcnow()
                        
                        # Log completion
                        log_entry = RequestLog(
                            request_id=request.id,
                            action="request_completed",
                            details="Records ready for download"
                        )
                        session.add(log_entry)
                        
                        # TODO: Download records and notify customer
                        
                    elif status == "processing":
                        request.status = RequestStatus.PROCESSING
                        
                    # Log status check
                    log_entry = RequestLog(
                        request_id=request.id,
                        action="status_checked",
                        details=f"Status: {status}"
                    )
                    session.add(log_entry)
                    
                    await session.commit()
                    
        except Exception as e:
            logger.error(f"Error checking status for request {request.id}: {str(e)}")
            
    async def get_pending_requests(self, session: AsyncSession):
        """Get requests that need processing."""
        # Get payment received requests that haven't been submitted
        result = await session.execute(
            select(Request).where(
                and_(
                    Request.status == RequestStatus.PAYMENT_RECEIVED,
                    Request.retry_count < 3
                )
            ).limit(10)
        )
        return result.scalars().all()
        
    async def get_submitted_requests(self, session: AsyncSession):
        """Get submitted requests that need status checks."""
        # Check requests submitted more than 1 hour ago
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        result = await session.execute(
            select(Request).where(
                and_(
                    Request.status.in_([RequestStatus.SUBMITTED, RequestStatus.PROCESSING]),
                    Request.submitted_to_portal_at < one_hour_ago
                )
            ).limit(20)
        )
        return result.scalars().all()
        
    async def process_loop(self):
        """Main processing loop."""
        self.running = True
        
        while self.running:
            try:
                async with self.async_session() as session:
                    # Process new requests
                    pending_requests = await self.get_pending_requests(session)
                    
                    for request in pending_requests:
                        # Check rate limits
                        current_hour = datetime.utcnow().strftime("%Y%m%d%H")
                        rate_key = f"worker:requests:{current_hour}"
                        
                        count = await self.redis_client.incr(rate_key)
                        if count == 1:
                            await self.redis_client.expire(rate_key, 3600)
                            
                        # Respect rate limit (10 per hour)
                        if count > 10:
                            logger.warning("Rate limit reached for this hour")
                            break
                            
                        # Process the request
                        await self.process_request(request, session)
                        
                        # Human-like delay between submissions
                        await human_delay(30, 90)
                        
                    # Check status of submitted requests
                    submitted_requests = await self.get_submitted_requests(session)
                    
                    for request in submitted_requests:
                        await self.check_request_status(request, session)
                        await human_delay(5, 15)
                        
                # Sleep before next iteration
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in process loop: {str(e)}")
                await asyncio.sleep(60)
                
    async def run(self):
        """Run the worker."""
        await self.setup()
        
        try:
            logger.info("Starting request processor")
            await self.process_loop()
        except KeyboardInterrupt:
            logger.info("Shutting down request processor")
        finally:
            self.running = False
            await self.cleanup()


async def main():
    """Main entry point."""
    processor = RequestProcessor()
    await processor.run()


if __name__ == "__main__":
    asyncio.run(main())