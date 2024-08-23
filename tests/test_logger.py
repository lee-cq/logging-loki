import logging
import os
import time

from logging_loki.handler import LokiHandler
from logging_loki.formater import DEFAULT_FIELD_MAX

logger = logging.getLogger("aa")

print(
    os.getenv("LOKI_URL"),
    os.getenv("LOKI_USERNAME"),
    os.getenv("LOKI_PASSWORD"),
)

handler = LokiHandler(
    loki_url=os.getenv("LOKI_URL"),
    username=os.getenv("LOKI_USERNAME"),
    password=os.getenv("LOKI_PASSWORD"),
    level="DEBUG",
    thread_pool_size=3,
    tags={"service_name": "test_loki_handler"},
    metadata={"test_meta": "meta"},
    included_field=DEFAULT_FIELD_MAX,
    gzipped=False,
    verify=False,
)

ch = logging.StreamHandler()
ch.setLevel("DEBUG")

logger.addHandler(handler)
# logger.addHandler(handler_gz)
# logger.addHandler(ch)
logger.setLevel("DEBUG")

print("level", handler.level)
logger.info("test ok.")
logger.debug("test debug...")
logger.warning("test warning ...")
logger.error("test error...")
