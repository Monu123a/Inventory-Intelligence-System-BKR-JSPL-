import time
import os
import sys
import logging
import schedule
import yaml

# Add backend directory to Python path for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.amazon.pipeline import AmazonPipeline

# Configure separate logger for scheduler
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "scheduler.log")),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("amazon.scheduler")

is_running = False

def job():
    global is_running
    if is_running:
        logger.warning("Previous Amazon SP-API job is still running. Skipping this cycle.")
        return
        
    is_running = True
    try:
        logger.info("Executing scheduled Amazon SP-API job...")
        pipeline = AmazonPipeline()
        pipeline.run()
    finally:
        is_running = False

if __name__ == "__main__":
    if os.getenv("AMAZON_SYNC_ENABLED", "true").lower() != "true":
        logger.info("Amazon Sync is disabled via AMAZON_SYNC_ENABLED=false. Exiting scheduler.")
        sys.exit(0)
        
    interval = int(os.getenv("AMAZON_SYNC_INTERVAL", "30"))
    logger.info(f"Amazon SP-API Scheduler initialized. Job will run every {interval} minutes.")
    
    schedule.every(interval).minutes.do(job)
    
    # Optional: Run it immediately once on startup for debugging/testing
    if os.getenv("RUN_ON_STARTUP", "false").lower() == "true":
        logger.info("RUN_ON_STARTUP is enabled. Running job now...")
        job()

    while True:
        schedule.run_pending()
        time.sleep(60) # Sleep for a minute to save CPU
