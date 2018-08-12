from coolqbot.main import run
from coolqbot.logger import logger

try:
    run()
except KeyboardInterrupt:
    logger.info("User stop. exit.")
    exit(0)