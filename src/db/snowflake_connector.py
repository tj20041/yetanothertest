import logging
import time
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG = Path(__file__).resolve().parents[2] / "configs" / "error_config.yaml"


def get_active_error():
    """Read the active_error flag from the error configuration file.

    Returns:
        str: The active error key, or 'none' if not set.
    """
    with open(CONFIG) as f:
        return yaml.safe_load(f).get("active_error", "none")


def get_snowflake_connection():
    """Establish (or simulate) a Snowflake connection.

    Reads the active_error config flag and raises the appropriate
    simulated exception when a non-'none' value is configured.  In
    normal operation (active_error == 'none') the function returns a
    mock connection object that stands in for a real
    snowflake.connector connection.

    Returns:
        str: Mock connection handle when no error is active.

    Raises:
        TimeoutError: When active_error == 'snowflake_timeout'.
        PermissionError: When active_error == 'snowflake_auth'.
    """
    logger.info("Connecting to test-account.snowflakecomputing.com")

    error = get_active_error()

    if error == "snowflake_timeout":
        logger.error(
            "Could not connect to Snowflake backend after 1 second."
        )
        raise TimeoutError(
            "250001: Could not connect to Snowflake backend after 1 second."
        )

    if error == "snowflake_auth":
        logger.info("Authenticating user demo_user")
        time.sleep(1)
        logger.error("Authentication failed for user demo_user")
        logger.error(
            "Failed to establish session with Snowflake backend"
        )
        raise PermissionError(
            "390100: Incorrect username or password was specified "
            "for user demo_user."
        )

    logger.info("Snowflake connection established successfully.")
    return "<mock-snowflake-connection>"
