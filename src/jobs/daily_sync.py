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

    conn = get_snowflake_connection()

    logger.info("Executing query on Snowflake")

    error = get_active_error()

    query = """
    SELECT *
    FROM CUSTOMER_TRANSACTIONS
    """

    logger.info("Executing SQL:\n%s", query.strip())

    if error == "table_not_found":

        time.sleep(1)

        logger.error(
            "SQL execution failed while querying CUSTOMER_TRANSACTIONS"
        )
        logger.error(
            "snowflake.connector.errors.ProgrammingError: "
            "002003 (42S02): SQL compilation error: "
            "Object 'CUSTOMER_TRANSACTIONS' does not exist or not authorized. "
            "Please verify that the table exists and the Snowflake user has SELECT privileges."
        )

        # Do not raise — log and return gracefully so pipeline can continue
        logger.warning(
            "Skipping CUSTOMER_TRANSACTIONS sync due to table_not_found error. "
            "Set active_error to 'none' in configs/error_config.yaml to resolve."
        )
        return

    logger.info("Daily sync completed successfully.")
