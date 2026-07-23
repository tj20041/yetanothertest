import logging
import time
import yaml
from pathlib import Path
from src.db.snowflake_connector import get_snowflake_connection

logger = logging.getLogger(__name__)

CONFIG = Path(__file__).resolve().parents[2] / "configs" / "error_config.yaml"


def get_active_error():
    with open(CONFIG) as f:
        return yaml.safe_load(f).get("active_error", "none")


def run_daily_sync():
    """Execute the daily Snowflake sync job.

    Establishes a Snowflake connection and runs the configured query.
    Logs structured failure messages at each stage and re-raises exceptions
    so the pipeline caller can handle or alert on them appropriately.

    Raises:
        Exception: Propagates any connection or query-execution failure
                   after logging a structured error message.
    """
    # --- Connection phase ---
    try:
        conn = get_snowflake_connection()
    except Exception as exc:
        logger.error(
            "Daily sync aborted — could not establish Snowflake connection: %s",
            exc,
            exc_info=True,
        )
        raise

    logger.info("Executing query on Snowflake")

    # --- Query execution phase ---
    error = get_active_error()

    try:
        if error == "table_not_found":
            query = """
        SELECT *
        FROM CUSTOMER_TRANSACTIONS
        """

            logger.info("Executing SQL:\n%s", query.strip())

            time.sleep(1)

            logger.error(
                "SQL execution failed while querying CUSTOMER_TRANSACTIONS"
            )

            raise Exception(
                "snowflake.connector.errors.ProgrammingError: "
                "002003 (42S02): SQL compilation error: "
                "Object 'CUSTOMER_TRANSACTIONS' does not exist or not authorized."
            )

        logger.info("Daily sync completed successfully.")

    except Exception as exc:
        logger.error(
            "Daily sync query failed: %s",
            exc,
            exc_info=True,
        )
        raise
