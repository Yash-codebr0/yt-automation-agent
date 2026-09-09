import logging
import uuid
import sys
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "filename": record.filename,
            "line": record.lineno
        }
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)
            if not hasattr(record, "error_id"):
                record.error_id = f"ERR-{uuid.uuid4().hex[:8].upper()}"
        
        if hasattr(record, "error_id"):
            log_data["error_id"] = record.error_id
            
        return json.dumps(log_data)

def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)

def log_error_with_id(logger, message, exc=None):
    """Logs an error with a generated unique error ID and returns it."""
    error_id = f"ERR-{uuid.uuid4().hex[:8].upper()}"
    extra = {"error_id": error_id}
    if exc:
        logger.error(f"{message} (Error ID: {error_id})", exc_info=exc, extra=extra)
    else:
        logger.error(f"{message} (Error ID: {error_id})", extra=extra)
    return error_id
