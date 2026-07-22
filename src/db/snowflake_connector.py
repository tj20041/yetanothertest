import logging
import os
import time
import yaml
from pathlib import Path

try:
    import snowflake.connector
except ImportError:
    snowflake = None  # type: ignore

logger = logging.getLogger(__name__)

CONFIG = Path(__file__).resolve().parents[2] / "configs" / "error_config.yaml"

# Retry configuration
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 2
_NETWORK_TIMEOUT_SECONDS = 30


def get_active_error():
    """Read the active error scenario from the config file."""
    with open(CONFIG) as f:
        return yaml.safe_load(f).get("active_error", "none")


def get_snowflake_connection():
    """
    Establish and return a real Snowflake connection using the
    snowflake-connector-python library.

    Connection parameters are read from environment variables:
        SNOWFLAKE_ACCOUNT   — Snowflake account identifier (required)
        SNOWFLAKE_USER      — Snowflake username (required)
        SNOWFLAKE_PASSWORD  — Snowflake user password (required)
        SNOWFLAKE_WAREHOUSE — Virtual warehouse to use (optional)
        SNOWFLAKE_DATABASE  — Default database (optional)
        SNOWFLAKE_SCHEMA    — Default schema (optional)
        SNOWFLAKE_ROLE      — Role to assume (optional)

    Raises:
        TimeoutError:    when active_error == 'snowflake_timeout' (test injection)
        PermissionError: when active_error == 'snowflake_auth'    (test injection)
        RuntimeError:    when snowflake-connector-python is not installed
        Exception:       when the real connection attempt fails after all retries
    """
    logger.info("Initializing Snowflake connection...")

    # ------------------------------------------------------------------ #
    # Simulated error injection (for pipeline testing only)               #
    # Controlled via configs/error_config.yaml -> active_error            #
    # ------------------------------------------------------------------ #
    active_error = get_active_error()

    if active_error == "snowflake_timeout":
        logger.info("[TEST MODE] Simulating Snowflake connection timeout...")
        time.sleep(2)
        logger.error(
            "[TEST MODE] Connection to Snowflake timed out after waiting "
            "for server response."
        )
        raise TimeoutError(
            "250001: Could not connect to Snowflake backend after 2 second(s). "
            "Verify network connectivity and account endpoint."
        )

    if active_error == "snowflake_auth":
        logger.error(
            "[TEST MODE] Authentication failed for Snowflake connection."
        )
        raise PermissionError(
            "390100: Incorrect username or password was specified."
        )

    # ------------------------------------------------------------------ #
    # Real connection using snowflake-connector-python                    #
    # ------------------------------------------------------------------ #
    if snowflake is None:
        raise RuntimeError(
            "snowflake-connector-python is not installed. "
            "Run: pip install snowflake-connector-python"
        )

    account = os.environ.get("SNOWFLAKE_ACCOUNT", "")
    user = os.environ.get("SNOWFLAKE_USER", "")
    password = os.environ.get("SNOWFLAKE_PASSWORD", "")

    if not account or not user or not password:
        raise ValueError(
            "Missing required Snowflake credentials. "
            "Set environment variables: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, "
            "SNOWFLAKE_PASSWORD."
        )

    connect_kwargs = {
        "account": account,
        "user": user,
        "password": password,
        "network_timeout": _NETWORK_TIMEOUT_SECONDS,
    }

    # Optional parameters — only passed when explicitly set
    optional_params = {
        "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE"),
        "database": os.environ.get("SNOWFLAKE_DATABASE"),
        "schema": os.environ.get("SNOWFLAKE_SCHEMA"),
        "role": os.environ.get("SNOWFLAKE_ROLE"),
    }
    connect_kwargs.update(
        {k: v for k, v in optional_params.items() if v is not None}
    )

    last_exception = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            logger.info(
                "Connecting to Snowflake (attempt %d/%d), account=%s, user=%s",
                attempt,
                _MAX_RETRIES,
                account,
                user,
            )
            conn = snowflake.connector.connect(**connect_kwargs)
            logger.info(
                "Snowflake connection established successfully on attempt %d.",
                attempt,
            )
            return conn

        except snowflake.connector.errors.OperationalError as exc:
            last_exception = exc
            logger.warning(
                "Snowflake connection attempt %d/%d failed (OperationalError): %s",
                attempt,
                _MAX_RETRIES,
                exc,
            )

        except snowflake.connector.errors.DatabaseError as exc:
            last_exception = exc
            logger.warning(
                "Snowflake connection attempt %d/%d failed (DatabaseError): %s",
                attempt,
                _MAX_RETRIES,
                exc,
            )

        except Exception as exc:  # pylint: disable=broad-except
            last_exception = exc
            logger.warning(
                "Snowflake connection attempt %d/%d failed (unexpected error): %s",
                attempt,
                _MAX_RETRIES,
                exc,
            )

        if attempt < _MAX_RETRIES:
            backoff = _INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))
            logger.info(
                "Retrying Snowflake connection in %d second(s)...", backoff
            )
            time.sleep(backoff)

    logger.error(
        "Failed to establish Snowflake connection after %d attempt(s). "
        "Last error: %s",
        _MAX_RETRIES,
        last_exception,
    )
    raise ConnectionError(
        f"Could not connect to Snowflake after {_MAX_RETRIES} attempt(s). "
        f"Last error: {last_exception}"
    ) from last_exception
