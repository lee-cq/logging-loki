import logging
import os
import time

from logging_loki.handler import LokiHandler

logger = logging.getLogger("aa")

handler = LokiHandler(
    level="DEBUG",
    loki_url=os.getenv("LOKI_URL"),
    username=os.getenv("LOKI_USERNAME"),
    password=os.getenv("LOKI_PASSWORD"),
    tags={"app": "test_loki_headler"},
    thread_pool_size=0,
    verify=False,
)
ch = logging.StreamHandler()
ch.setLevel("DEBUG")

logger.addHandler(handler)
# logger.addHandler(ch)
logger.setLevel("DEBUG")


print(handler.level)
logger.info("test ok.")
logger.debug("test debug...")
