import logging
import time
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG = Path(__file__).resolve().parents[2] / "configs" / "error_config.yaml"


def get_active_error():
    with open(CONFIG) as f:
        return yaml.safe_load(f).get("active_error", "none")


def get_snowflake_connection():
    logger.info("Initializing Snowflake connection...")

    error = get_active_error()

    if error == "snowflake_timeout":
        logger.info("Connecting to Snowflake account...")

        time.sleep(2)

        logger.error(
            "Connection to Snowflake timed out after waiting for server response."
        )

        raise TimeoutError(
            "250001: Could not connect to Snowflake backend after 2 second(s). "
            "Verify network connectivity and account endpoint."
        )

    logger.info("Snowflake connection established successfully.")

    return "<mock-snowflake-connection>"
