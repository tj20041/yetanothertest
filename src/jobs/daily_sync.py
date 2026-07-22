import logging
from src.db.snowflake_connector import get_snowflake_connection
logger=logging.getLogger(__name__)
def run_daily_sync():
    logger.info('Starting daily sync')
    conn=get_snowflake_connection()
    logger.info('Connected: %s',conn)
