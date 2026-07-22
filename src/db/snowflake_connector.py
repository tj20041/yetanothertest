import logging
import time
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG = Path(__file__).resolve().parents[2] / "configs" / "error_config.yaml"


def get_active_error():
    with open(CONFIG, "r") as f:
        return yaml.safe_load(f).get("active_error", "none")


def get_snowflake_connection():

    logger.info(
        "Connecting to test-account.snowflakecomputing.com"
    )

    error = get_active_error()

    if error == "snowflake_dns":

        time.sleep(1)

        logger.error(
            "Failed to resolve host test-account.snowflakecomputing.com"
        )

        logger.error(
            "Failed to establish session with Snowflake backend"
        )

        raise Exception(
            "snowflake.connector.errors.OperationalError: "
            "250001: Could not connect to Snowflake backend."
        )

    logger.info("Snowflake connection established successfully.")

    return "<mock-snowflake-connection>"
