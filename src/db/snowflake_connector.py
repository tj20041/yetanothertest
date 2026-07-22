import logging
import os
import time
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG = Path(__file__).resolve().parents[2] / "configs" / "error_config.yaml"

# Snowflake connection parameters — override via environment variables
# SNOWFLAKE_ACCOUNT: the account identifier used to build the hostname
#   e.g. export SNOWFLAKE_ACCOUNT=my-account
#   resolves to my-account.snowflakecomputing.com
_DEFAULT_ACCOUNT = "test-account"
SNOWFLAKE_ACCOUNT = os.environ.get("SNOWFLAKE_ACCOUNT", _DEFAULT_ACCOUNT)

# Retry configuration
_MAX_RETRIES = 3
_RETRY_BASE_DELAY_SECONDS = 1  # exponential backoff: 1s, 2s, 4s


def get_active_error() -> str:
    """Read the currently active synthetic error from the config file."""
    with open(CONFIG, "r") as f:
        return yaml.safe_load(f).get("active_error", "none")


def _attempt_snowflake_connection(account: str) -> str:
    """
    Attempt a single connection to Snowflake.

    In production this would call snowflake.connector.connect().
    Here we simulate the behaviour driven by the error config.

    Parameters
    ----------
    account:
        The Snowflake account identifier (hostname prefix).

    Returns
    -------
    str
        A mock connection handle on success.

    Raises
    ------
    Exception
        Propagates any Snowflake-level operational errors.
    """
    host = f"{account}.snowflakecomputing.com"
    logger.info("Attempting Snowflake connection to %s", host)

    error = get_active_error()

    if error == "snowflake_dns":
        logger.error("Failed to resolve host %s", host)
        logger.error("Failed to establish session with Snowflake backend")
        raise Exception(
            "snowflake.connector.errors.OperationalError: "
            "250001: Could not connect to Snowflake backend."
        )

    if error == "snowflake_timeout":
        raise TimeoutError(
            "250001: Could not connect to Snowflake backend after 1 second."
        )

    if error == "snowflake_auth":
        raise PermissionError("390100: Incorrect username or password.")

    return "<mock-snowflake-connection>"


def get_snowflake_connection() -> str:
    """
    Establish a connection to Snowflake with retry logic and exponential backoff.

    The Snowflake account identifier is read from the ``SNOWFLAKE_ACCOUNT``
    environment variable (defaults to ``test-account`` when not set).

    Retries up to ``_MAX_RETRIES`` times on transient network/DNS errors,
    doubling the wait interval between each attempt.

    Returns
    -------
    str
        A connection handle (real snowflake.connector.SnowflakeConnection in
        production; a mock string in this demo).

    Raises
    ------
    Exception
        Re-raises the last exception after all retry attempts are exhausted,
        or immediately for non-retriable errors (auth failures).
    """
    account = SNOWFLAKE_ACCOUNT
    host = f"{account}.snowflakecomputing.com"
    logger.info("Opening Snowflake connection (account=%s, host=%s)", account, host)

    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            conn = _attempt_snowflake_connection(account)
            logger.info("Snowflake connection established successfully on attempt %d.", attempt)
            return conn

        except PermissionError:
            # Auth errors are not transient — fail immediately
            logger.error(
                "Snowflake authentication failed. "
                "Check SNOWFLAKE_USER / SNOWFLAKE_PASSWORD credentials."
            )
            raise

        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < _MAX_RETRIES:
                delay = _RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "Snowflake connection attempt %d/%d failed: %s. "
                    "Retrying in %ds...",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                    delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "Snowflake connection failed after %d attempts. "
                    "Verify DNS resolution for %s and check network connectivity. "
                    "Last error: %s",
                    _MAX_RETRIES,
                    host,
                    exc,
                )

    raise last_exc
