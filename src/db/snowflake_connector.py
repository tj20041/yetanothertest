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
    logger.info(
        "Connecting to test-account.snowflakecomputing.com"
    )

    error = get_active_error()

    if error == "snowflake_auth":

        logger.info(
            "Authenticating user demo_user"
        )

        time.sleep(1)

        logger.error(
            "Authentication failed for user demo_user"
        )

        logger.error(
            "Failed to establish session with Snowflake backend"
        )

        raise Exception(
            "snowflake.connector.errors.DatabaseError: "
            "250001 (08001): Incorrect username or password was specified."
        )

    logger.info("Snowflake connection established successfully.")

    return "<mock-snowflake-connection>"
