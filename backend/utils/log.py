
import logging

def setup_logger(name="app", level=logging.INFO):
    logger = logging.getLogger(name)
    if not logger.handlers:
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger

log = setup_logger()