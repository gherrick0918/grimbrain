import logging


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger configured with basicConfig."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    return logging.getLogger(name)
