import logging


def get_logger(name: str = "scrapper") -> logging.Logger:
    """Return a configured logger. Ensures basicConfig is set once."""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    return logging.getLogger(name)
