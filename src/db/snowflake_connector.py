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
        SNOWFLAKE_ACCOUNT   — e.g. myorg-myaccount
        SNOWFLAKE_USER      — Snowflake username
        SNOWFLAKE_PASSWORD  — Snowflake password
        SNOWFLAKE_DATABASE  — (optional) default database
        SNOWFLAKE_SCHEMA    — (optional) default schema
        SNOWFLAKE_WAREHOUSE — (optional) default warehouse

    Test-harness error injection (controlled by configs/error_config.yaml)
    is preserved and clearly separated from the real connection path.
    """
    # ------------------------------------------------------------------ #
    # [TEST MODE] Error-injection branches — controlled by                 #
    # configs/error_config.yaml.  These run BEFORE any real network I/O.  #
    # ------------------------------------------------------------------ #
    active_error = get_active_error()

    if active_error == "snowflake_timeout":
        logger.warning("[TEST MODE] Simulating Snowflake timeout error.")
        raise TimeoutError(
            "250001: Could not connect to Snowflake backend after 1 second."
        )

    if active_error == "snowflake_auth":
        logger.warning("[TEST MODE] Simulating Snowflake authentication error.")
        raise PermissionError(
            "390100: Incorrect username or password was specified."
        )

    if active_error == "snowflake_dns":
        logger.warning("[TEST MODE] Simulating Snowflake DNS resolution error.")
        raise Exception(
            "snowflake.connector.errors.OperationalError: "
            "250001: Could not connect to Snowflake backend."
        )

    # ------------------------------------------------------------------ #
    # Real connection path                                                 #
    # ------------------------------------------------------------------ #
    if snowflake is None:
        raise ImportError(
            "snowflake-connector-python is not installed. "
            "Run: pip install snowflake-connector-python"
        )

    account = os.environ.get("SNOWFLAKE_ACCOUNT")
    user = os.environ.get("SNOWFLAKE_USER")
    password = os.environ.get("SNOWFLAKE_PASSWORD")

    missing = [k for k, v in {
        "SNOWFLAKE_ACCOUNT": account,
        "SNOWFLAKE_USER": user,
        "SNOWFLAKE_PASSWORD": password,
    }.items() if not v]

    if missing:
        raise EnvironmentError(
            "Missing required environment variable(s) for Snowflake connection: "
            + ", ".join(missing)
        )

    connect_kwargs = {
        "account": account,
        "user": user,
        "password": password,
        "network_timeout": _NETWORK_TIMEOUT_SECONDS,
    }

    database = os.environ.get("SNOWFLAKE_DATABASE")
    schema = os.environ.get("SNOWFLAKE_SCHEMA")
    warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE")

    if database:
        connect_kwargs["database"] = database
    if schema:
        connect_kwargs["schema"] = schema
    if warehouse:
        connect_kwargs["warehouse"] = warehouse

    logger.info(
        "Connecting to Snowflake account '%s' as user '%s' "
        "(network_timeout=%ds).",
        account,
        user,
        _NETWORK_TIMEOUT_SECONDS,
    )

    backoff = _INITIAL_BACKOFF_SECONDS
    last_exc = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            conn = snowflake.connector.connect(**connect_kwargs)
            logger.info(
                "Snowflake connection established successfully on attempt %d.",
                attempt,
            )
            return conn
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < _MAX_RETRIES:
                logger.warning(
                    "Snowflake connection attempt %d/%d failed: %s. "
                    "Retrying in %d second(s)…",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                    backoff,
                )
                time.sleep(backoff)
                backoff *= 2
            else:
                logger.error(
                    "Snowflake connection failed after %d attempt(s): %s",
                    _MAX_RETRIES,
                    exc,
                )

    raise last_exc
