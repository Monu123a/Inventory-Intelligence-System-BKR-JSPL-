import logging
from logging.handlers import RotatingFileHandler
import os
import json
import time

# Ensure logs directory exists
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

metrics_logger = logging.getLogger("metrics")
metrics_logger.setLevel(logging.INFO)

# Prevent log propagation to root logger
metrics_logger.propagate = False

if not metrics_logger.handlers:
    # Max 10MB, keep 5 backups
    handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, "metrics.log"),
        maxBytes=10_000_000,
        backupCount=5
    )
    # Just write the raw message (we will format it as JSON string)
    handler.setFormatter(logging.Formatter("%(message)s"))
    metrics_logger.addHandler(handler)

def log_metric(metric_name: str, value: float = 1.0, tags: dict = None):
    """
    Non-blocking metrics logger.
    """
    try:
        if tags is None:
            tags = {}
        
        record = {
            "timestamp": int(time.time() * 1000),
            "metric": metric_name,
            "value": value,
            **tags
        }
        metrics_logger.info(json.dumps(record))
    except Exception as e:
        # Ignore metric logging failures to never block request flow
        pass
