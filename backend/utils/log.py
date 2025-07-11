
import logging

def setup_logger(name="app", level=logging.INFO):
    '''
    Maintain a log file and append all the logs to that file
    '''

    logger = logging.getLogger(name)
    if not logger.handlers:
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
        handler = logging.FileHandler("app.log")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger

log = setup_logger()