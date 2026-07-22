import logging,yaml
from pathlib import Path
logger=logging.getLogger(__name__)
CFG=Path(__file__).resolve().parents[2]/"configs"/"error_config.yaml"
def _err():
    return yaml.safe_load(CFG.read_text()).get("active_error","none")
def get_snowflake_connection():
    e=_err()
    logger.info("Opening Snowflake connection")
    if e=="snowflake_timeout":
        raise TimeoutError("250001: Could not connect to Snowflake backend after 1 second.")
    if e=="snowflake_auth":
        raise PermissionError("390100: Incorrect username or password.")
    return "<mock-snowflake-connection>"
