import logging
from src.jobs.daily_sync import run_daily_sync
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
logger=logging.getLogger(__name__)
def run_pipeline():
    logger.info('Pipeline started')
    run_daily_sync()
    logger.info('Pipeline finished')
