
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logger(name="app", level=logging.INFO):
    '''
    Setup logger with structured JSON output for Google Cloud Logging.
    '''

    logger = logging.getLogger(name)
    if not logger.handlers:
        # Console handler for structured logging (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        
        # Use JSON formatter for Google Cloud structured logging
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s',
            timestamp=True
        )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler with JSON formatting
        file_handler = logging.FileHandler("app.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.setLevel(level)
    return logger

log = setup_logger()