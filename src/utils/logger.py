import logging
import sys

# Configure colored output if you want to keep that feature


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord):
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]
        record.msg = f"{color}{record.msg}{reset}"
        return super().format(record)


# Set up logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(
    ColorFormatter(
        "%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# Convenience functions if you want to keep the same interface


def log_debug(message: str):
    logger.debug(message)


def log_info(message: str):
    logger.info(message)


def log_warn(message: str):
    logger.warning(message)


def log_err(message: str):
    logger.error(message)
