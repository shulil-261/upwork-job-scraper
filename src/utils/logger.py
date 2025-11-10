import logging
import sys

def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)
    root = logging.getLogger()
    # Clear existing handlers to avoid duplicates in repeated runs
    root.handlers = []
    root.setLevel(level)
    root.addHandler(handler)