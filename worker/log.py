
import logging

def setup_logger(name="app", level=logging.INFO):
    '''
    Maintain a log file and append all the logs to that file
    '''

    logger = logging.getLogger(name)
    if not logger.handlers:
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
        
        # File handler
        file_handler = logging.FileHandler("app.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        logger.setLevel(level)
    return logger

log = setup_logger()