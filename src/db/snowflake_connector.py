import logging
import time
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG = Path(__file__).resolve().parents[2] / "configs" / "error_config.yaml"


def get_active_error():
    with open(CONFIG, "r") as f:
        return yaml.safe_load(f).get("active_error", "none")


def get_snowflake_connection(max_retries=3, base_delay=2):
    """Attempt to establish a Snowflake connection with exponential back-off retry.

    Args:
        max_retries (int): Maximum number of connection attempts. Defaults to 3.
        base_delay (int): Base delay in seconds for exponential back-off. Defaults to 2.

    Returns:
        str: A mock Snowflake connection handle on success.

    Raises:
        Exception: Re-raises the last connection exception after all retries are exhausted.
    """
    logger.info("Connecting to test-account.snowflakecomputing.com")

    error = get_active_error()
    last_exc = None

    for attempt in range(1, max_retries + 1):
        try:
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

            if error == "snowflake_auth":
                raise PermissionError(
                    "390100: Incorrect username or password."
                )

            logger.info("Snowflake connection established successfully.")
            return "<mock-snowflake-connection>"

        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Connection attempt %d/%d failed: %s",
                attempt,
                max_retries,
                exc,
            )

            if attempt == max_retries:
                logger.error(
                    "All %d connection attempts failed. Raising.", max_retries
                )
                raise

            delay = base_delay * (2 ** (attempt - 1))
            logger.info(
                "Retrying in %d second(s) (attempt %d/%d)...",
                delay,
                attempt + 1,
                max_retries,
            )
            time.sleep(delay)
